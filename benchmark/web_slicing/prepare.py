"""Prepare the public A/C study without altering Sim2Web sources."""
import argparse
import gzip
import json
import shutil
from pathlib import Path

import numpy as np
import pyvista as pv
import vtk
from vtk.util.numpy_support import vtk_to_numpy

from sim2web.config import load_config
from sim2web.geometry import with_display_points
from sim2web.regions import identify_void

ROOT = Path(__file__).resolve().parents[2]
CONFIG = {"A": "flac3d_cavern_iv2", "C": "3dec_slope"}
SUPPORTED = {10, 11, 12, 13, 14}

def read_case(case):
    cfg = load_config(ROOT / "examples" / CONFIG[case] / "sim2web.yaml")
    path = Path(cfg.resolved_stages()[0].file)
    grid = pv.read(path)
    retained = ~identify_void(grid, cfg).mask
    name = cfg.fields.displacement.name
    if name not in grid.point_data:
        grid = with_display_points(grid)
    vectors = np.asarray(grid.point_data[name])[:, :3]
    return path, grid, vectors, retained

def retained_grid(grid, vectors, mask):
    # Use the source precision as the reference. Keep point connectivity, including
    # distinct nodes on opposite sides of a joint.
    result = pv.UnstructuredGrid(grid.cells, grid.celltypes, grid.points)
    result.point_data["TotalDisplacement"] = np.linalg.norm(vectors.astype(np.float64), axis=1)
    if not mask.all():
        result = result.extract_cells(mask)
    result.set_active_scalars("TotalDisplacement", preference="point")
    return result

def cutter_for(mesh):
    plane = vtk.vtkPlane()
    plane.SetNormal(1, 0, 0)
    algo = vtk.vtkCutter()
    algo.SetInputData(mesh)
    algo.SetCutFunction(plane)
    algo.SetLocator(vtk.vtkNonMergingPointLocator())
    algo.GenerateTrianglesOn()
    return plane, algo

def capture(obj, file):
    arr = lambda a: np.asarray(vtk_to_numpy(a))
    polys = obj.GetPolys()
    np.savez_compressed(file, points=arr(obj.GetPoints().GetData()),
        values=arr(obj.GetPointData().GetArray("TotalDisplacement")),
        connectivity=arr(polys.GetConnectivityArray()).reshape(-1,3))

def prepare(case, site, out):
    out.mkdir(parents=True, exist_ok=True)
    index = json.loads((site / "model_cache/index.json").read_text(encoding="utf-8"))
    stage = index["stages"][0]
    section = stage["sections"]["x"]
    # Same endpoint-inclusive rounding as benchmark/browser_benchmark.mjs.
    indices = np.floor(np.linspace(0, len(section)-1, 10)+0.5).astype(int)
    picked = [section[i]["value"] for i in indices]
    path, grid, vectors, mask = read_case(case)
    celltypes, counts = np.unique(grid.celltypes, return_counts=True)
    assert set(celltypes) <= SUPPORTED, celltypes
    cells = np.asarray(grid.cell_connectivity, dtype="<i4")
    arrays = [np.array([0x36574153, grid.n_points, grid.n_cells, len(cells)], dtype="<i4"),
              np.asarray(grid.points, dtype="<f4"), np.asarray(grid.offset, dtype="<i4"),
              cells, np.asarray(grid.celltypes, dtype="<i4"),
              np.asarray(vectors, dtype="<f4"), np.asarray(mask, dtype="<i4")]
    raw = out / "volume.bin"
    with raw.open("wb") as f:
        for arr in arrays:
            arr.tofile(f)
    zipper = out / "volume.bin.gz"
    with raw.open("rb") as f, gzip.open(zipper, "wb", compresslevel=6) as g:
        shutil.copyfileobj(f, g)
    used = retained_grid(grid, vectors, mask)
    plane, cutter = cutter_for(used)
    checked = [0,4,9]
    for j in checked:
        plane.SetOrigin(picked[j], 0, 0)
        cutter.Update()
        capture(cutter.GetOutput(), out / f"reference_{j}.npz")
    # A second independent VTK reference honours the exact precision of the
    # browser's published Float32 transport.
    quantized = pv.UnstructuredGrid(grid.cells, grid.celltypes, np.asarray(grid.points,dtype=np.float32))
    browser_mesh = retained_grid(quantized, vectors.astype(np.float32), mask)
    q_plane, q_cutter = cutter_for(browser_mesh)
    for j in checked:
        q_plane.SetOrigin(picked[j],0,0)
        q_cutter.Update()
        capture(q_cutter.GetOutput(), out / f"reference_browser_{j}.npz")
    b = np.array(used.bounds).reshape(3,2)
    center = b.mean(axis=1)
    focal = center.tolist()
    camera = [float(center[0]+4*np.ptp(b,axis=1).max()),float(center[1]),float(center[2]),*focal,0,0,1,float(max(b[2,1]-b[2,0],(b[1,1]-b[1,0])*.62)*.58)]
    stats = stage["fields"]["TotalDisplacement"]
    all_fields = [x["id"] for x in stage["layers"]]
    info = {"case":case, "source":str(path), "source_bytes":path.stat().st_size, "points":grid.n_points,
            "cells":grid.n_cells,"retained_cells":int(mask.sum()),"vtk_cell_types":dict(zip(map(int,celltypes),map(int,counts))),
            "binary_bytes":raw.stat().st_size,"gzip_bytes":zipper.stat().st_size,"gzip_level":6,
            "positions":picked,"w_indices":indices.tolist(),"first_index":4,"correctness_indices":checked,
            "camera":camera,"projection":"parallel, x-normal", "viewport":[1600,900],"layers":all_fields,
            "range":[stats["min"],stats["max"]],"range_mode":"full","colormap":index["viewer"]["colormap"],"bands":index["viewer"]["bands"],
            "retained_filter":"Apply the shipped void rule after receiving whole topology.",
            "field":"TotalDisplacement, interpolate nodal magnitude as the shipped viewer does. Source point vectors require no cell-data averaging."}
    (out / "case.json").write_text(json.dumps(info,indent=2)+"\n", encoding="utf-8")
    print(json.dumps(info,indent=2))

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("case",choices=CONFIG)
    p.add_argument("site",type=Path)
    p.add_argument("out",type=Path)
    a=p.parse_args()
    prepare(a.case,a.site,a.out)
