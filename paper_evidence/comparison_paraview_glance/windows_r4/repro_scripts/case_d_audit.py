import json, sys
from pathlib import Path
import numpy as np
import pyvista as pv
from sim2web.geometry import polygons

site, out, r3 = map(Path, sys.argv[1:])
stage = json.loads((site/"model_cache/index.json").read_text(encoding="utf-8"))["stages"][0]
report = json.loads((site/"model_cache/build_report.json").read_text(encoding="utf-8"))["stages"][0]
old = json.loads(r3.read_text(encoding="utf-8"))["stages"][0]
layer = next(v for v in stage["layers"] if v["kind"] == "excavation")
wall = pv.read(site/layer["file"])
offsets, ids = polygons(wall)
lengths = np.diff(offsets)
xyz = np.asarray(wall.points,dtype=np.float64)[ids]
row = np.repeat(np.arange(wall.n_cells),lengths)
center = np.zeros((wall.n_cells,3))
np.add.at(center,row,xyz)
center /= lengths[:,None]
z_low = np.minimum.reduceat(xyz[:,2],offsets[:-1])
z_high = np.maximum.reduceat(xyz[:,2],offsets[:-1])
area = np.asarray(wall.compute_cell_sizes(length=False,volume=False).cell_data["Area"])
normals = np.asarray(wall.compute_normals(point_normals=False,consistent_normals=False).cell_data["Normals"])
radius = np.linalg.norm(center[:,:2],axis=1)
levels = {}
for boundary in [-57.5,-57.5013]:
    selection = center[:,2] < boundary
    floor = selection & (np.max(np.abs(np.column_stack((z_low,z_high))+57.5003),axis=1)<=0.001) & (np.abs(normals[:,2])>=.95)
    def describe(s):
        return {"faces":int(s.sum()),"area_m2":float(area[s].sum()),
                "centroid_z_m":[float(center[s,2].min()),float(center[s,2].max())] if s.any() else None,
                "centroid_radius_m":[float(radius[s].min()),float(radius[s].max())] if s.any() else None}
    levels[str(boundary)]={"centroid_below":describe(selection),"all_vertices_below":describe(z_high<boundary),
                           "any_vertex_below":describe(z_low<boundary),"nominal_floor_faces":describe(floor),
                           "other_centroids_below":describe(selection & ~floor)}
def exterior(s):
    return [{key:v[key] for key in ("id","file","cells","bytes") if key in v}
            for v in s["layers"] if v["kind"]=="exterior"]
result={"published_excavation_faces":wall.n_cells,"published_excavation_area_m2":float(area.sum()),
        "bounds_m":list(wall.bounds),"depth_audit":levels,"excavation_boundary":report.get("excavation_boundary"),
        "exterior_r3":exterior(old),"exterior_r4":exterior(stage),
        "mesh_regions":stage.get("mesh_regions"),"internal_faces":stage.get("internal_faces")}
out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,indent=2))
