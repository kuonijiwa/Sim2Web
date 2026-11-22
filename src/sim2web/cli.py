"""Command-line interface: ``sim2web <command> ...``."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__


def _cmd_build(args):
    from .config import load_config
    from .pipeline import build

    cfg = load_config(args.config, args.set)
    copy_viewer = False if args.no_viewer else None
    result = build(cfg, quality=not args.no_quality, copy_viewer=copy_viewer)
    print(f"Package: {result.output_dir}")
    return 0


def _cmd_validate(args):
    from .config import load_config
    from .validate import validate_package, write_report

    cfg = load_config(args.config, args.set)
    sections = args.sections if args.sections == "all" else int(args.sections)
    report = validate_package(cfg, sections=sections)
    out = Path(args.out) if args.out else cfg.cache_dir.parent / "validation"
    js, cs = write_report(report, out)
    print(f"Summary: {js}\nPairs:   {cs}")
    if report["failures"]:
        print("FAILED:\n  " + "\n  ".join(report["failures"][:50]))
        return 1
    print("All checks passed.")
    return 0


def _cmd_sensitivity(args):
    from .config import load_config
    from .diagnostics import excavation_sensitivity

    cfg = load_config(args.config, args.set)
    result = excavation_sensitivity(cfg, args.stage, args.thresholds, args.tolerances)
    _dump(result, args.out)
    return 0


def _cmd_interp(args):
    from .config import load_config
    from .diagnostics import analytical_interpolation_check

    cfg = load_config(args.config, args.set)
    result = analytical_interpolation_check(cfg, args.stage, per_axis=args.per_axis)
    _dump(result, args.out)
    return 0


def _cmd_inspect(args):
    from .inspect import draft_config, inspect_vtu

    info = inspect_vtu(args.vtu)
    if args.draft_config:
        Path(args.draft_config).write_text(draft_config(info, args.vtu), encoding="utf-8")
        print(f"Draft configuration written to {args.draft_config}; review every line marked REVIEW.",
              file=sys.stderr)
    print(json.dumps(info, indent=2))
    return 0


def _cmd_convert(args):
    from .convert import convert

    names = {}
    for item in args.component_names or []:
        array, _, comps = item.partition("=")
        names[array] = [c.strip().upper() for c in comps.split(",")]
    rename = dict(item.split("=", 1) for item in args.rename or [])
    time = args.time
    if time not in ("last", "first") and not time.startswith("#"):
        time = float(time)
    report = convert(args.source, args.target, names, rename, time=time, assemble=not args.no_assemble)
    print(json.dumps(report, indent=2))
    if report["dropped"]:
        print("Note: non-3D or unsupported cells were dropped (see 'dropped', VTK cell type ids).", file=sys.stderr)
    return 0


def _cmd_gui(args):
    from .workbench import run

    run(args.project, port=args.port, open_browser=not args.no_browser)
    return 0


def _cmd_serve(args):
    from .site import serve

    serve(args.directory, args.host, args.port)
    return 0


def _cmd_install_viewer(args):
    from .site import install_viewer

    print(install_viewer(args.directory, args.source))
    return 0


def _dump(result, out):
    text = json.dumps(result, indent=2)
    if out:
        Path(out).write_text(text + "\n", encoding="utf-8")
        print(f"Written to {out}")
    else:
        print(text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="sim2web", description="Prepare geotechnical simulation results for browser review.")
    parser.add_argument("--version", action="version", version=f"sim2web {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="build a static review package from a case configuration")
    p.add_argument("config")
    p.add_argument("--no-viewer", action="store_true", help="write data products only")
    p.add_argument("--no-quality", action="store_true", help="skip triangle-quality statistics")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("validate", help="verify a built package against its source models")
    p.add_argument("config")
    p.add_argument("--sections", default="all", help="'all' or N: interpolation check on every N-th section")
    p.add_argument("--out", help="report directory (default: <output>/validation)")
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("sensitivity", help="excavation-boundary sensitivity to threshold and tolerance")
    p.add_argument("config")
    p.add_argument("--stage")
    p.add_argument("--thresholds", type=float, nargs="+")
    p.add_argument("--tolerances", type=float, nargs="+")
    p.add_argument("--out")
    p.set_defaults(func=_cmd_sensitivity)

    p = sub.add_parser("verify-interpolation", help="analytical linear-field check of section interpolation")
    p.add_argument("config")
    p.add_argument("--stage")
    p.add_argument("--per-axis", type=int, default=5)
    p.add_argument("--out")
    p.set_defaults(func=_cmd_interp)

    p = sub.add_parser("inspect", help="list the arrays of a VTU and optionally draft a configuration")
    p.add_argument("vtu")
    p.add_argument("--draft-config")
    p.set_defaults(func=_cmd_inspect)

    p = sub.add_parser("gui", help="open the processing workbench in the browser (local only)")
    p.add_argument("project", nargs="?", default=".", help="project directory (holds case.yaml); default: here")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    p.set_defaults(func=_cmd_gui)
    p = sub.add_parser("convert", help="convert another mesh/result format (via meshio) to VTU")
    p.add_argument("source")
    p.add_argument("target")
    p.add_argument("--component-names", action="append", metavar="ARRAY=C1,C2,...",
                   help="stamp component names, e.g. sigma=XX,YY,ZZ,XY,YZ,XZ")
    p.add_argument("--rename", action="append", metavar="OLD=NEW", help="rename an array")
    p.add_argument("--time", default="last", metavar="last|first|#STEP|VALUE",
                   help="Exodus time step to convert: last (default), first, #index or the nearest time value")
    p.add_argument("--no-assemble", action="store_true",
                   help="keep separate component arrays (stress_xx, ..., disp_x, ...) instead of assembling them")
    p.set_defaults(func=_cmd_convert)

    p = sub.add_parser("serve", help="serve a built package over HTTP for local viewing")
    p.add_argument("directory")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=_cmd_serve)

    p = sub.add_parser("install-viewer", help="copy the packaged viewer into a directory")
    p.add_argument("directory")
    p.add_argument("--source", help="custom viewer build directory")
    p.set_defaults(func=_cmd_install_viewer)

    for name in ("build", "validate", "sensitivity", "verify-interpolation"):
        sub.choices[name].add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                                       help="override a configuration value, e.g. sections.spacing=5")
    args = parser.parse_args(argv)
    from .config import ConfigError

    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
