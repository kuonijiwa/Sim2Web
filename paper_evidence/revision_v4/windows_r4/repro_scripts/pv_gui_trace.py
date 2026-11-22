import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path

from paraview import smtrace
from paraview.simple import Delete, GetActiveSource, GetActiveView, GetSources, Hide, Render

root=Path("C:/swv_r4_20261121")
output=Path("G:/成果/papers/02/codex_run_2026-11-21_r4/cases")
modspec=importlib.util.spec_from_file_location("baseline_r4",root/"paraview_baseline.py")
baseline=importlib.util.module_from_spec(modspec)
modspec.loader.exec_module(baseline)
normal_reader=baseline.XMLUnstructuredGridReader
view=GetActiveView()
baseline.CreateView=lambda _:view
for case in ("A","C","D"):
    d=output/case
    dest=root/"pv_gui"/case
    dest.mkdir(parents=True,exist_ok=True)
    command=d/"paraview_command.json"
    ready=d/"paraview_exit.json"
    try:
        for _ in range(360):
            if command.is_file() and ready.is_file():
                break
            time.sleep(5)
        else:
            raise RuntimeError("No CLI run with verified section positions")
        argv=json.loads(command.read_text(encoding="utf-8"))[1:]
        argv[argv.index("--out")+1]=str(dest)
        if case=="A":
            reader=GetActiveSource()
            assert reader and str(reader.FileName[0]).endswith("A.vtu")
            Hide(reader,view)
            baseline.XMLUnstructuredGridReader=lambda **_:reader
        else:
            baseline.XMLUnstructuredGridReader=normal_reader
            smtrace.start_trace()
        before=time.perf_counter()
        saved=sys.argv
        sys.argv=argv
        try:
            baseline.main()
        finally:
            sys.argv=saved
        elapsed=time.perf_counter()-before
        (dest/"gui_native_trace.py").write_text(smtrace.stop_trace(),encoding="utf-8")
        (dest/"gui_result.json").write_text(json.dumps({"seconds":elapsed,"code":0,"case":case,
              "command":argv,"method":"ParaView desktop Python panel; A read and Apply performed in GUI before timed macro. Trace captured by native smtrace."},indent=2),encoding="utf-8")
        for _,source in reversed(list(GetSources().items())):
            Delete(source)
        Render(view)
    except Exception:
        (dest/"gui_result.json").write_text(json.dumps({"code":1,"traceback":traceback.format_exc()},indent=2),encoding="utf-8")
        raise
