"""Regenerate three real cases and compare final VTP arrays using source IDs."""
import csv
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import pyvista as pv
import scipy
import vtk

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_evidence/revision_v2"
OUT.mkdir(parents=True, exist_ok=True)
CASES = {"A": "flac3d_cavern_iv2", "B": "flac3d_slope_exac23", "C": "3dec_slope"}
STRESS = ["Stress_XX", "Stress_YY", "Stress_ZZ", "Stress_Min_Principal", "Stress_Mid_Principal", "Stress_Max_Principal"]


def expected_fields(source, case):
    d = np.asarray(source.point_data["Displacement"], dtype=np.float64)
    point = dict(zip(["X_Disp", "Y_Disp", "Z_Disp"], d.T))
    point["TotalDisplacement"] = np.linalg.norm(d, axis=1)
    key = next(k for k in source.cell_data if "stress" in k.lower())
    s = np.asarray(source.cell_data[key], dtype=np.float64)
    t = np.zeros((len(s), 3, 3))
    t[:, 0, 0], t[:, 1, 1], t[:, 2, 2] = s[:, :3].T
    t[:, 0, 1] = t[:, 1, 0] = s[:, 3]
    t[:, 0, 2] = t[:, 2, 0] = s[:, 4 if case == "C" else 5]
    t[:, 1, 2] = t[:, 2, 1] = s[:, 5 if case == "C" else 4]
    ev = np.linalg.eigvalsh(t)
    cell = dict(zip(STRESS, [s[:, 0], s[:, 1], s[:, 2], ev[:, 0], ev[:, 1], ev[:, 2]]))
    labels = {}
    for k in source.cell_data:
        if "group" in k.lower():
            values, inv = np.unique(source.cell_data[k], return_inverse=True)
            cell[k + "_ID"] = inv
            labels[k + "_ID"] = [str(x) for x in values]
    return point, cell, labels


def measure(actual, expected):
    delta = np.asarray(actual, dtype=np.float64) - expected
    span = float(np.ptp(expected))
    rmse = float(np.sqrt(np.mean(delta * delta)))
    return {"tuples": len(expected), "max_absolute_error": float(np.max(np.abs(delta))), "rmse": rmse,
            "reference_span": span, "nrmse": rmse / span if span else None,
            "equals_expected_float32": bool(np.array_equal(actual, expected.astype(np.float32)))}


