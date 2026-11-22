"""Principal stresses as a generic VTK/ParaView pipeline computes them.

ParaView's "Tensor Principal Invariants" filter is VTK's
``vtkTensorPrincipalInvariants``.  It reads a six-component array in VTK's
symmetric-tensor order (XX, YY, ZZ, XY, YZ, XZ) and does not look at the
``ComponentName`` attributes written by the exporter.  This script applies the
filter to a VTU exactly as ParaView would and compares the result with the
principal stresses computed in the component order the file declares.

    python benchmark/paraview_principal_check.py model.vtu --array Stress \
        --null-threshold 1e-8 --out result.json

Runs with the VTK Python package (no ParaView needed) because the filter is
the same code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import vtk

from sim2web.fields import principal_values
from sim2web.vtkxml import component_names

VTK_ORDER = ["XX", "YY", "ZZ", "XY", "YZ", "XZ"]


def check(path: Path, array: str, null_threshold: float) -> dict:
    declared = component_names(path).get(array)
    mesh = pv.read(path)
    stress = np.asarray(mesh.cell_data[array], dtype=np.float64)
    retained = np.abs(stress).max(axis=1) > null_threshold
    flt = vtk.vtkTensorPrincipalInvariants()
    flt.SetInputData(mesh)
    flt.Update()
    out = pv.wrap(flt.GetOutput())
    generic = np.sort(np.column_stack([np.asarray(out.cell_data[f"{array} - Sigma {k}"]) for k in (1, 2, 3)]),
                      axis=1)
    as_vtk = principal_values(stress, VTK_ORDER)
    result = {
        "file": path.name, "array": array, "cells": int(mesh.n_cells), "retained_cells": int(retained.sum()),
        "component_names_in_file": declared, "vtk_filter_order": ",".join(VTK_ORDER),
        "vtk_filter_matches_vtk_order": bool(np.allclose(generic[retained], as_vtk[retained], rtol=1e-6, atol=1e-6)),
        "principal": {},
    }
    if not declared:
        result["note"] = "the file does not name its components; no reference order"
        return result
    correct = principal_values(stress, declared)
    result["vtk_filter_matches_file_order"] = bool(np.allclose(generic[retained], correct[retained],
                                                               rtol=1e-6, atol=1e-6))
    for k, name in enumerate(("min", "mid", "max")):
        ref, got = correct[retained, k], generic[retained, k]
        err = np.abs(got - ref)
        span = float(np.ptp(ref)) or 1.0
        result["principal"][name] = {
            "correct_range": [float(ref.min()), float(ref.max())],
            "generic_range": [float(got.min()), float(got.max())],
            "max_abs_error": float(err.max()),
            "max_error_percent_of_range": 100 * float(err.max()) / span,
            "cells_error_over_1pct_of_range": int((err > 0.01 * span).sum()),
            "cells_positive_generic_but_not_correct": int(((got > 0) & (ref <= 0)).sum()) if name == "max" else None,
        }
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vtu", type=Path)
    ap.add_argument("--array", default="Stress")
    ap.add_argument("--null-threshold", type=float, default=1e-8)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    result = check(a.vtu, a.array, a.null_threshold)
    text = json.dumps(result, indent=2)
    print(text)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
