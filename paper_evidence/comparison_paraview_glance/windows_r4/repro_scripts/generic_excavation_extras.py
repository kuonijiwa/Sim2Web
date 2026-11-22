import json,sys
from pathlib import Path
import numpy as np
import pyvista as pv
from scipy.spatial import cKDTree
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

case,source,baseline,simsite,out = sys.argv[1:]
volume=pv.read(source)
surface=pv.read(baseline)
raw_surface_faces=surface.n_cells
def polygons(poly):
    cells=poly.GetPolys()
    return vtk_to_numpy(cells.GetOffsetsArray()),vtk_to_numpy(cells.GetConnectivityArray())
def locations(poly):
    line,indices=polygons(poly)
    n=np.diff(line)
    xyz=np.asarray(poly.points,dtype=float)[indices]
    face_order=np.repeat(np.arange(poly.n_cells),n)
    centers=np.zeros((poly.n_cells,3))
    np.add.at(centers,face_order,xyz)
    return centers/n[:,None],n,xyz,face_order
if case=="A":
    void=np.max(np.abs(volume.cell_data["Stress"]),axis=1)<=1e-8
    air=volume.extract_cells(void).extract_surface()
    distance=cKDTree(air.points).query(surface.points)[0]
    product=surface.extract_points(distance<1e-5).extract_surface().clean()
    extra={"void_cells":int(void.sum()),"tolerance_m":1e-5}
else:
    ctr,n,xyz,office=locations(surface)
    bounds=np.asarray(volume.bounds).reshape(3,2)
    on_box=np.zeros(surface.n_cells,dtype=bool)
    for axis,(lower,upper) in enumerate(bounds):
        for h in (lower,upper):
            on_box |= np.bincount(office,weights=(abs(xyz[:,axis]-h)<=.001))==n
    ids=np.flatnonzero(~on_box)
    surface=surface.extract_cells(ids).extract_surface().clean()
    ctr,n,xyz,office=locations(surface)
    normals=np.asarray(surface.compute_normals(point_normals=False,consistent_normals=False).cell_data["Normals"],dtype=float)
    area=np.asarray(surface.compute_cell_sizes(length=False,volume=False).cell_data["Area"])
    scale=.02*np.sqrt(np.maximum(area,1e-300))
    q=np.vstack((ctr,(ctr[office]+xyz)/2))
    face_ids=np.r_[np.arange(surface.n_cells),office]
    shift=normals[face_ids]*scale[face_ids,None]
    p=vtk.vtkPoints()
    p.SetData(numpy_to_vtk(np.vstack((q+shift,q-shift)),deep=True))
    targets=vtk.vtkPolyData()
    targets.SetPoints(p)
    probe=vtk.vtkProbeFilter()
    probe.SetInputData(targets)
    solid=pv.UnstructuredGrid(volume.cells,volume.celltypes,np.asarray(volume.points,dtype=float))
    solid.cell_data["_solid"]=np.ones(solid.n_cells,dtype=np.uint8)
    probe.SetSourceData(solid)
    probe.ComputeToleranceOff()
    probe.SetTolerance(1e-9 * np.linalg.norm(bounds[:,1]-bounds[:,0]))
    probe.SetFindCellStrategy(vtk.vtkCellLocatorStrategy())
    probe.Update()
    hits=vtk_to_numpy(probe.GetOutput().GetPointData().GetArray("vtkValidPointMask")).astype(bool)
    has_open_side=np.bincount(face_ids,weights=~(hits[:len(q)] & hits[len(q):]))>0
    product=surface.extract_cells(has_open_side).extract_surface().clean()
    extra={"box_faces_removed":int(on_box.sum()),"faces_with_solid_both_sides_removed":int((~has_open_side).sum()),"domain_tolerance_m":0.001}
s=Path(simsite)
i=json.loads((s/"model_cache/index.json").read_text(encoding="utf8"))
layer=next(x for x in i["stages"][0]["layers"] if x["kind"]=="excavation")
reference=pv.read(s/layer["file"])
pc,*_=locations(product)
rc,*_=locations(reference)
to_reference=cKDTree(rc).query(pc)[0]
to_generic=cKDTree(pc).query(rc)[0]
report={"case":case,"unmodified_ExtractSurface_faces":raw_surface_faces,
        "extra_operations":4 if case=="A" else 3,"refined_faces":product.n_cells,"refined_area_m2":product.area,
        "sim2web_faces":reference.n_cells,"sim2web_area_m2":reference.area,**extra,
        "unmatched_refined_centers_at_1mm":int((to_reference>.001).sum()),"unmatched_reference_centers_at_1mm":int((to_generic>.001).sum()),
        "test_scope":"Additional filters implemented with generic VTK/PyVista operations on the actual ParaView Extract Surface output. Compares geometric face centers, no values or winding."}
print(json.dumps(report,indent=2))
Path(out).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
