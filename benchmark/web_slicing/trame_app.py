"""A trame-vtk comparison app for the public Sim2Web A/C models."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

START = time.perf_counter()
if extra := os.environ.get("SIM2WEB_R6_TRAME_LIB"):
    # Preserve the workstation's existing Python scientific-stack versions.
    sys.path.append(extra)

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from trame.app import get_server
from trame.ui.html import DivLayout
from trame.widgets import html
from trame.widgets import vtk as widgets
from prepare import cutter_for, read_case, retained_grid

def colors(lut, meta):
    jet = [(0,0,0,.5),(.11,0,0,1),(.34,0,1,1),(.65,1,1,0),(.89,1,0,0),(1,.5,0,0)]
    assert meta["colormap"] == "jet"
    n = meta["bands"]
    lo, hi = meta["range"]
    step = (hi - lo) / n
    epsilon = (hi - lo) * 1e-9
    for i in range(n):
        t = i / (n-1)
        j = next(k for k in range(1,len(jet)) if t <= jet[k][0])
        a, b = jet[j-1], jet[j]
        blend = (t-a[0])/(b[0]-a[0])
        rgb = [a[k] + blend*(b[k]-a[k]) for k in (1,2,3)]
        lut.AddRGBPoint(lo+i*step,*rgb)
        lut.AddRGBPoint(lo+(i+1)*step-epsilon,*rgb)

p = argparse.ArgumentParser()
p.add_argument("mode", choices=("local","remote"))
p.add_argument("case_meta",type=Path)
p.add_argument("port",type=int)
p.add_argument("run_log",type=Path)
a = p.parse_args()
meta = json.loads(a.case_meta.read_text(encoding="utf-8"))
before_read = time.perf_counter()
_, mesh, vectors, mask = read_case(meta["case"])
source_read = time.perf_counter()-before_read
solid = retained_grid(mesh,vectors,mask)
del mesh,vectors,mask
model_ready = time.perf_counter()
plane, cutter = cutter_for(solid)
renderer = vtk.vtkRenderer()
renderer.SetBackground(1,1,1)
window = vtk.vtkRenderWindow()
window.SetOffScreenRendering(True)
window.SetSize(*meta["viewport"])
window.AddRenderer(renderer)
interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(window)
style = vtk.vtkInteractorStyleTrackballCamera()
interactor.SetInteractorStyle(style)
c = meta["camera"]
camera = renderer.GetActiveCamera()
camera.SetPosition(*c[:3])
camera.SetFocalPoint(*c[3:6])
camera.SetViewUp(*c[6:9])
camera.ParallelProjectionOn()
camera.SetParallelScale(c[9])
lookup = vtk.vtkColorTransferFunction()
colors(lookup, meta)
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(cutter.GetOutputPort())
mapper.SetLookupTable(lookup)
mapper.UseLookupTableScalarRangeOn()
mapper.SetScalarModeToUsePointData()
mapper.SetColorModeToMapScalars()
mapper.InterpolateScalarsBeforeMappingOn()
actor = vtk.vtkActor()
actor.SetMapper(mapper)
renderer.AddActor(actor)
if a.mode == "remote":
    marker_points = vtk.vtkPoints()
    for point in ((7, 7, 0), (27, 7, 0), (27, 27, 0), (7, 27, 0)):
        marker_points.InsertNextPoint(*point)
    marker_cells = vtk.vtkCellArray()
    marker_cells.InsertNextCell(4)
    for point_id in range(4):
        marker_cells.InsertCellPoint(point_id)
    marker_data = vtk.vtkPolyData()
    marker_data.SetPoints(marker_points)
    marker_data.SetPolys(marker_cells)
    marker_mapper = vtk.vtkPolyDataMapper2D()
    marker_mapper.SetInputData(marker_data)
    frame_marker = vtk.vtkActor2D()
    frame_marker.SetMapper(marker_mapper)
    renderer.AddViewProp(frame_marker)
server = get_server(client_type="vue3")
state = server.state
state.section_index = meta["first_index"]
state.cut_revision = 0
positions_verified = set()

def event(data):
    with a.run_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data)+"\n")
    print(json.dumps(data),flush=True)

def cut(index):
    t = time.perf_counter()
    plane.SetOrigin(meta["positions"][index],0,0)
    cutter.Update()
    renderer.ResetCameraClippingRange()
    if a.mode == "remote":
        frame_marker.GetProperty().SetColor((32 + 21 * index) / 255, 40 / 255, 100 / 255)
    return time.perf_counter()-t

first = cut(meta["first_index"])
if a.mode=="remote":window.Render()
event({"phase":"load", "pid":os.getpid(), "case":meta["case"], "mode":a.mode, "source_read_s":source_read,
       "model_and_derive_s":model_ready-before_read,"first_cut_s":first,"app_setup_s":time.perf_counter()-START,
       "triangles":cutter.GetOutput().GetNumberOfPolys()})

class OrthographicLocalView(widgets.VtkLocalView):
    def update(self, **kwargs):
        if self.server.protocol:
            from trame_vtk.modules.vtk.serializers.registry import register_instance_serializer
            from trame_vtk.modules.vtk.serializers.render_windows import camera_serializer

            def serialize_camera(parent, instance, obj_id, context, depth):
                state = camera_serializer(parent, instance, obj_id, context, depth)
                state["properties"].update(
                    parallelProjection=bool(instance.GetParallelProjection()),
                    parallelScale=instance.GetParallelScale(),
                    viewAngle=instance.GetViewAngle(),
                )
                return state

            register_instance_serializer(camera.GetClassName(), serialize_camera)
        return super().update(**kwargs)

with DivLayout(server,style="position:fixed;inset:0;overflow:hidden"):
    view_class = OrthographicLocalView if a.mode=="local" else widgets.VtkRemoteView
    params = {"interactive_ratio":1,"still_ratio":1,"interactive_quality":100,"still_quality":100} if a.mode=="remote" else {}
    view = view_class(window,ref="section_view",style="position:absolute;inset:0",**params)
    with html.Label(style="position:absolute;left:14px;top:14px;background:#fff;border:1px solid #aaa;padding:10px;font:14px Arial;z-index:1"):
        html.Span("X section ")
        html.Input(id="section",type="range",min=0,max=9,step=1,v_model_number=("section_index",meta["first_index"]),aria_label="X section")
        html.Span(" {{ section_index + 1 }} / 10")
    html.Div("{{ cut_revision }}",id="revision",style="display:none")

last = meta["first_index"]
@state.change("section_index")
def changed(section_index, **_):
    global last
    index = int(section_index)
    if index == last:
        return
    start, cpu = time.perf_counter(), time.process_time()
    cut_time=cut(index)
    if a.mode=="remote":
        window.Render()
    view.update()
    last = index
    state.cut_revision += 1
    output = cutter.GetOutput()
    verify = {}
    if index in meta["correctness_indices"] and index not in positions_verified:
        positions_verified.add(index)
        with np.load(a.case_meta.parent / f"reference_{index}.npz") as ref:
            same = {
                "points": bool(np.array_equal(ref["points"],vtk_to_numpy(output.GetPoints().GetData()))),
                "values": bool(np.array_equal(ref["values"],vtk_to_numpy(output.GetPointData().GetArray("TotalDisplacement")))),
                "connectivity": bool(np.array_equal(ref["connectivity"],vtk_to_numpy(output.GetPolys().GetConnectivityArray()).reshape(-1,3))),
            }
        verify = {"vtk_reference_agreement":same}
    event({"phase":"switch","index":index,"x":meta["positions"][index],"cut_s":cut_time,
           "server_s":time.perf_counter()-start,"sync_cpu_s":time.process_time()-cpu,
           "triangles":output.GetNumberOfPolys(),**verify})
server.start(port=a.port,host="127.0.0.1",open_browser=False,timeout=0)
