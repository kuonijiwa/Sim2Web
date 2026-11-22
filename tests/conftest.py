"""Synthetic models with known answers, written as VTU files for the tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

#: Linear displacement u(x) = A x + b used by the synthetic models.
A = np.array([[1.0e-3, 2.0e-4, -1.0e-4], [-3.0e-4, 5.0e-4, 2.0e-4], [1.0e-4, -2.0e-4, -8.0e-4]])
B = np.array([1.0e-3, -2.0e-3, 5.0e-4])


def displacement(points):
    return np.asarray(points, dtype=np.float64) @ A.T + B


def make_block_model(n=10, void_box=(3, 7), tetra=False, stress_order="XX,YY,ZZ,XY,YZ,XZ",
                     near_null_cell=False, labels=True, name_components=True):
    """A cube of n^3 unit hexahedra (or tetrahedra) with an excavated box.

    * void cells (centres inside ``void_box``^3) carry exactly zero stress and,
      when ``labels`` is true, the group label ``"null"``;
    * retained cells carry a non-zero stress tensor that varies with position;
    * two retained groups, ``lower`` (z < n/2) and ``upper``;
    * displacement is the linear field :func:`displacement`.
    """
    grid = pv.ImageData(dimensions=(n + 1, n + 1, n + 1), spacing=(1.0, 1.0, 1.0)).cast_to_unstructured_grid()
    if tetra:
        grid = grid.triangulate()
    centers = grid.cell_centers().points
    lo, hi = void_box
    void = np.all((centers > lo) & (centers < hi), axis=1)
    c = centers
    comps = {"XX": -10 - c[:, 2], "YY": -5 - 0.5 * c[:, 2], "ZZ": -20 - 2 * c[:, 2],
             "XY": 0.1 * c[:, 0], "YZ": 0.2 * c[:, 1], "XZ": -0.3 * c[:, 0]}
    order = [k.strip() for k in stress_order.split(",")]
    stress = np.column_stack([comps[k] for k in order])
    stress[void] = 0.0
    if near_null_cell:
        # a retained cell that happens to carry tiny stress (failure mode test)
        k = int(np.flatnonzero(~void)[0])
        stress[k] = 1e-12
    group = np.where(c[:, 2] < n / 2, "lower", "upper").astype("<U8")
    if labels:
        group[void] = "null"
    grid.cell_data["Stress"] = stress
    grid.cell_data["Group"] = group
    grid.point_data["Displacement"] = displacement(grid.points)
    if name_components:  # as written by Itasca's VTU export: ComponentName attributes
        array = grid.GetCellData().GetArray("Stress")
        for i, comp in enumerate(order):
            array.SetComponentName(i, comp)
    return grid, void


def base_config(stage_file: str, **over) -> dict:
    cfg = {
        "schema": "sim2web-config/1",
        "title": "Synthetic block",
        "input": {"stages": [{"file": stage_file, "name": "s1"}]},
        "output": {"dir": "site", "viewer": False},
        "fields": {
            "displacement": {"name": "Displacement", "unit": "m"},
            "stress": {"name": "Stress", "order": "XX,YY,ZZ,XY,YZ,XZ", "unit": "kPa"},
            "categories": [{"name": "Group", "label": "Group"}],
        },
        "geometry": {
            "primary": "exterior",
            "exterior": {"enabled": True, "split_by_group": True},
            "excavation": {"enabled": True, "strategy": "stress", "null_threshold": 1e-8,
                           "contact_tolerance": 1e-6},
            "groups": {"field": "Group"},
            "display_averaging": "per_group",
        },
        "sections": {"axes": ["x", "y", "z"], "spacing": 1.0, "placement": "interior", "min_points": 0},
    }
    for key, value in over.items():
        node = cfg
        parts = key.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value
    return cfg


@pytest.fixture
def block_model(tmp_path: Path):
    grid, void = make_block_model()
    path = tmp_path / "block.vtu"
    grid.save(path)
    return path, grid, void
