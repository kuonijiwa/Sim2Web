import json,sys
from pathlib import Path
import numpy as np
import pyvista as pv
import vtk
from sim2web.vtkxml import component_names
from sim2web.fields import principal_values
p,out=map(Path,sys.argv[1:3])
order=["XX","YY","ZZ","XY","YZ","XZ"]
mesh=pv.read(p)
labels=[v.upper() for v in component_names(p)["Stress"]]
original=np.asarray(mesh.cell_data["Stress"],dtype=np.float64)
ref=principal_values(original,labels)
reordered=original[:,[labels.index(k) for k in order]]
mesh.cell_data["Stress_VTK_order"]=reordered
flt=vtk.vtkTensorPrincipalInvariants()
flt.SetInputData(mesh)
flt.Update()
arrays=pv.wrap(flt.GetOutput()).cell_data
pred=np.column_stack([arrays[f"Stress_VTK_order - Sigma {k}"] for k in (3,2,1)])
err=np.abs(ref-pred)
r={"original_labels":labels,"enabled_tensor_order":order,"additional_operations":1,
   "max_abs_mpa_min_mid_max":err.max(axis=0).tolist(),
   "false_tensile_due_to_roundoff":int(((pred[:,-1]>0)&(ref[:,-1]<=0)).sum()),
   "false_tensile_using_1e_9_mpa_sign_epsilon":int(((pred[:,-1]>1e-9)&(ref[:,-1]<=1e-9)).sum()),
   "note":"An explicit tensor reorder can be added as one Programmable Filter before the native principal stress filter. Does not change reported default timing/size."}
out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
print(json.dumps(r,indent=2))
