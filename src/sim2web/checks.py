"""Plausibility checks on input data that the configuration cannot verify.

``stress_unit_check`` infers the stress unit from the growth of vertical
stress with depth.  Under gravity, |σzz| increases by roughly the unit weight
γ ≈ 15–30 kN/m³ per metre (5–30 kN/m³ allowing for buoyancy and arching),
that is 5e3–3e4 Pa/m, 5–30 kPa/m or 0.005–0.03 MPa/m.  The three candidate
units differ by factors of 1000, so the order of magnitude decides.
"""
from __future__ import annotations

import numpy as np

#: Candidate units and the factor converting 1 unit to Pa.
UNITS = {"Pa": 1.0, "kPa": 1e3, "MPa": 1e6, "GPa": 1e9}
GAMMA_RANGE = (5e3, 3e4)   # Pa per metre


def stress_unit_check(mesh, stress_name: str, zz_column: int, declared: str = "", bins: int = 20) -> dict:
    """Infer the unit of a stress array from its vertical gradient.

    The gradient is the slope of a straight line fitted to the median σzz of
    horizontal slices (``bins`` equal z intervals) of the stressed cells.  The
    slope does not depend on stresses applied at the model top, so models whose
    top boundary is not the ground surface are handled.
    """
    if stress_name in mesh.cell_data:
        s = np.asarray(mesh.cell_data[stress_name], dtype=np.float64)
        coords = np.asarray(mesh.cell_centers().points, dtype=np.float64)
    else:
        s = np.asarray(mesh.point_data[stress_name], dtype=np.float64)
        coords = np.asarray(mesh.points, dtype=np.float64)
    keep = ~np.all(np.abs(s) < 1e-30, axis=1)
    z = coords[keep, 2]
    szz = s[keep, zz_column]
    if szz.size < 100 or np.ptp(z) <= 0:
        return {"status": "not enough stressed cells"}
    edges = np.linspace(z.min(), z.max(), bins + 1)
    idx = np.clip(np.digitize(z, edges) - 1, 0, bins - 1)
    zc, med = [], []
    for k in range(bins):
        sel = idx == k
        if sel.sum() >= 20:
            zc.append(z[sel].mean())
            med.append(np.median(szz[sel]))
    if len(zc) < 4:
        return {"status": "not enough depth bins"}
    slope, intercept = np.polyfit(zc, med, 1)        # σzz per metre of elevation
    resid = np.asarray(med) - (slope * np.asarray(zc) + intercept)
    r2 = 1 - float(np.sum(resid ** 2)) / float(np.sum((np.asarray(med) - np.mean(med)) ** 2) or 1)
    gradient = abs(float(slope))
    result = {"status": "ok", "gradient_per_m": gradient, "fit_r2": r2, "bins_used": len(zc),
              "compression_increases_with_depth": bool(slope > 0)}   # σzz more negative at depth
    consistent = []
    for unit, factor in UNITS.items():
        gamma = gradient * factor
        result[f"implied_unit_weight_kN_m3_if_{unit}"] = gamma / 1e3
        if GAMMA_RANGE[0] * 0.5 <= gamma <= GAMMA_RANGE[1] * 2:
            consistent.append(unit)
    result["consistent_units"] = consistent
    if declared:
        result["declared"] = declared
        result["declared_consistent"] = declared in consistent
    return result
