"""Choose a common orthographic camera and colour range from the built stages."""
import argparse
import json
from pathlib import Path

import numpy as np
import pyvista as pv


parser = argparse.ArgumentParser()
parser.add_argument("site", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
index = json.loads((args.site/"model_cache/index.json").read_text(encoding="utf-8"))
selected = [index["stages"][i] for i in (0,2,4)]
field = "Stress_Min_Principal"
surfaces = [pv.read(args.site/next(l["file"] for l in stage["layers"] if l["id"]=="excavation"))
            for stage in index["stages"]]
geometry = np.concatenate([surface.points for surface in surfaces])
centre = (geometry.max(0)+geometry.min(0))/2
out = np.array([-0.60,-1.00,0.58])
out /= np.linalg.norm(out)
right = np.cross(-out,[0,0,1])
right /= np.linalg.norm(right)
up = np.cross(out,right)
projected = geometry@np.column_stack((right,up))
adjustment = (projected.max(0)+projected.min(0))/2-centre@np.column_stack((right,up))
centre = centre+adjustment[0]*right+adjustment[1]*up
eye = centre+out*np.linalg.norm(np.ptp(geometry,axis=0))*3
width,height = 760,480
span = np.ptp(projected,axis=0)
scale = max(span[1]/2,span[0]*height/(2*width))*1.07
values = np.concatenate([surface.cell_data[field] for surface in surfaces])
limits = np.percentile(values[np.isfinite(values)],[5,95]).tolist()
setup = {"stages":[x["id"] for x in selected],"field":field,"limits":limits,
         "limits_method":"P5–P95 of excavation face values pooled over all five construction stages",
         "camera":[*eye,*centre,*up,scale],"viewport":{"width":width,"height":height}}
args.output.write_text(json.dumps(setup,indent=2)+"\n",encoding="utf-8")
print(setup["stages"],setup["field"],setup["limits"])
