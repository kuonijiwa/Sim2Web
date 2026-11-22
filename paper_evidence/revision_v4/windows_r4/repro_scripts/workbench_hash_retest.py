import hashlib,json,os,sys,time,subprocess,shutil
from pathlib import Path
from sim2web.workbench import Project
source,dest,out=map(Path,sys.argv[1:])
dest.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source,dest/"case.yaml")
p=Project(dest)
j=p.start("build",{})
for _ in range(600):
    if j.state!="running":break
    time.sleep(.2)
assert j.state=="done",j.error
f=dest/"site/model_cache/index.json"
sha=lambda:hashlib.sha256(f.read_bytes()).hexdigest()
w=sha()
cmd=[sys.executable,"-m","sim2web","build",str(dest/"case.yaml")]
r=subprocess.run(cmd)
assert r.returncode==0
cli=sha()
report={"workbench_sha256":w,"cli_sha256":cli,"match":w==cli,"cli_command":cmd,"cli_exit_code":r.returncode}
out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
assert w==cli
