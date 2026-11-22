import difflib, json, subprocess, sys, time
from pathlib import Path
import yaml
w,e=map(Path,sys.argv[1:])
s=json.loads((w/"cases_r4.json").read_text(encoding="utf-8"))
stages="ACD"
for k in stages:
    d=e/"cases"/k
    cmd=[str(w/"venv/Scripts/sim2web.exe"),"inspect",s[k]["model"],"--draft-config",str(d/"auto_draft.yaml")]
    t=time.perf_counter()
    with (d/"inspect.json").open("wb") as f,(d/"inspect.stderr.log").open("wb") as err:
        result=subprocess.run(cmd,stdout=f,stderr=err)
    (d/"inspect_command.json").write_text(json.dumps({"command":cmd,"exit_code":result.returncode,"seconds":time.perf_counter()-t},indent=2),encoding="utf-8")
    if result.returncode: continue
    draft=d/"auto_draft.yaml"
    actual=w/"model_runs"/k/"case.yaml"
    left,right=[yaml.safe_dump(yaml.safe_load(p.read_text(encoding="utf-8")),allow_unicode=True,sort_keys=True).splitlines(True) for p in (draft,actual)]
    ops=[(t,i2-i1,j2-j1) for t,i1,i2,j1,j2 in difflib.SequenceMatcher(None,left,right,autojunk=False).get_opcodes() if t!="equal"]
    metrics={"changed_lines":sum(max(a,b) for _,a,b in ops),"removed_lines":sum(a for _,a,b in ops),"added_lines":sum(b for _,a,b in ops),
        "method":"Canonical sorted safe_dump, SequenceMatcher. Each replace counts max(old lines,new lines); pure inserts/deletes count their lines."}
    (d/"draft_delta.json").write_text(json.dumps(metrics,indent=2),encoding="utf-8")
    (d/"draft_delta.diff").write_text("".join(difflib.unified_diff(left,right,fromfile="inspect draft (normalized)",tofile="run case.yaml (normalized)")),encoding="utf-8")
    print(k,metrics,flush=True)
