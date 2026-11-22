"""Local processing workbench: ``sim2web gui [PROJECT_DIR]``.

A small HTTP server on 127.0.0.1 that puts the library behind a JSON API and
serves the workbench user interface.  The workbench only *edits a case
configuration* (``case.yaml`` in the project directory) and *runs the
library on it*; everything it does can be reproduced with the commands it
shows.  The package it builds is the same static package ``sim2web build``
writes, displayed in the same viewer that is published.

Only the standard library is used, so the workbench adds no dependency and
can be bundled into a stand-alone executable.

API (JSON unless noted)
-----------------------
``GET  /api/project``           project directory, configuration, errors, commands
``PUT  /api/config``            replace the configuration; it is validated and saved
``GET  /api/browse?path=``      list a directory (for the file dialog)
``POST /api/jobs``              start ``inspect``, ``convert``, ``preview``, ``build`` or ``validate``
``GET  /api/jobs/<id>?since=n`` state, new log lines, result
``GET  /api/export``            ZIP of the package and its configuration (binary)
``GET  /site/...``              the built package; ``/preview/...`` the quick preview
"""
from __future__ import annotations

import copy
import io
import json
import mimetypes
import shutil
import os
import string
import threading
import time
import traceback
import uuid
import webbrowser
import zipfile
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from . import __version__
from .config import STRESS_ORDERS, ConfigError, config_from_dict, load_config

WORKBENCH_DIR = Path(__file__).parent / "workbench_dist"
CONFIG_NAME = "case.yaml"
PREVIEW_DIR = ".sim2web/preview"
#: Input files the file dialog offers.
MODEL_SUFFIXES = (".vtu", ".vtk", ".e", ".exo", ".ex2", ".med", ".xdmf", ".xmf", ".msh", ".inp")
CONVERTIBLE = (".e", ".exo", ".ex2", ".med", ".xdmf", ".xmf", ".msh", ".inp", ".vtk")
#: Allowed values offered by the forms (validated again by the library).
CHOICES = {
    "stress_orders": STRESS_ORDERS,
    "colormaps": ["jet", "viridis", "turbo", "coolwarm", "grayscale"],
    "stress_units": ["Pa", "kPa", "MPa"],
    "length_units": ["m", "mm", "cm", "ft"],
}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
HEADER = ("# Sim2Web case configuration, written by the Sim2Web workbench.\n"
          "# Reproduce with:  sim2web build case.yaml && sim2web validate case.yaml\n")


# --------------------------------------------------------------------------- #
# Jobs
# --------------------------------------------------------------------------- #
@dataclass
class Job:
    kind: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: str = "running"            # running | done | failed
    log: list[str] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    started: float = field(default_factory=time.time)
    finished: float | None = None

    def write(self, *parts):
        self.log.append(" ".join(str(p) for p in parts))

    def view(self, since: int = 0) -> dict:
        return {"id": self.id, "kind": self.kind, "state": self.state, "log": self.log[since:],
                "log_length": len(self.log), "result": self.result, "error": self.error,
                "seconds": (self.finished or time.time()) - self.started}


