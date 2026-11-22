"""Small read-only checks shared by the packaged examples and tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv


def mesh_summary(path: str | Path) -> dict[str, object]:
    """Read a VTU/VTP file and report basic topology and field associations."""
    mesh = pv.read(Path(path))
    if mesh.n_points <= 0 or mesh.n_cells <= 0:
        raise ValueError(f"Mesh is empty: {path}")
    faces = mesh.extract_surface().triangulate().faces.reshape(-1, 4)[:, 1:]
    if faces.size and (faces.min() < 0 or faces.max() >= mesh.extract_surface().triangulate().n_points):
        raise ValueError(f"Invalid point index in: {path}")
    return {
        "points": int(mesh.n_points),
        "cells": int(mesh.n_cells),
        "point_arrays": sorted(mesh.point_data.keys()),
        "cell_arrays": sorted(mesh.cell_data.keys()),
    }


def section_plane_residual(path: str | Path) -> float:
    """Return the smallest max residual to an axis-aligned section plane."""
    points = np.asarray(pv.read(Path(path)).points, dtype=float)
    if not len(points):
        raise ValueError(f"Section has no points: {path}")
    residuals = [float(np.max(np.abs(points[:, axis] - np.median(points[:, axis])))) for axis in range(3)]
    return min(residuals)
