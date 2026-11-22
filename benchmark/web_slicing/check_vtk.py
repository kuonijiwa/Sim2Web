import argparse
from pathlib import Path
import json
import numpy as np
from scipy.spatial import cKDTree

def read_browser(path):
    with path.open("rb") as f:
        n, cells = np.fromfile(f,"<u4",count=2)
        p=np.fromfile(f,"<f4",count=int(n)*3).reshape(-1,3)
        v=np.fromfile(f,"<f4",count=int(n))
        c=np.fromfile(f,"<u4",count=int(cells)*4).reshape(-1,4)[:,1:]
    assert len(p)==len(v) and len(c)==cells
    return p,v,c

def area(points, conn):
    a,b,c=np.asarray(points,dtype=np.float64)[conn].transpose(1,0,2)
    return float(np.linalg.norm(np.cross(b-a,c-a),axis=1).sum()/2)

def matches(points, vals, origin, original_vals, tolerance):
    # CAD/3DEC duplicated nodes retain both discontinuous field values. Look for
    # coordinate-neighbours with the same scalar, then check both directions.
    neighbors=cKDTree(origin).query_ball_point(points,tolerance)
    count=0
    max_diff=None
    for v,candidates in zip(vals,neighbors):
        if not candidates:
            count+=1
            continue
        error=float(np.min(np.abs(original_vals[candidates]-v)))
        max_diff=error if max_diff is None else max(max_diff,error)
    distances=cKDTree(origin).query(points)[0]
    return count,max_diff,float(distances.max())

p=argparse.ArgumentParser()
p.add_argument("data",type=Path)
p.add_argument("export",type=Path)
p.add_argument("out",type=Path)
a=p.parse_args()
meta=json.loads((a.data/"case.json").read_text(encoding="utf-8"))
items=[]
for i in meta["correctness_indices"]:
    bp,bv,bt=read_browser(a.export/f"browser_{i}.bin")
    ba=area(bp,bt)
    reference={}
    for key,prefix in (("original","reference"),("transport_precision","reference_browser")):
        with np.load(a.data/f"{prefix}_{i}.npz") as q:
            rp,rv,rt=(q[k] for k in ("points","values","connectivity"))
        pa=area(rp,rt)
        r1,v1,s1=matches(rp,rv,bp,bv,0.001)
        r2,v2,s2=matches(bp,bv,rp,rv,0.001)
        n_d=abs(len(bt)-len(rt))/len(rt)*100
        a_d=abs(ba-pa)/pa*100
        m=max(x for x in (v1,v2) if x is not None)
        passed=n_d<=1 and a_d<=.1 and m<1e-6
        reference[key]=dict(vtk_triangles=len(rt),triangle_error_percent=n_d,vtk_area=pa,area_error_percent=a_d,
            max_displacement_diff_m=m,unmatched_vtk_points=r1,unmatched_browser_points=r2,
            largest_nearest_position_gap_m=max(s1,s2),criteria_passed=passed)
    passed=all(x["criteria_passed"] for x in reference.values()) and not any(reference["transport_precision"][k]
        for k in ("unmatched_vtk_points","unmatched_browser_points"))
    items.append(dict(index=i,x=meta["positions"][i],browser_triangles=len(bt),browser_area=ba,
        coordinate_tolerance_m=.001,references=reference,passed=passed))
summary={"case":meta["case"],"method":"vtkCutter with source and matching Float32 transport precision, triangles, non-merging locator, retained mesh.",
    "gate":"All requested triangle, area and matched-value tolerances on both references. Also require 100% bidirectional matches within 1 mm on the exact transported mesh. Record original-precision unmatched points.",
    "planes":items,"passed":all(i["passed"] for i in items)}
a.out.write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
if not summary["passed"]: raise SystemExit(1)
