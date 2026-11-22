"""Compare a sim2web package with products of the frozen v0.1 case scripts.

Usage::

    python scripts/compare_with_legacy.py CONFIG LEGACY_MODEL_CACHE [--out report.json]

Products are matched by role (excavation/exterior surface) and by section axis
and position.  Each pair is compared first byte for byte, then geometry and
every array value by value, so that a difference in file encoding is not
mistaken for a numerical difference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pyvista as pv

from sim2web.config import load_config

LEGACY_PRIMARY = {"excavation": "cavity_surface.vtp", "exterior": "full_model.vtp"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def legacy_sections(stage_dir: Path):
    out = {}
    for p in stage_dir.glob("slice_*.vtp"):
        m = re.match(r"slice_([xyz])_(-?[\d.]+)\.vtp$", p.name)
        out[(m.group(1), float(m.group(2)))] = p
    return out


def compare_arrays(a, b):
    diffs = []
    if a.n_points != b.n_points or a.n_cells != b.n_cells:
        return [f"size {a.n_points}/{a.n_cells} vs {b.n_points}/{b.n_cells}"]
    if not np.array_equal(a.points, b.points):
        diffs.append("points")
    if not np.array_equal(a.faces, b.faces):
        diffs.append("faces")
    for kind in ("point_data", "cell_data"):
        ca, cb = getattr(a, kind), getattr(b, kind)
        if list(ca.keys()) != list(cb.keys()):
            diffs.append(f"{kind} names {sorted(ca.keys())} vs {sorted(cb.keys())}")
        for name in set(ca.keys()) & set(cb.keys()):
            x, y = np.asarray(ca[name]), np.asarray(cb[name])
            if x.dtype.kind in "USO" or y.dtype.kind in "USO":
                same = np.array_equal(x.astype(str), y.astype(str))
            else:
                same = np.array_equal(x, y)
            if not same:
                diffs.append(f"{kind}:{name} values")
            elif x.dtype != y.dtype:
                diffs.append(f"{kind}:{name} dtype {x.dtype} vs {y.dtype}")
    return diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("legacy_cache")
    ap.add_argument("--hash-record", help="hashes_<case>.json of a published v0.1 run")
    ap.add_argument("--out")
    args = ap.parse_args()
    record = json.loads(Path(args.hash_record).read_text()) if args.hash_record else None
    cfg = load_config(args.config)
    index = json.loads((cfg.cache_dir / "index.json").read_text(encoding="utf-8"))
    root = cfg.cache_dir.parent
    report = {"config": Path(args.config).as_posix(), "stages": {}}
    for stage in index["stages"]:
        legacy_dir = Path(args.legacy_cache) / stage["id"]
        pairs = []
        for layer in stage["layers"]:
            name = LEGACY_PRIMARY[layer["kind"]]
            if (legacy_dir / name).exists():
                pairs.append((layer["file"], legacy_dir / name))
        legacy = legacy_sections(legacy_dir)
        new_keys = set()
        for axis, entries in stage["sections"].items():
            for e in entries:
                key = (axis, round(e["value"], 6))
                new_keys.add(key)
                match = next((p for (ax, v), p in legacy.items() if ax == axis and abs(v - e["value"]) < 5e-3), None)
                pairs.append((e["file"], match))
        unmatched_legacy = sorted(f"{a}={v:g}" for (a, v) in legacy
                                  if not any(a == k[0] and abs(v - k[1]) < 5e-3 for k in new_keys))
        identical = equal_values = 0
        problems = []
        for new_rel, old in pairs:
            if old is None:
                problems.append(f"{new_rel}: no legacy counterpart")
                continue
            new = root / new_rel
            if record is not None:
                rel = f"{stage['id']}/{old.name}"
                if rel in record and sha(new) == record[rel]:
                    identical += 1
                    equal_values += 1
                    continue
            if sha(new) == sha(old):
                identical += 1
                equal_values += 1
                continue
            diffs = compare_arrays(pv.read(new), pv.read(old))
            if not diffs or all("dtype" in d for d in diffs):
                equal_values += 1
            problems.append(f"{new_rel} vs {old.name}: {diffs or 'bytes only'}")
        report["stages"][stage["id"]] = {"pairs": len(pairs), "byte_identical": identical, "compared_with": "hash record" if record else "legacy files",
                                         "value_identical": equal_values, "unmatched_legacy": unmatched_legacy,
                                         "differences": problems}
        print(stage["id"], json.dumps(report["stages"][stage["id"]], indent=1)[:3000])
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
