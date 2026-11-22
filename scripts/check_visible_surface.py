"""Check that removing internal block contacts did not change the visible surface.

    python scripts/check_visible_surface.py CONFIG [--rays 1000] [--stage NAME]

Rays are cast from random directions outside the model towards random points
inside its bounding box. For every ray, the distance to the first hit on the
complete block surface (every block face, as published by v0.1) is compared
with the first hit on the published exterior layer. Identical first hits mean
that the removed faces were not visible from outside.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pyvista as pv
import vtk

from sim2web.config import load_config


def first_hit(tree, p0, p1):
    pts, ids = vtk.vtkPoints(), vtk.vtkIdList()
    tree.IntersectWithLine(p0, p1, pts, ids)
    if pts.GetNumberOfPoints() == 0:
        return None
    hits = np.array([pts.GetPoint(i) for i in range(pts.GetNumberOfPoints())])
    return float(np.min(np.linalg.norm(hits - p0, axis=1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("--rays", type=int, default=1000)
    ap.add_argument("--stage")
    ap.add_argument("--out")
    args = ap.parse_args()
    cfg = load_config(args.config)
    index = json.loads((cfg.cache_dir / "index.json").read_text(encoding="utf-8"))
    stage = next(s for s in index["stages"] if args.stage in (None, s["id"]))
    spec = next(s for s in cfg.resolved_stages() if s.name == stage["id"])
    source = pv.read(spec.file)
    full = source.extract_surface()
    layer = next(l for l in stage["layers"] if l["kind"] == "exterior")
    published = pv.read(cfg.cache_dir.parent / layer["file"])
    trees = []
    for mesh in (full, published):
        tree = vtk.vtkOBBTree()
        tree.SetDataSet(mesh)
        tree.BuildLocator()
        trees.append(tree)
    b = np.asarray(source.bounds, dtype=float)
    centre, span = (b[0::2] + b[1::2]) / 2, b[1::2] - b[0::2]
    radius = float(np.linalg.norm(span))
    rng = np.random.default_rng(1)
    started = time.time()
    hits = same = only_one = 0
    worst = 0.0
    for _ in range(args.rays):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        target = centre + (rng.random(3) - 0.5) * span * 0.9
        p0, p1 = target + d * radius, target - d * radius
        a, c = first_hit(trees[0], p0, p1), first_hit(trees[1], p0, p1)
        if a is None and c is None:
            continue
        if (a is None) != (c is None):
            only_one += 1
            continue
        hits += 1
        worst = max(worst, abs(a - c))
        same += abs(a - c) < 1e-3 * max(1.0, radius / 1000)
    result = {"stage": stage["id"], "rays": args.rays, "rays_hitting_model": hits + only_one,
              "same_first_hit": same, "different_first_hit": hits - same, "hit_only_one_surface": only_one,
              "largest_distance_difference": worst, "faces_full_surface": int(full.n_cells),
              "faces_published": int(published.n_cells), "seconds": round(time.time() - started, 1)}
    print(json.dumps(result, indent=2))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
