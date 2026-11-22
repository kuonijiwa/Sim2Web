import json, sys
from pathlib import Path
import numpy as np
import pyvista as pv
from scipy.spatial import cKDTree

old,last,first,out = map(Path,sys.argv[1:])
m3,m4,m0 = (pv.read(p) for p in (old,last,first))
def coords(reference, target):
    dist, ids=cKDTree(reference.points).query(target.points)
    assert len(set(ids)) == len(reference.points) == len(target.points)
    return ids,float(dist.max())
ids, err = coords(m3,m4)
time_ids, time_coord_err = coords(m0,m4)
def cell_keys(grid, point_ids):
    return [tuple(sorted(point_ids[grid.get_cell(i).point_ids])) for i in range(grid.n_cells)]
lookup={k:i for i,k in enumerate(cell_keys(m3,np.arange(m3.n_points)))}
cells=[lookup[k] for k in cell_keys(m4,ids)]
npd=m4.GetPointData().GetArray("disp")
ncd=m4.GetCellData().GetArray("stress")
opd=m3.GetPointData().GetArray("Displacement")
ocd=m3.GetCellData().GetArray("Stress")
def names(arr):
    return [arr.GetComponentName(i) for i in range(arr.GetNumberOfComponents())]
n=[s.upper().replace("ZX","XZ") for s in names(ncd)]
o=[s.upper().replace("ZX","XZ") for s in names(ocd)]
aligned=m3.cell_data["Stress"][cells][:,[o.index(s) for s in n]]
d_err=np.max(np.abs(m4.point_data["disp"]-m3.point_data["Displacement"][ids]),axis=0)
s_err=np.max(np.abs(m4.cell_data["stress"]-aligned),axis=0)
data=dict(points=m4.n_points,cells=m4.n_cells,r3_disp_components=names(opd),r4_disp_components=names(npd),
          r3_stress_components=names(ocd),r4_stress_components=names(ncd),
          r3_r4_coordinate_max_distance=err,r4_first_last_coordinate_max_distance=time_coord_err,
          displacement_max_abs_by_component=d_err.tolist(), stress_max_abs_by_component=s_err.tolist(),
          displacement_max_abs=float(d_err.max()),stress_max_abs=float(s_err.max()),
          comparison="Matched vertices by coordinates, then cells by vertex sets; equivalent ZX/XZ labels aligned.")
out.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
print(json.dumps(data,indent=2))
