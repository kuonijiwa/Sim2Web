import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path
from paraview import smtrace
from paraview.simple import Delete, GetActiveViewOrCreate, GetSources

root=Path("C:/swv_r4_20261121")
out=Path("G:/成果/papers/02/codex_run_2026-11-21_r4/cases")
module=importlib.util.spec_from_file_location("baseline_r4",root/"paraview_baseline.py")
baseline=importlib.util.module_from_spec(module)
module.loader.exec_module(baseline)
view=GetActiveViewOrCreate("RenderView")
baseline.CreateView=lambda _:view
baseline.SaveData=lambda *args,**kwargs:None
for case in ("C","D","A"):
    evidence=out/case
    command=evidence/"paraview_command.json"
    dest=root/"pv_gui_optimized"/case
    dest.mkdir(parents=True,exist_ok=True)
    argv=json.loads(command.read_text(encoding="utf8"))[1:]
    argv[argv.index("--out")+1]=str(dest)
    saved=sys.argv
    sys.argv=argv
    message={"case":case,"mode":"ParaView desktop --script, native smtrace; no separate VTP writes; same filters, fields, positions and actual Export Scene API"}
    started=time.perf_counter()
    smtrace.start_trace()
    try:
        old=baseline.Show
        def show(*args,**kw):
            v=old(*args,**kw)
            (dest/"trace_running.py").write_text(smtrace.get_current_trace_output(),encoding="utf-8")
            return v
        baseline.Show=show
        try:
            baseline.main()
        finally:
            baseline.Show=old
        message.update(code=0,seconds=time.perf_counter()-started)
    except Exception:
        message.update(code=1,seconds=time.perf_counter()-started,traceback=traceback.format_exc())
    finally:
        sys.argv=saved
        trace=smtrace.stop_trace()
        (evidence/"paraview_gui_native_trace.py").write_text(trace,encoding="utf-8")
        (evidence/"paraview_gui_result.json").write_text(json.dumps(message,indent=2)+"\n",encoding="utf-8")
        for name,obj in reversed(list(GetSources().items())):
            Delete(obj)
