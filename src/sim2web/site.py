"""Static-site helpers: install the packaged viewer and serve a package locally."""
from __future__ import annotations

import functools
import http.server
import shutil
from pathlib import Path

VIEWER_DIR = Path(__file__).parent / "viewer_dist"


class ViewerNotBuilt(RuntimeError):
    pass


def viewer_available() -> bool:
    return (VIEWER_DIR / "index.html").is_file()


def install_viewer(output_dir: str | Path, source: str | Path | None = None) -> Path:
    """Copy the prebuilt viewer (``index.html`` and ``assets/``) into ``output_dir``.

    The viewer is data-driven: it reads ``model_cache/index.json`` and needs no
    per-case code.  A custom build can be supplied through ``source``.
    """
    src = Path(source) if source else VIEWER_DIR
    if not (src / "index.html").is_file():
        raise ViewerNotBuilt(
            f"No viewer build found in {src}. Install a released wheel, or build it with "
            "'npm ci && npm run build:viewer' in the repository root.")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = out / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    return out


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".vtp": "application/octet-stream", ".json": "application/json", ".js": "text/javascript"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):  # quieter default
        pass


def serve(directory: str | Path, host: str = "127.0.0.1", port: int = 8000) -> None:
    handler = functools.partial(_Handler, directory=str(directory))
    with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
        print(f"Serving {directory} at http://{host}:{port}/  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