class Project:
    """A project directory holding ``case.yaml`` and the packages built from it."""

    def __init__(self, directory: str | Path):
        self.dir = Path(directory).resolve()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.dir / CONFIG_NAME
        self.config: dict | None = None
        self.inspection: dict | None = None
        self.jobs: dict[str, Job] = {}
        self._busy = threading.Lock()
        if self.config_path.is_file():
            self.config = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}

    # -- configuration ------------------------------------------------------ #
    def errors(self, data: dict | None = None) -> list[str]:
        data = self.config if data is None else data
        if not data:
            return ["No model has been opened yet."]
        try:
            cfg = config_from_dict(copy.deepcopy(data), self.dir)
            stages = cfg.resolved_stages()
            if not stages:
                return ["No input file matches the stage list."]
            if cfg.fields.stress.name:  # cheap: reads only the XML header of the first stage
                cfg.resolve_stress_order(stages[0].file)
        except (ConfigError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            return [str(exc)]
        return []

    def save(self, data: dict) -> list[str]:
        self.config = data
        self.config_path.write_text(HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                                    encoding="utf-8")
        return self.errors()

    def case(self, overrides: dict | None = None):
        data = copy.deepcopy(self.config)
        for key, value in (overrides or {}).items():
            node = data
            parts = key.split(".")
            for p in parts[:-1]:
                node = node.setdefault(p, {})
            node[parts[-1]] = value
        cfg = config_from_dict(data, self.dir)
        cfg.source_text = yaml.safe_dump(data, sort_keys=False)
        return cfg

    def state(self) -> dict:
        out_dir = self.dir / ((self.config or {}).get("output", {}) or {}).get("dir", "site")
        built = (out_dir / "model_cache" / "index.json").is_file()
        validation = out_dir / "validation" / "validation_summary.json"      # where `sim2web validate` writes
        report = out_dir / "model_cache" / "build_report.json"
        return {
            "version": __version__,
            "dir": str(self.dir),
            "config_file": str(self.config_path),
            "config": self.config,
            "yaml": self.config_path.read_text(encoding="utf-8") if self.config_path.is_file() else "",
            "errors": self.errors(),
            "inspection": self.inspection,
            "built": built,
            "site_url": "/site/index.html" if built else None,
            "build_report": json.loads(report.read_text(encoding="utf-8")) if report.is_file() else None,
            "validation": _validation_summary(validation),
            "commands": [f"cd \"{self.dir}\"", "sim2web build case.yaml", "sim2web validate case.yaml",
                         "sim2web serve site"],
            "choices": CHOICES,
        }

    # -- jobs ---------------------------------------------------------------- #
    def start(self, kind: str, params: dict) -> Job:
        runner = getattr(self, f"_job_{kind}", None)
        if runner is None:
            raise ValueError(f"unknown job '{kind}'")
        if not self._busy.acquire(blocking=False):
            raise RuntimeError("Another task is still running.")
        job = Job(kind)
        self.jobs[job.id] = job

        def run():
            try:
                job.result = runner(job, params) or {}
                job.state = "done"
            except Exception as exc:  # reported to the user, never raised in the server
                job.state = "failed"
                job.error = f"{type(exc).__name__}: {exc}"
                job.write(traceback.format_exc())
            finally:
                job.finished = time.time()
                self._busy.release()

        threading.Thread(target=run, daemon=True).start()
        return job

    def _job_inspect(self, job: Job, params: dict) -> dict:
        from .inspect import draft_config, inspect_vtu

        files = [p if p.is_absolute() else self.dir / p for p in map(Path, params.get("files", []))]
        names = list(params.get("names") or [f.stem for f in files])
        if not files:
            raise ValueError("Choose at least one model file.")
        for f in files:
            if not f.is_file():
                raise FileNotFoundError(f"{f} does not exist")
        if files[0].suffix.lower() != ".vtu":
            raise ValueError(f"{files[0].name} is not a VTU file; convert it first.")
        job.write(f"Inspecting {files[0]}")
        info = inspect_vtu(files[0])
        draft = yaml.safe_load(draft_config(info, self._rel(files[0])))
        draft["input"]["stages"] = [{"file": self._rel(f), "name": n or f.stem} for f, n in zip(files, names)]
        draft["output"] = {"dir": "site"}
        stress = draft.get("fields", {}).get("stress", {})
        named = {**info["point_arrays"], **info["cell_arrays"]}.get(stress.get("name"), {}).get("component_names")
        if stress.get("name") and not named:
            # never preselect an order the file does not state: the user must choose it
            stress["order"] = "from_file"
        if self.config and params.get("keep_settings"):
            kept = copy.deepcopy(self.config)
            kept["input"] = draft["input"]
            draft = kept
        self.inspection = info
        errors = self.save(draft)
        job.write(f"{info['cells']:,} cells, {info['points']:,} points; configuration drafted")
        return {"inspection": info, "errors": errors}

    def _job_convert(self, job: Job, params: dict) -> dict:
        from .convert import convert

        source = Path(params["file"])
        target_dir = self.dir / "input"
        target_dir.mkdir(exist_ok=True)
        target = target_dir / f"{source.stem}.vtu"
        job.write(f"Converting {source} -> {target}")
        report = convert(source, target, time=params.get("time", "last"))
        for item in report.get("assembled", []):
            job.write(f"assembled {item['array']} from {', '.join(item['from'])}")
        if report.get("exodus"):
            job.write(f"time step {report['exodus']['time_step']} (t = {report['exodus']['time']})")
        return {"file": str(target), "report": report}

    def _job_preview(self, job: Job, params: dict) -> dict:
        from .pipeline import build

        cfg = self.case({"output.dir": PREVIEW_DIR, "output.viewer": True, "sections.enabled": False})
        job.write("Quick preview: surfaces only, no sections")
        build(cfg, quality=False, log=job.write)
        return {"url": "/preview/index.html"}

    def _job_build(self, job: Job, params: dict) -> dict:
        from .pipeline import build

        cfg = load_config(self.config_path)
        if not cfg.output.viewer:
            # A workbench package needs a viewer. Persist this choice so that
            # replay uses exactly the same configuration and provenance hash.
            data = yaml.safe_load(cfg.source_text)
            data.setdefault("output", {})["viewer"] = True
            self.save(data)
            cfg = load_config(self.config_path)
        stale = cfg.output_dir / "validation"
        if stale.is_dir():  # a validation of the previous build must not be shown for this one
            shutil.rmtree(stale)
        result = build(cfg, log=job.write)
        return {"url": "/site/index.html", "report": json.loads(result.report_path.read_text(encoding="utf-8"))}

    def _job_validate(self, job: Job, params: dict) -> dict:
        from .validate import validate_package, write_report

        cfg = self.case()
        sections = params.get("sections", "all")
        report = validate_package(cfg, sections=sections if sections == "all" else int(sections), log=job.write)
        out = cfg.cache_dir.parent / "validation"
        write_report(report, out)
        return _validation_summary(out / "validation_summary.json")

    def _rel(self, path: Path) -> str:
        path = Path(path).resolve()
        try:
            return path.relative_to(self.dir).as_posix()
        except ValueError:
            return str(path)

    # -- export -------------------------------------------------------------- #
    def export_zip(self) -> bytes:
        cfg = self.case()
        out = cfg.output_dir
        if not (out / "model_cache" / "index.json").is_file():
            raise RuntimeError("Build the package before exporting it.")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(out.rglob("*")):
                if p.is_file():
                    z.write(p, Path("site") / p.relative_to(out))
            z.write(self.config_path, CONFIG_NAME)
        return buffer.getvalue()


def _validation_summary(path: Path) -> dict | None:
    if not path.is_file():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    return {"failures": report.get("failures", []), "passed": not report.get("failures"),
            "stages": {k: {kk: vv for kk, vv in v.items() if not isinstance(vv, (list, dict)) or kk == "failures"}
                       for k, v in report.get("stages", {}).items()}}


def browse(path: str | None) -> dict:
    """Directory listing for the file dialog (directories and model files)."""
    p = Path(path).expanduser() if path else Path.home()
    if p.is_file():
        p = p.parent
    p = p.resolve()
    entries = []
    try:
        children = sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))
    except PermissionError:
        children = []
    for c in children:
        if c.name.startswith("."):
            continue
        try:
            if c.is_dir():
                entries.append({"name": c.name, "path": str(c), "dir": True})
            elif c.suffix.lower() in MODEL_SUFFIXES:
                entries.append({"name": c.name, "path": str(c), "dir": False, "bytes": c.stat().st_size,
                                "convert": c.suffix.lower() in CONVERTIBLE})
        except OSError:
            continue
    drives = []
    if os.name == "nt":  # offer the drive letters on Windows
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    return {"path": str(p), "parent": str(p.parent) if p.parent != p else None, "entries": entries,
            "drives": drives}


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
class _Handler(BaseHTTPRequestHandler):
    project: Project
    server_version = f"Sim2Web/{__version__}"

    def log_message(self, fmt, *args):
        pass

    # local use only: refuse requests for other host names (DNS rebinding)
    def _local(self) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host not in LOCAL_HOSTS:
            self._json({"error": "The workbench only answers requests for localhost."}, HTTPStatus.FORBIDDEN)
            return False
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).hostname not in {"127.0.0.1", "localhost", "::1"}:
            self._json({"error": "Cross-origin requests are not accepted."}, HTTPStatus.FORBIDDEN)
            return False
        return True

    def _json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _file(self, root: Path, rel: str):
        root = root.resolve()
        target = (root / unquote(rel).lstrip("/")).resolve()
        if target.is_dir():
            target = target / "index.html"
        if root not in target.parents and target != root or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        ctype = {".vtp": "application/octet-stream", ".js": "text/javascript", ".json": "application/json",
                 ".css": "text/css", ".html": "text/html; charset=utf-8"}.get(target.suffix.lower()) \
            or mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._local():
            return
        url = urlparse(self.path)
        q = parse_qs(url.query)
        p = self.project
        try:
            if url.path in ("/", ""):
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/workbench/")
                self.end_headers()
            elif url.path == "/api/project":
                self._json(p.state())
            elif url.path == "/api/browse":
                self._json(browse((q.get("path") or [None])[0]))
            elif url.path.startswith("/api/jobs/"):
                job = p.jobs.get(url.path.rsplit("/", 1)[1])
                if job is None:
                    self._json({"error": "no such job"}, HTTPStatus.NOT_FOUND)
                else:
                    self._json(job.view(int((q.get("since") or [0])[0])))
            elif url.path == "/api/export":
                data = p.export_zip()
                name = f"{(p.config or {}).get('title') or 'sim2web'}".replace(" ", "_")[:60] + "_package.zip"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f"attachment; filename=\"{name}\"")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif url.path.startswith("/workbench"):
                if not (WORKBENCH_DIR / "index.html").is_file():
                    self._json({"error": "The workbench interface is not built: npm run build:workbench"},
                               HTTPStatus.NOT_FOUND)
                else:
                    self._file(WORKBENCH_DIR, url.path[len("/workbench"):] or "/")
            elif url.path.startswith("/site/") and p.config:
                self._file(p.case().output_dir, url.path[len("/site/"):])
            elif url.path.startswith("/preview/"):
                self._file(p.dir / PREVIEW_DIR, url.path[len("/preview/"):])
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except (ConfigError, RuntimeError, ValueError, FileNotFoundError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_PUT(self):
        if not self._local():
            return
        if urlparse(self.path).path != "/api/config":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = self._body().get("config")
        if not isinstance(data, dict):
            self._json({"error": "config must be an object"}, HTTPStatus.BAD_REQUEST)
            return
        self.project.save(data)
        self._json(self.project.state())

    def do_POST(self):
        if not self._local():
            return
        if urlparse(self.path).path != "/api/jobs":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = self._body()
        try:
            job = self.project.start(body.get("kind", ""), body.get("params") or {})
        except RuntimeError as exc:
            self._json({"error": str(exc)}, HTTPStatus.CONFLICT)
            return
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._json(job.view(), HTTPStatus.ACCEPTED)


def make_server(project_dir: str | Path, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("The workbench listens on the local machine only.")
    handler = type("Handler", (_Handler,), {"project": Project(project_dir)})
    return ThreadingHTTPServer((host, port), handler)


def run(project_dir: str | Path = ".", port: int = 8765, open_browser: bool = True) -> None:
    server = make_server(project_dir, port=port)
    url = f"http://127.0.0.1:{server.server_address[1]}/workbench/"
    print(f"Sim2Web workbench for {Path(project_dir).resolve()}\n  {url}\n(Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
