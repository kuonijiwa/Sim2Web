"""Generic ParaView baseline for the comparison with Sim2Web (run with pvpython).

    pvpython benchmark/paraview_baseline.py model.vtu --out baseline_dir \
        --sections x=10,20,30 --sections y=0 --sections z=-20 [--null-threshold 1e-8]

What a careful ParaView user does to share the same content as a Sim2Web
package: keep the retained (non-null) zones, extract their surface, compute
principal stresses with "Tensor Principal Invariants", cut the sections, and
export the scene for ParaView Glance.  Every step is the standard filter with
default settings; nothing is corrected.  The script writes

* ``surface.vtp`` and ``sections/*.vtp``: the data ParaView shows;
* ``scene.vtkjs`` (plus an HTML scene when a Glance template is supplied);
* ``baseline_report.json``: timings, sizes, filter list.

Verified against ParaView 5.13.3 on Windows.
"""
import argparse
from pathlib import Path
import json
import os
import time
from contextlib import contextmanager
from paraview import smtrace, servermanager


from paraview.simple import (Calculator, ColorBy, CreateView, ExportView, ExtractSurface, PythonCalculator, SaveData, Show, Slice,
                             TensorPrincipalInvariants, Threshold, XMLUnstructuredGridReader)


@contextmanager
def trace_changes(proxy):
    event=smtrace.PropertiesModified(proxy.SMProxy)
    try:
        yield
    finally:
        event.finalize()

def tracked_export(filename, view, **kwargs):
    helper=servermanager.vtkSMViewExportHelper()
    smproxy=helper.CreateExporter(filename,view.SMProxy)
    proxy=servermanager._getPyProxy(smproxy)
    for k,v in kwargs.items():
        setattr(proxy,k,v)
    event=smtrace.ExportView(view.SMProxy,smproxy,filename)
    event.finalize()
    return ExportView(filename,view=view,**kwargs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vtu")
    ap.add_argument("--out", required=True)
    ap.add_argument("--array", default="Stress")
    ap.add_argument("--displacement", default="Displacement")
    ap.add_argument("--glance-template", type=Path)
    ap.add_argument("--keep-all", action="store_true", help="source has no null zones")
    ap.add_argument("--null-threshold", type=float, default=1e-8)
    ap.add_argument("--sections", action="append", default=[], help="axis=v1,v2,...")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "sections"), exist_ok=True)
    times, filters = {}, []
    started = time.perf_counter()

    t = time.perf_counter()
    reader = XMLUnstructuredGridReader(FileName=[a.vtu])
    reader.UpdatePipeline()
    filters.append("XMLUnstructuredGridReader")
    times["read"] = time.perf_counter() - t

    # retained zones: largest absolute stress component above the null threshold
    t = time.perf_counter()
    retained = reader
    if not a.keep_all:
        calc = PythonCalculator(Input=reader, ArrayAssociation="Cell Data", ArrayName="absmax",
                                Expression=f"max(abs(inputs[0].CellData['{a.array}']), axis=1)")
        retained = Threshold(Input=calc, Scalars=["CELLS", "absmax"])
        with trace_changes(retained):
            retained.LowerThreshold = a.null_threshold
            retained.UpperThreshold = 1e300
            retained.ThresholdMethod = "Between"
        filters += ["PythonCalculator", "Threshold"]
    retained.UpdatePipeline()
    principal = TensorPrincipalInvariants(Input=retained)
    with trace_changes(principal):
        principal.CellTensors = [a.array]
    principal.UpdatePipeline()
    vector = Calculator(Input=principal, AttributeType="Point Data", ResultArrayName="Displacement_Magnitude",
                        Function=f'mag("{a.displacement}")')
    surface = ExtractSurface(Input=vector)
    surface.UpdatePipeline()
    filters += ["TensorPrincipalInvariants", "Calculator", "ExtractSurface"]
    times["surface"] = time.perf_counter() - t
    SaveData(os.path.join(a.out, "surface.vtp"), proxy=surface)
    faces = surface.GetDataInformation().GetNumberOfCells()

    view = CreateView("RenderView")
    display = Show(surface, view)
    ColorBy(display, ('POINTS', 'Displacement_Magnitude'))
    view.ResetCamera()
    t = time.perf_counter()
    n_sections = 0
    for spec in a.sections:
        axis, values = spec.split("=")
        normal = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis]
        for v in values.split(","):
            cut = Slice(Input=vector)
            cut.SliceType = "Plane"
            origin = [0.0, 0.0, 0.0]
            origin["xyz".index(axis)] = float(v)
            with trace_changes(cut):
                cut.SliceType.Origin = origin
                cut.SliceType.Normal = normal
            SaveData(os.path.join(a.out, "sections", f"slice_{axis}_{v}.vtp"), proxy=cut)
            cut_display = Show(cut, view)
            ColorBy(cut_display, ('POINTS', 'Displacement_Magnitude'))
            n_sections += 1
    filters += ["Slice"] * n_sections
    times["sections"] = time.perf_counter() - t

    t = time.perf_counter()
    scene = os.path.join(a.out, "scene.vtkjs")
    if a.glance_template:
        tracked_export(scene, view=view, ParaViewGlanceHTML=str(a.glance_template.resolve()))
    else:
        tracked_export(scene, view=view)
    exported = sorted(n for n in os.listdir(a.out) if n.endswith((".vtkjs", ".html")))
    times["export"] = time.perf_counter() - t

    sizes = {}
    for root, _, files in os.walk(a.out):
        for f in files:
            p = os.path.join(root, f)
            sizes[os.path.relpath(p, a.out)] = os.path.getsize(p)
    report = {"input": os.path.basename(a.vtu), "filters": filters, "sections": n_sections, "seconds": times,
              "exported": exported, "bytes": sizes, "surface_faces": faces,
              "elapsed_wall_seconds": time.perf_counter() - started,
              "note": "TensorPrincipalInvariants reads the tensor in VTK order XX,YY,ZZ,XY,YZ,XZ; "
                      "ComponentName attributes of the file are not used."}
    with open(os.path.join(a.out, "baseline_report.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