def tree_hash(folder):
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--geometry-reference', type=Path, help='Optional earlier candidate for read-only geometry regression')
    args = parser.parse_args()
    info = {"platform": platform.platform(), "python": platform.python_version(),
            "numpy": np.__version__, "scipy": scipy.__version__, "pyvista": pv.__version__, "vtk": vtk.vtkVersion.GetVTKVersion(),
            "logical_processors": os.cpu_count(), "cases": {},
            "scope": "All output CellData stress/category arrays; primary PointData displacement; slices PointData interpolation not independently validated"}
    all_rows = []
    for case, folder in CASES.items():
        case_root = ROOT / "examples" / folder
        # Only the newly copied candidate's explicit output can be regenerated.
        target = (case_root / "output/model_cache").resolve()
        assert target.is_relative_to(ROOT.resolve()) and (ROOT / 'pyproject.toml').is_file()
        times, hashes = [], []
        for repeat in range(2):
            started = time.perf_counter()
            with (OUT / f"processing_{case}_{repeat + 1}.log").open("w", encoding="utf-8") as log:
                subprocess.run([sys.executable, str(case_root / "processing/process.py")], cwd=ROOT,
                               stdout=log, stderr=subprocess.STDOUT, check=True,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0"})
            times.append(time.perf_counter() - started)
            log_path = OUT / f"processing_{case}_{repeat + 1}.log"
            log_path.write_text(log_path.read_text(encoding='utf-8').replace(str(ROOT), 'REPOSITORY_ROOT'), encoding='utf-8')
            hashes.append(tree_hash(target))
        source_file = next((case_root / "input").glob("*.vtu"))
        source = pv.read(source_file)
        point, cell, labels = expected_fields(source, case)
        paths = sorted(target.rglob("*.vtp"))
        primary_name = "cavity_surface.vtp" if case == "A" else "full_model.vtp"
        primary = next(p for p in paths if p.name == primary_name)
        records = []
        category_count = 0
        failed = []
        geometry_unchanged = True if args.geometry_reference else None
        old_base = args.geometry_reference / "examples" / folder / "output/model_cache" if args.geometry_reference else None
        for path in paths:
            mesh = pv.read(path)
            if any(k.endswith("_ID") and not k.startswith("Source_") for k in mesh.point_data):
                failed.append(f"Averaged point category in {path.name}")
            ids = np.asarray(mesh.cell_data["Source_Cell_ID"])
            assert np.issubdtype(ids.dtype, np.integer) and ids.min() >= 0 and ids.max() < source.n_cells
            for name, values in cell.items():
                actual = np.asarray(mesh.cell_data[name])
                expected = values[ids]
                metric = measure(actual, expected)
                if name.endswith("_ID"):
                    category_count += len(actual)
                    metric["category_agreement"] = float(np.mean(actual == expected))
                row = {"case": case, "file": path.relative_to(ROOT).as_posix(), "association": "CellData", "field": name, **metric}
                records.append(row)
                if not metric["equals_expected_float32"]:
                    failed.append(f"CellData mismatch: {path.name}/{name}")
            if path == primary:
                pids = np.asarray(mesh.point_data["Source_Point_ID"])
                assert np.issubdtype(pids.dtype, np.integer)
                for name, values in point.items():
                    metric = measure(mesh.point_data[name], values[pids])
                    records.append({"case": case, "file": path.relative_to(ROOT).as_posix(), "association": "PointData", "field": name, **metric})
                    if not metric["equals_expected_float32"]:
                        failed.append(f"PointData mismatch: {path.name}/{name}")
                if not np.array_equal(mesh.points, np.asarray(source.points[pids], dtype=np.float32)):
                    failed.append("Primary coordinates differ from source-point correspondence")
            if old_base is not None:
                old = pv.read(old_base / path.relative_to(target))
                geometry_unchanged &= (np.array_equal(old.points, mesh.points) and np.array_equal(old.faces, mesh.faces))
        all_rows.extend(records)
        nrmse = [r["nrmse"] for r in records if r["nrmse"] is not None and not r["field"].endswith("_ID")]
        m = pv.read(primary)
        info["cases"][case] = {"processing_seconds": times, "vtp_count": len(paths), "primary_points": m.n_points,
            "primary_cells": m.n_cells, "raw_bytes": source_file.stat().st_size, "primary_bytes": primary.stat().st_size,
            "output_bytes": sum(p.stat().st_size for p in target.rglob("*") if p.is_file()),
            "byte_identical_regeneration": hashes[0] == hashes[1], "regenerated_files": len(hashes[0]),
            "geometry_identical_to_frozen": geometry_unchanged, "paired_arrays": len(records),
            "paired_tuples": sum(r["tuples"] for r in records), "category_tuples": category_count,
            "max_nrmse": max(nrmse), "category_labels": labels, "failures": failed}
        (OUT / f"hashes_{case}.json").write_text(json.dumps(hashes[1], indent=2), encoding="utf-8")
        (OUT / "summary.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
        print(case, json.dumps(info["cases"][case]), flush=True)
    keys = ["case", "file", "association", "field", "tuples", "max_absolute_error", "rmse", "reference_span", "nrmse", "equals_expected_float32", "category_agreement"]
    with (OUT / "source_output_pairs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_rows)
    assert not any(c["failures"] for c in info["cases"].values()), "See summary for mismatches"


if __name__ == "__main__":
    main()
