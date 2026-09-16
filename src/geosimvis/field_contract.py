"""Publication revision: explicit array roles and source provenance, not geometry logic."""
from pathlib import Path
import numpy as np

POINT_ID = "Source_Point_ID"
CELL_ID = "Source_Cell_ID"
DISPLAY_SUFFIX = "_DisplayOnly"


def is_category(name):
    return name not in (POINT_ID, CELL_ID) and any(
        token in name.lower() for token in ("group", "material", "state", "plastic", "_id", "block", "region", "slot")
    )


def attach_source_ids(mesh):
    """Call after source-derived fields, before any selection or cell-to-point filter."""
    mesh.point_data[POINT_ID] = np.arange(mesh.n_points, dtype=np.int64)
    mesh.cell_data[CELL_ID] = np.arange(mesh.n_cells, dtype=np.int64)


def prepare_output(mesh, path, ranges):
    """Remove averaged categories, label display stress, and accumulate output ranges."""
    for name in list(mesh.point_data):
        if is_category(name) or name == CELL_ID or (name == POINT_ID and Path(path).name.startswith("slice_")):
            del mesh.point_data[name]
        elif name.startswith("Stress_") and not name.endswith(DISPLAY_SUFFIX):
            mesh.point_data[name + DISPLAY_SUFFIX] = mesh.point_data[name].copy()
            del mesh.point_data[name]
    for name in (CELL_ID,):
        if name not in mesh.cell_data:
            raise ValueError("Source cell provenance was lost before writing")
    # Unreliable filter-local IDs are not exposed as source provenance.
    for container in (mesh.point_data, mesh.cell_data):
        for name in list(container):
            if name.startswith("vtkOriginal"):
                del container[name]
    names = set(mesh.point_data) | set(mesh.cell_data)
    for name in sorted(names):
        if name in (POINT_ID, CELL_ID) or name.endswith(DISPLAY_SUFFIX):
            continue
        container = mesh.cell_data if name in mesh.cell_data and (is_category(name) or name.startswith("Stress_")) else mesh.point_data
        if name not in container:
            continue
        values = np.asarray(container[name])
        if values.ndim != 1 or not np.issubdtype(values.dtype, np.number):
            continue
        if not np.all(np.isfinite(values)):
            raise ValueError(f"Nonfinite output scalar {name}")
        lo, hi = float(values.min()), float(values.max())
        previous = ranges.get(name, [lo, hi])
        ranges[name] = [min(lo, previous[0]), max(hi, previous[1])]


def public_field(name):
    return name not in (POINT_ID, CELL_ID) and not name.endswith(DISPLAY_SUFFIX) and not name.startswith("vtkOriginal")
