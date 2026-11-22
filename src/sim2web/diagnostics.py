"""Robustness studies: excavation-boundary sensitivity and analytical-field checks."""
from __future__ import annotations

import itertools

import numpy as np
import pyvista as pv

from .config import CaseConfig
from .fields import attach_source_ids, category_output_name, derive_fields
from .geometry import (excavation_boundary, partition, section_per_group, section_positions, section_whole,
                       with_display_points)
from .regions import label_void_mask, max_abs_stress, stress_void_mask


def _boundary_ids(solid, void, tolerance):
    surf = excavation_boundary(solid, void, tolerance)
    if surf is None or surf.n_cells == 0:
        return set(), 0.0, 0, 0
    regions = int(surf.connectivity().cell_data["RegionId"].max() + 1)
    return set(np.asarray(surf.cell_data["Source_Cell_ID"]).tolist()), float(surf.area), int(surf.n_cells), regions


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def excavation_sensitivity(cfg: CaseConfig, stage: str | None = None, thresholds=None, tolerances=None, log=print):
    """Sweep the stress null threshold and contact tolerance.

    For every combination the void-cell count, boundary face count, boundary
    area, number of connected boundary regions and the Jaccard index of the
    boundary's ``Source_Cell_ID`` set relative to the configured baseline are
    reported.  When label fields with void tokens exist, the label-based
    boundary is used as an additional reference.
    """
    exc = cfg.geometry.excavation
    spec = next(s for s in cfg.resolved_stages() if stage in (None, s.name))
    mesh = pv.read(spec.file)
    derive_fields(mesh, cfg, cfg.resolve_stress_order(spec.file)[0] if cfg.fields.stress.name else None)
    attach_source_ids(mesh)
    stress = cfg.fields.stress.name
    if not stress:
        raise ValueError("Sensitivity analysis needs fields.stress.name")
    thresholds = thresholds or [exc.null_threshold * f for f in (1e-2, 1e-1, 1.0, 1e1, 1e2)]
    tolerances = tolerances or [exc.contact_tolerance * f for f in (0.1, 1.0, 10.0)]
    m = max_abs_stress(mesh, stress)

    def boundary_for(mask, tol):
        solid = mesh.extract_cells(~mask)
        void = mesh.extract_cells(mask)
        return _boundary_ids(solid, void, tol)

    base_mask = stress_void_mask(mesh, stress, exc.null_threshold)
    baseline = boundary_for(base_mask, exc.contact_tolerance)
    references = {"baseline": baseline[0]}
    lmask, used = label_void_mask(mesh, exc.label_fields or cfg.category_names, exc.label_tokens)
    if used:
        references["labels"] = boundary_for(lmask, exc.contact_tolerance)[0]
    rows = []
    for thr, tol in itertools.product(thresholds, tolerances):
        mask = stress_void_mask(mesh, stress, thr)
        ids, area, faces, regions = boundary_for(mask, tol)
        row = {"stage": spec.name, "null_threshold": thr, "contact_tolerance": tol, "void_cells": int(mask.sum()),
               "boundary_faces": faces, "boundary_area": area, "boundary_regions": regions,
               "jaccard_vs_baseline": _jaccard(ids, references["baseline"])}
        if "labels" in references:
            row["jaccard_vs_labels"] = _jaccard(ids, references["labels"])
            row["void_cells_vs_labels_jaccard"] = float((mask & lmask).sum() / max(1, (mask | lmask).sum()))
        rows.append(row)
        log(f"thr={thr:.1e} tol={tol:.1e}: void={row['void_cells']} faces={faces} area={area:.3f} "
            f"J={row['jaccard_vs_baseline']:.4f}")
    # distribution gap: how many cells fall in each decade of max |stress|
    positive = m[m > 0]
    gap = {"zero_stress_cells": int((m == 0).sum()),
           "smallest_nonzero_max_abs_stress": float(positive.min()) if positive.size else None,
           "cells_below": {f"{t:.0e}": int((m < t).sum()) for t in sorted(set(thresholds))}}
    return {"stage": spec.name, "baseline": {"null_threshold": exc.null_threshold,
                                              "contact_tolerance": exc.contact_tolerance,
                                              "boundary_faces": baseline[2], "boundary_area": baseline[1]},
            "label_reference": used, "stress_distribution": gap, "rows": rows}


