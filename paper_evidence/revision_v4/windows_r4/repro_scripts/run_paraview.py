import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("work",type=Path)
p.add_argument("run",type=Path)
p.add_argument("repo",type=Path)
p.add_argument("cases",nargs="+")
a=p.parse_args()
w,e,repo=a.work,a.run,a.repo
pv=(w/"pvpython_path.txt").read_text(encoding="utf-8-sig").strip()
template=next((w/"paraview").rglob("ParaViewGlance.html"))
for case in a.cases:
    site=w/"model_runs"/case/"site"
    dest=w/"pv_baselines"/case
    evidence=e/"cases"/case
    cfg=w/"model_runs"/case/"case.yaml"
    for _ in range(180):
        if (e/"logs"/f"034_build_{case}.json").is_file():
            break
        time.sleep(5)
    idx=json.loads((site/"model_cache/index.json").read_text(encoding="utf-8"))
    specs=[axis+"="+",".join(str(s["value"]) for s in ss) for axis,ss in idx["stages"][0]["sections"].items()]
    args=[pv,str(w/"paraview_baseline.py"),str(w/"pv_sources"/f"{case}.vtu"),"--out",str(dest),"--glance-template",str(template)]
    args += {"A":[],"C":["--null-threshold","1e-6"],"D":["--keep-all"]}[case]
    for spec in specs:
        args += ["--sections",spec]
    (evidence/"paraview_command.json").write_text(json.dumps(args,indent=2),encoding="utf-8")
    log=evidence/"paraview_baseline.log"
    started=time.perf_counter()
    with log.open("wb") as f:
        r=subprocess.run(args,cwd=repo,stdout=f,stderr=subprocess.STDOUT)
    elapsed=time.perf_counter()-started
    print(case,r.returncode,elapsed,flush=True)
    (evidence/"paraview_exit.json").write_text(json.dumps({"exit_code":r.returncode,"seconds":elapsed,"command":args},indent=2),encoding="utf-8")
    report=dest/"baseline_report.json"
    if report.is_file():
        shutil.copyfile(report,evidence/"paraview_baseline_report.json")
