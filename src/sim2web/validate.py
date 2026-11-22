"""Independent verification of a built package against its source models.

Three kinds of evidence are kept separate, as they establish different things:

``exact``          arrays that are copies of source values (CellData via
                   ``Source_Cell_ID``; primary-surface PointData via
                   ``Source_Point_ID``).  They must equal the source-derived
                   Float32 reference bit for bit.
``interpolation``  PointData on section vertices, which are new points on cut
                   cell edges.  They are compared with an *independent*
                   evaluation of the source field at the same coordinates
                   (``vtkProbeFilter``: cell location + shape functions, a
                   different code path from the cutter's edge interpolation).
``package``        file hashes, field associations and ranges recorded in
                   ``index.json``.

The expected values are recomputed here from the raw source arrays without
calling the build code, so a defect in :mod:`sim2web.fields` cannot hide
itself.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from .config import CaseConfig
from .writer import sha256_file

_PAIRS = {"XX": (0, 0), "YY": (1, 1), "ZZ": (2, 2), "XY": (0, 1), "YX": (0, 1),
          "YZ": (1, 2), "ZY": (1, 2), "XZ": (0, 2), "ZX": (0, 2)}


def reference_order(cfg: CaseConfig, path) -> tuple[list[str] | None, list[str]]:
    """Stress order for the reference values, established independently of the build.

    The file's ``ComponentName`` attributes take precedence; the configuration
    is used only when the file names no components.  A disagreement between
    the two is reported as a failure even when the build was told to ignore it.
    """
    from .vtkxml import component_names

    s = cfg.fields.stress
    if not s.name:
        return None, []
    in_file = component_names(path).get(s.name)
    declared = cfg.stress_order
    problems = []
    if in_file and declared and in_file != declared:
        problems.append(f"configured stress order {','.join(declared)} differs from the file's ComponentName "
                        f"attributes {','.join(in_file)}")
    order = in_file or declared
    if order is None:
        problems.append("the stress order is neither declared nor named in the file")
    return order, problems


def reference_fields(source, cfg: CaseConfig, order: list[str] | None = None):
    """Float64 expected arrays recomputed directly from the source model."""
    point, cell = {}, {}
    f = cfg.fields
    if f.displacement.name:
        d = np.asarray(source.point_data[f.displacement.name], dtype=np.float64)
        point.update({"X_Disp": d[:, 0], "Y_Disp": d[:, 1], "Z_Disp": d[:, 2],
                      "TotalDisplacement": np.sqrt(np.sum(d[:, :3] ** 2, axis=1))})
    if f.stress.name:
        holder = source.cell_data if f.stress.name in source.cell_data else source.point_data
        s = np.asarray(holder[f.stress.name], dtype=np.float64)
        order = order or cfg.stress_order
        t = np.empty((len(s), 3, 3))
        for col, comp in enumerate(order):
            i, j = _PAIRS[comp]
            t[:, i, j] = t[:, j, i] = s[:, col]
        ev = np.linalg.eigvalsh(t)
        target = cell if f.stress.name in source.cell_data else point
        target.update({"Stress_XX": t[:, 0, 0], "Stress_YY": t[:, 1, 1], "Stress_ZZ": t[:, 2, 2],
                       "Stress_Min_Principal": ev[:, 0], "Stress_Mid_Principal": ev[:, 1],
                       "Stress_Max_Principal": ev[:, 2]})
    for cat in f.categories:
        _, codes = np.unique(source.cell_data[cat.name], return_inverse=True)
        cell[f"{cat.name}_ID"] = codes
    for extra in f.extra:
        target = cell if extra.association == "cell" else point
        target[extra.name] = np.asarray((source.cell_data if extra.association == "cell" else source.point_data)[extra.name],
                                        dtype=np.float64)
    return point, cell


def compare(actual, expected) -> dict:
    a = np.asarray(actual)
    e = np.asarray(expected, dtype=np.float64)
    delta = a.astype(np.float64) - e
    span = float(np.ptp(e)) if e.size else 0.0
    rmse = float(np.sqrt(np.mean(delta * delta))) if e.size else 0.0
    if np.issubdtype(a.dtype, np.integer):
        equal32 = bool(np.array_equal(a, expected))
    else:
        equal32 = bool(np.array_equal(a, e.astype(np.float32)))
    return {"tuples": int(e.size), "max_abs_error": float(np.max(np.abs(delta))) if e.size else 0.0,
            "rmse": rmse, "reference_span": span, "nrmse": rmse / span if span else None,
            "equals_float32_reference": equal32}


def probe(source_points_only, coordinates: np.ndarray, names: list[str], tolerance: float):
    """Evaluate source PointData at arbitrary coordinates with vtkProbeFilter.

    ``tolerance`` must exceed the Float32 rounding of the written coordinates.
    """
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(coordinates, dtype=np.float64), deep=True))
    target = vtk.vtkPolyData()
    target.SetPoints(pts)
    flt = vtk.vtkProbeFilter()
    flt.SetInputData(target)
    flt.SetSourceData(source_points_only)
    flt.SetTolerance(tolerance)
    flt.ComputeToleranceOff()
    # a cell locator also works where blocks share no nodes (point-locator default does not)
    flt.SetFindCellStrategy(vtk.vtkCellLocatorStrategy())
    flt.Update()
    out = flt.GetOutput()
    valid = vtk_to_numpy(out.GetPointData().GetArray(flt.GetValidPointMaskArrayName())).astype(bool)
    values = {n: vtk_to_numpy(out.GetPointData().GetArray(n)).astype(np.float64).copy() for n in names}
    fallback = np.flatnonzero(~valid)
    if fallback.size:
        # Points on warped (non-planar) exterior faces can fall a few Float32
        # ulps outside every cell.  Evaluate the shape functions of the closest
        # cell instead, provided it is within ``tolerance``.
        locator = vtk.vtkStaticCellLocator()
        locator.SetDataSet(source_points_only)
        locator.BuildLocator()
        cell = vtk.vtkGenericCell()
        closest = [0.0, 0.0, 0.0]
        cid, sub, dist2 = vtk.reference(0), vtk.reference(0), vtk.reference(0.0)
        pcoords, weights = [0.0, 0.0, 0.0], [0.0] * 27
        pd = source_points_only.GetPointData()
        arrays = {n: vtk_to_numpy(pd.GetArray(n)).astype(np.float64) for n in names}
        sub_id = vtk.reference(0)
        d2 = vtk.reference(0.0)
        for k in fallback:
            x = coordinates[k].tolist()
            locator.FindClosestPoint(x, closest, cell, cid, sub, dist2)
            if dist2.get() > tolerance * tolerance:
                continue
            source_points_only.GetCell(cid.get(), cell)
            inside = [0.0, 0.0, 0.0]
            cell.EvaluatePosition(x, inside, sub_id, pcoords, d2, weights)
            # evaluate the shape functions at the projected point on the cell
            cell.EvaluatePosition(list(closest), inside, sub_id, pcoords, d2, weights)
            ids = [cell.GetPointId(i) for i in range(cell.GetNumberOfPoints())]
            w = np.asarray(weights[:len(ids)])
            for n in names:
                values[n][k] = float(np.dot(w, arrays[n][ids]))
            valid[k] = True
    fallback_mask = np.zeros(len(coordinates), dtype=bool)
    fallback_mask[fallback] = True
    return values, valid, fallback_mask


def _vertex_cells(mesh):
    """CSR map from section vertex to the polygons that use it."""
    from .geometry import polygons

    offsets, conn = polygons(mesh)
    owner = np.repeat(np.arange(len(offsets) - 1), np.diff(offsets))
    order = np.argsort(conn, kind="stable")
    starts = np.searchsorted(conn[order], np.arange(mesh.n_points + 1))
    return owner[order], starts


def _interpolate_in_cell(source, cell_id, x, arrays):
    cell = vtk.vtkGenericCell()
    source.GetCell(int(cell_id), cell)
    closest, pcoords, weights = [0.0] * 3, [0.0] * 3, [0.0] * 27
    sub, d2 = vtk.reference(0), vtk.reference(0.0)
    cell.EvaluatePosition(list(x), closest, sub, pcoords, d2, weights)
    ids = [cell.GetPointId(i) for i in range(cell.GetNumberOfPoints())]
    w = np.asarray(weights[:len(ids)])
    return {n: float(np.dot(w, a[ids])) for n, a in arrays.items()}, float(np.sqrt(d2.get()))


def cell_restricted_check(mesh, source, arrays, flagged, tolerance_by_field):
    """Re-evaluate flagged section vertices inside each incident source cell.

    Returns per field the maximum error against the *best-matching* incident
    cell, and the number of vertices whose incident source cells disagree
    (vertices on a displacement discontinuity, e.g. a block contact).
    """
    poly_of_vertex, starts = _vertex_cells(mesh)
    src_cell = np.asarray(mesh.cell_data["Source_Cell_ID"])
    names = list(arrays)
    worst = {n: 0.0 for n in names}
    on_discontinuity = 0
    max_jump = {n: 0.0 for n in names}
    for v in flagged:
        cells = np.unique(src_cell[poly_of_vertex[starts[v]:starts[v + 1]]])
        if not cells.size:
            continue
        evals = [_interpolate_in_cell(source, c, mesh.points[v], arrays)[0] for c in cells]
        disagree = False
        for n in names:
            vals = np.array([e[n] for e in evals])
            stored = float(mesh.point_data[n][v])
            worst[n] = max(worst[n], float(np.min(np.abs(vals - stored))))
            jump = float(np.ptp(vals)) if len(vals) > 1 else 0.0
            max_jump[n] = max(max_jump[n], jump)
            disagree |= jump > tolerance_by_field[n]
        on_discontinuity += int(disagree)
    return worst, on_discontinuity, max_jump


def validate_package(cfg: CaseConfig, sections: str | int = "all", log=print) -> dict:
    """Validate every product listed in the package index.

    ``sections`` selects which sections receive the interpolation check:
    ``"all"`` or an integer *n* for every *n*-th section on each axis.
    """
    index_path = cfg.cache_dir / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    root = cfg.cache_dir.parent
    meta = index["fields"]
    report = {"index": str(index_path.name), "schema": index.get("schema"), "stages": {}, "failures": []}
    rows = []
    stride = 1 if sections == "all" else max(1, int(sections))
    for stage in index["stages"]:
        spec = next(s for s in cfg.resolved_stages() if s.name == stage["id"])
        source = pv.read(spec.file)
        order, failures = reference_order(cfg, spec.file)
        point_ref, cell_ref = reference_fields(source, cfg, order)
        if sha256_file(spec.file) != stage["source"]["sha256"]:
            failures.append("Source file hash differs from the hash recorded at build time")
        # probe source: geometry + raw displacement only (independent of build arrays)
        probe_src = pv.UnstructuredGrid(source.cells, source.celltypes, np.asarray(source.points, dtype=np.float64))
        for name, values in point_ref.items():
            probe_src.point_data[name] = values
        nodal_stress = bool(cfg.fields.stress.name) and cfg.fields.stress.name in source.point_data
        if nodal_stress:
            raw = np.asarray(source.point_data[cfg.fields.stress.name], dtype=np.float64)
            for k in range(6):
                probe_src.point_data[f"_sigma{k}"] = raw[:, k]
        bounds = np.asarray(source.bounds, dtype=float)
        tolerance = 1e-6 * float(np.linalg.norm(bounds[1::2] - bounds[0::2]))
        magnitude_rule = stage.get("section_rules", {}).get("displacement_magnitude", "interpolated")
        summary = {"exact_arrays": 0, "exact_tuples": 0, "exact_mismatches": 0,
                   "interpolated_arrays": 0, "interpolated_tuples": 0, "max_interp_nrmse": 0.0,
                   "max_interp_abs_error": {}, "unlocated_section_points": 0, "closest_cell_fallback_points": 0,
                   "fallback_max_abs_error": {}, "probe_disagreements": 0, "vertices_on_discontinuities": 0,
                   "cell_restricted_max_abs_error": {}, "max_jump_across_discontinuity": {},
                   "magnitude_vs_vector_norm": {"max_abs": 0.0, "max_relative_to_span": 0.0},
                   "files": 0, "max_exact_nrmse_vs_float64": 0.0}
        products = [(l, False) for l in stage["layers"]]
        for axis, entries in stage["sections"].items():
            products += [(e | {"axis": axis, "_k": k}, True) for k, e in enumerate(entries)]
        for product, is_section in products:
            path = root / product["file"]
            summary["files"] += 1
            if path.stat().st_size != product["bytes"] or sha256_file(path) != product["sha256"]:
                failures.append(f"{product['file']}: size/hash differs from index")
            mesh = pv.read(path)
            ids = np.asarray(mesh.cell_data["Source_Cell_ID"])
            if not np.issubdtype(ids.dtype, np.integer) or ids.min() < 0 or ids.max() >= source.n_cells:
                failures.append(f"{product['file']}: invalid Source_Cell_ID")
                continue
            for name, ref in cell_ref.items():
                if name not in mesh.cell_data:
                    continue
                m = compare(mesh.cell_data[name], ref[ids])
                rows.append({"stage": stage["id"], "file": product["file"], "check": "exact", "association": "cell",
                             "field": name, **m})
                summary["exact_arrays"] += 1
                summary["exact_tuples"] += m["tuples"]
                if m["nrmse"] is not None and not name.endswith("_ID"):
                    summary["max_exact_nrmse_vs_float64"] = max(summary["max_exact_nrmse_vs_float64"], m["nrmse"])
                if not m["equals_float32_reference"]:
                    summary["exact_mismatches"] += 1
                    failures.append(f"{product['file']}: CellData {name} differs from source")
            for name in mesh.point_data:
                if name in meta and meta[name]["association"] == "cell":
                    failures.append(f"{product['file']}: cell field {name} published as PointData")
                if any(name == f"{c.name}_ID" for c in cfg.fields.categories):
                    failures.append(f"{product['file']}: averaged category {name} in PointData")
            if not is_section:
                if "Source_Point_ID" not in mesh.point_data:
                    failures.append(f"{product['file']}: Source_Point_ID missing on a surface product")
                    continue
                pids = np.asarray(mesh.point_data["Source_Point_ID"])
                if not np.array_equal(np.asarray(mesh.points), np.asarray(source.points[pids], dtype=np.float32)):
                    failures.append(f"{product['file']}: coordinates differ from source nodes")
                for name, ref in point_ref.items():
                    if name not in mesh.point_data:
                        continue
                    m = compare(mesh.point_data[name], ref[pids])
                    rows.append({"stage": stage["id"], "file": product["file"], "check": "exact",
                                 "association": "point", "field": name, **m})
                    summary["exact_arrays"] += 1
                    summary["exact_tuples"] += m["tuples"]
                    if m["nrmse"] is not None:
                        summary["max_exact_nrmse_vs_float64"] = max(summary["max_exact_nrmse_vs_float64"], m["nrmse"])
                    if not m["equals_float32_reference"]:
                        summary["exact_mismatches"] += 1
                        failures.append(f"{product['file']}: PointData {name} differs from source")
            else:
                if "Source_Point_ID" in mesh.point_data:
                    failures.append(f"{product['file']}: section claims Source_Point_ID")
                coords = np.asarray(mesh.points, dtype=np.float64)
                axis_i = "xyz".index(product["axis"])
                residual = float(np.max(np.abs(coords[:, axis_i] - product["value"])))
                if residual > 1e-3 * max(1.0, abs(product["value"])):
                    failures.append(f"{product['file']}: vertices are not on the section plane")
                if product["_k"] % stride:
                    continue
                names = [n for n in point_ref if n in mesh.point_data]
                if not names:
                    continue
                extra = [f"_sigma{k}" for k in range(6)] if nodal_stress else []
                expected, valid, fell_back = probe(probe_src, coords, names + extra, tolerance)
                if nodal_stress:
                    from .fields import principal_values as _pv

                    eig = _pv(np.column_stack([expected.pop(f"_sigma{k}") for k in range(6)]), order)
                    for k, pname in enumerate(("Stress_Min_Principal", "Stress_Mid_Principal", "Stress_Max_Principal")):
                        if pname in expected:
                            expected[pname] = eig[:, k]
                summary["closest_cell_fallback_points"] += int((fell_back & valid).sum())
                if magnitude_rule == "vector_norm" and {"X_Disp", "Y_Disp", "Z_Disp", "TotalDisplacement"} <= set(names):
                    expected["TotalDisplacement"] = np.linalg.norm(
                        np.column_stack([expected[c] for c in ("X_Disp", "Y_Disp", "Z_Disp")]), axis=1)
                summary["unlocated_section_points"] += int((~valid).sum())
                main_pts = valid & ~fell_back
                # vertices whose probe value disagrees noticeably: decide inside the incident source cells
                tol = {n: 1e-5 * (float(np.ptp(point_ref[n])) or 1.0) for n in names}
                flagged = np.zeros(mesh.n_points, dtype=bool)
                for n in names:
                    flagged |= np.abs(np.asarray(mesh.point_data[n], dtype=np.float64) - expected[n]) > tol[n]
                flagged &= valid
                comp = [n for n in names if n != "TotalDisplacement" and not n.endswith("_Principal")] or names
                if flagged.any():
                    worst, n_disc, jump = cell_restricted_check(
                        mesh, probe_src, {n: np.asarray(probe_src.point_data[n]) for n in comp}, np.flatnonzero(flagged),
                        tol)
                    summary["probe_disagreements"] += int(flagged.sum())
                    summary["vertices_on_discontinuities"] += n_disc
                    for n in comp:
                        if worst[n] > 10 * tol[n]:
                            failures.append(f"{product['file']}: {n} on {int(flagged.sum())} vertices matches no "
                                            f"incident source cell (max error {worst[n]:.3e})")
                        summary["cell_restricted_max_abs_error"][n] = max(summary["cell_restricted_max_abs_error"].get(n, 0.0), worst[n])
                        summary["max_jump_across_discontinuity"][n] = max(summary["max_jump_across_discontinuity"].get(n, 0.0), jump[n])
                    main_pts &= ~flagged
                for name in names:
                    fb = fell_back & valid & ~flagged  # flagged vertices are judged in their incident cells
                    if fb.any():
                        err = float(np.max(np.abs(np.asarray(mesh.point_data[name])[fb] - expected[name][fb])))
                        summary["fallback_max_abs_error"][name] = max(summary["fallback_max_abs_error"].get(name, 0.0), err)
                    actual = np.asarray(mesh.point_data[name])[main_pts]
                    m = compare(actual, expected[name][main_pts])
                    m["section_value"] = product["value"]
                    rows.append({"stage": stage["id"], "file": product["file"], "check": "interpolation",
                                 "association": "point", "field": name, **m})
                    summary["interpolated_arrays"] += 1
                    summary["interpolated_tuples"] += m["tuples"]
                    span = float(np.ptp(point_ref[name])) or 1.0
                    summary["max_interp_nrmse"] = max(summary["max_interp_nrmse"], m["rmse"] / span)
                    prev = summary["max_interp_abs_error"].get(name, 0.0)
                    summary["max_interp_abs_error"][name] = max(prev, m["max_abs_error"])
                if {"TotalDisplacement", "X_Disp", "Y_Disp", "Z_Disp"} <= set(mesh.point_data):
                    vec = np.stack([np.asarray(mesh.point_data[c], dtype=np.float64) for c in ("X_Disp", "Y_Disp", "Z_Disp")], 1)
                    diff = np.abs(np.asarray(mesh.point_data["TotalDisplacement"], dtype=np.float64) - np.linalg.norm(vec, axis=1))
                    span = float(np.ptp(point_ref["TotalDisplacement"])) or 1.0
                    mv = summary["magnitude_vs_vector_norm"]
                    mv["max_abs"] = max(mv["max_abs"], float(diff.max()))
                    mv["max_relative_to_span"] = max(mv["max_relative_to_span"], float(diff.max()) / span)
            # recorded ranges must cover the data
            for name in set(mesh.point_data) | set(mesh.cell_data):
                if name not in stage["fields"]:
                    continue
                arr = np.asarray(mesh.cell_data[name] if (meta[name]["association"] == "cell" and name in mesh.cell_data)
                                 else mesh.point_data[name] if name in mesh.point_data else mesh.cell_data[name])
                lo, hi = stage["fields"][name]["min"], stage["fields"][name]["max"]
                if arr.size and (arr.min() < lo or arr.max() > hi):
                    failures.append(f"{product['file']}: {name} outside recorded range")
        summary["failures"] = failures
        report["stages"][stage["id"]] = summary
        report["failures"] += [f"{stage['id']}: {f}" for f in failures]
        log(f"[{stage['id']}] files={summary['files']} exact arrays={summary['exact_arrays']} "
            f"(mismatches {summary['exact_mismatches']}), interpolated arrays={summary['interpolated_arrays']}, "
            f"max interpolation nRMSE={summary['max_interp_nrmse']:.3e}, failures={len(failures)}")
    report["rows"] = rows
    return report


def write_report(report: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = report.pop("rows")
    js = out_dir / "validation_summary.json"
    js.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    cs = out_dir / "validation_pairs.csv"
    keys = ["stage", "file", "check", "association", "field", "tuples", "max_abs_error", "rmse",
            "reference_span", "nrmse", "equals_float32_reference", "section_value"]
    with cs.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    report["rows"] = rows
    return js, cs