def analytical_interpolation_check(cfg: CaseConfig, stage: str | None = None, per_axis: int = 5,
                                   coefficients=None, log=print):
    """Replace the displacement with a linear field and verify section values.

    With ``u(x) = A x + b`` every supported linear cell type interpolates
    ``u`` exactly along its edges, so the section vertices must reproduce the
    analytical value to rounding error.  The magnitude field is *not* linear,
    and the check also reports how far the interpolated magnitude departs from
    the norm of the interpolated vector.
    """
    spec = next(s for s in cfg.resolved_stages() if stage in (None, s.name))
    mesh = pv.read(spec.file)
    disp = cfg.fields.displacement.name
    if not disp:
        raise ValueError("The analytical check needs fields.displacement.name")
    rng = np.random.default_rng(20261120)
    A = np.asarray(coefficients if coefficients is not None else rng.uniform(-1e-3, 1e-3, (3, 3)))
    b = np.array([1e-3, -2e-3, 5e-4])
    p = np.asarray(mesh.points, dtype=np.float64)
    center = p.mean(axis=0)

    def u(points):
        return (np.asarray(points, dtype=np.float64) - center) @ A.T + b

    mesh.point_data[disp] = u(p)
    derive_fields(mesh, cfg, cfg.resolve_stress_order(spec.file)[0] if cfg.fields.stress.name else None)
    attach_source_ids(mesh)
    from .regions import identify_void

    void = identify_void(mesh, cfg)
    geo = cfg.geometry
    group = category_output_name(geo.groups.field) if geo.groups.field else None
    part = partition(mesh, void.mask, group, geo.groups.constant_fallback)
    per_group = geo.display_averaging == "per_group" and part.group_codes is not None
    blocks = [with_display_points(bk) for bk in part.blocks] if per_group else None
    whole = None if per_group else with_display_points(part.solid)
    positions = section_positions(part.solid.bounds, cfg.sections)
    rows = []
    for axis, values in positions.items():
        if not len(values):
            continue
        pick = np.unique(np.linspace(0, len(values) - 1, min(per_axis, len(values))).round().astype(int))
        for value in np.asarray(values)[pick]:
            cut = (section_per_group(blocks, axis, value, cfg.sections.min_points) if per_group
                   else section_whole(whole, axis, value, cfg.sections.min_points))
            if cut is None:
                continue
            pts = np.asarray(cut.points)
            exact = u(pts)
            # The cutter stores new vertices with the precision of the input
            # points; the analytical field evaluated at the stored (rounded)
            # coordinates differs from the interpolated value by |A dx|.
            ulp = np.spacing(np.abs(pts).astype(pts.dtype)).astype(np.float64)
            bound = float(np.max(np.abs(A) @ (0.5 * ulp.T)) * 1.01 + 1e-300) if pts.dtype == np.float32 \
                else float(np.max(np.abs(exact)) * 1e-13)
            vec = np.stack([np.asarray(cut.point_data[c], dtype=np.float64) for c in ("X_Disp", "Y_Disp", "Z_Disp")], 1)
            err = np.abs(vec - exact)
            scale = float(np.max(np.abs(exact))) or 1.0
            mag_interp = np.asarray(cut.point_data["TotalDisplacement"], dtype=np.float64)
            mag_exact = np.linalg.norm(exact, axis=1)
            rows.append({"axis": axis, "value": float(value), "points": int(cut.n_points),
                         "point_precision": str(pts.dtype), "coordinate_rounding_bound": bound,
                         "within_rounding_bound": bool(err.max() <= bound),
                         "max_abs_error_float64": float(err.max()), "max_relative_error_float64": float(err.max() / scale),
                         "max_abs_error_after_float32": float(np.max(np.abs(vec.astype(np.float32).astype(np.float64) - exact))),
                         "magnitude_interp_minus_exact_max": float(np.max(mag_interp - mag_exact)),
                         "magnitude_interp_minus_exact_min": float(np.min(mag_interp - mag_exact)),
                         "magnitude_relative_to_max": float(np.max(np.abs(mag_interp - mag_exact)) / max(mag_exact.max(), 1e-300))})
            log(f"{axis}={value:g}: {cut.n_points} pts, max rel. error {rows[-1]['max_relative_error_float64']:.2e}")
    return {"stage": spec.name, "field": "u(x) = A (x - c) + b", "A": A.tolist(), "b": b.tolist(),
            "c": center.tolist(), "rows": rows,
            "max_relative_error_float64": max((r["max_relative_error_float64"] for r in rows), default=None),
            "all_within_rounding_bound": all(r["within_rounding_bound"] for r in rows)}
