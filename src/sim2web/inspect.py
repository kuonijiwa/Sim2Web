"""Input inspection: report what a VTU contains and draft a configuration."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv

_CELL_TYPES = {10: "tetra", 12: "hexahedron", 13: "wedge", 14: "pyramid", 5: "triangle", 9: "quad"}


def inspect_vtu(path: str | Path) -> dict:
    from .vtkxml import component_names

    names = component_names(path)
    mesh = pv.read(Path(path))
    types, counts = np.unique(mesh.celltypes, return_counts=True)
    info = {"file": Path(path).name, "points": int(mesh.n_points), "cells": int(mesh.n_cells),
            "bounds": [float(b) for b in mesh.bounds],
            "cell_types": {_CELL_TYPES.get(int(t), str(int(t))): int(c) for t, c in zip(types, counts)},
            "point_arrays": {}, "cell_arrays": {}}
    six = lambda c: [n for n in c if np.asarray(c[n]).ndim == 2 and np.asarray(c[n]).shape[1] == 6
                     and not n.lower().startswith(("eps", "strain"))]
    stress = next(iter(six(mesh.cell_data) + six(mesh.point_data)), None)
    if stress:
        from .checks import stress_unit_check

        zz = names.get(stress, ["XX", "YY", "ZZ"]).index("ZZ") if "ZZ" in names.get(stress, ["XX", "YY", "ZZ"]) else 2
        info["stress_unit_check"] = {"array": stress, **stress_unit_check(mesh, stress, zz)}
    for assoc, container in (("point_arrays", mesh.point_data), ("cell_arrays", mesh.cell_data)):
        for name in container:
            arr = np.asarray(container[name])
            entry = {"dtype": str(arr.dtype), "components": 1 if arr.ndim == 1 else int(arr.shape[1])}
            if name in names:
                entry["component_names"] = names[name]
            if arr.dtype.kind in "USO" or (arr.ndim == 1 and arr.dtype.kind in "iub"):
                values = np.unique(arr)
                entry["unique_values"] = int(values.size)
                entry["examples"] = [str(v) for v in values[:8]]
            elif arr.size:
                entry["min"], entry["max"] = float(np.min(arr)), float(np.max(arr))
            info[assoc][name] = entry
    return info


def draft_config(info: dict, stage_file: str) -> str:
    """A starting configuration; every guessed value is marked for review."""
    disp = next((n for n, e in info["point_arrays"].items() if e["components"] == 3), "")
    candidates = [n for n, e in {**info["cell_arrays"], **info["point_arrays"]}.items()
                  if e["components"] == 6 and not n.lower().startswith(("eps", "strain"))]
    stress = info.get("stress_unit_check", {}).get("array") or (candidates[0] if candidates else "")
    named = {**info["point_arrays"], **info["cell_arrays"]}.get(stress, {}).get("component_names")
    check = info.get("stress_unit_check", {})
    units = check.get("consistent_units", [])
    if len(units) == 1:
        unit_line = (f"unit: {units[0]}                       # vertical gradient implies "
                     f"{check[f'implied_unit_weight_kN_m3_if_{units[0]}']:.1f} kN/m3 in {units[0]}; REVIEW")
    else:
        unit_line = "unit: Pa                        # REVIEW unit: the gravity check was inconclusive"
    if named:
        order_line = f"order: from_file                # the file declares {','.join(named)}"
    else:
        order_line = 'order: "XX,YY,ZZ,XY,XZ,YZ"     # REVIEW: the file does not name the components'
    cats = [n for n, e in info["cell_arrays"].items() if "unique_values" in e and e["components"] == 1]
    lines = [
        "schema: sim2web-config/1",
        f"title: \"{Path(stage_file).stem}\"",
        "solver: \"\"            # REVIEW: e.g. FLAC3D 9.0",
        "input:",
        "  stages:",
        f"    - file: {stage_file}",
        "output:",
        "  dir: site",
        "fields:",
        f"  displacement: {{name: \"{disp}\", unit: m}}          # REVIEW unit",
        "  stress:",
        f"    name: \"{stress}\"",
        f"    {order_line}",
        f"    {unit_line}",
        "    sign_convention: \"tension positive\"   # REVIEW sign",
        "  categories:",
    ]
    lines += [f"    - {{name: \"{c}\", label: \"{c}\"}}" for c in cats] or ["    []"]
    lines += [
        "geometry:",
        "  primary: exterior       # or: excavation",
        "  exterior: {enabled: true, split_by_group: true}",
        "  excavation:",
        "    enabled: false        # REVIEW: true for underground models",
        "    strategy: labels_then_stress",
        "    null_threshold: 1.0e-8",
        "    contact_tolerance: 1.0e-3",
        f"  groups: {{field: \"{cats[0] if cats else ''}\"}}",
        "  display_averaging: per_group",
        "sections:",
        "  axes: [x, y, z]",
        "  spacing: 10",
        "  placement: integer_grid",
        "viewer:",
        "  colormap: jet",
        "  bands: 8",
    ]
    return "\n".join(lines) + "\n"
