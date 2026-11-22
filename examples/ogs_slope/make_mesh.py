"""Generate the OpenGeoSys input meshes for Case E (two-layer slope under gravity).

    python make_mesh.py            # writes slope.vtu and boundary meshes into model/
    ogs slope.prj -o input                        # OpenGeoSys 6.5 (pip install ogs==6.5.9)

The result input/slope_result_ts_1_t_1.000000.vtu is the input of sim2web.yaml.
"""
from pathlib import Path

import numpy as np
import pyvista as pv

OUT = Path(__file__).parent / "model"
OUT.mkdir(exist_ok=True)
nx, ny, nz = 48, 16, 20
L, W = 160.0, 60.0


def ztop(x, y):
    """Crest at 60 m, bench at 40-42 m, toe at 20 m, gentle undulation along y."""
    return np.interp(x, [0, 60, 78, 86, 104, 160], [60, 60, 42, 40, 20, 20]) + 3 * np.sin(y / W * np.pi)


xs, ys, ts = np.linspace(0, L, nx + 1), np.linspace(0, W, ny + 1), np.linspace(0, 1, nz + 1)
X, Y, T = np.meshgrid(xs, ys, ts, indexing="ij")
Z = -40 + T * (ztop(X, Y) + 40)
grid = pv.StructuredGrid(X, Y, Z).cast_to_unstructured_grid()
c = grid.cell_centers().points
weak = (c[:, 2] > 10 - 0.15 * (c[:, 0] - 80)) & (c[:, 2] < 16 - 0.15 * (c[:, 0] - 80))   # weak layer
grid.cell_data["MaterialIDs"] = weak.astype(np.int32)
grid.point_data.clear()
grid.save(OUT / "slope.vtu")

p = grid.points
for name, sel in {"bottom": np.abs(p[:, 2] - p[:, 2].min()) < 1e-6, "xmin": np.abs(p[:, 0]) < 1e-6,
                  "xmax": np.abs(p[:, 0] - L) < 1e-6, "ymin": np.abs(p[:, 1]) < 1e-6,
                  "ymax": np.abs(p[:, 1] - W) < 1e-6}.items():
    ids = np.flatnonzero(sel)
    m = pv.UnstructuredGrid({1: np.arange(len(ids)).reshape(-1, 1)}, p[ids])
    m.point_data["bulk_node_ids"] = ids.astype(np.uint64)
    m.save(OUT / f"{name}.vtu")
print(f"{grid.n_points} nodes, {grid.n_cells} hexahedra, {int(weak.sum())} in the weak layer")
