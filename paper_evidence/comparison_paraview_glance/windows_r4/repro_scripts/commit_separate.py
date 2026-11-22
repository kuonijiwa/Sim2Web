import os, subprocess, sys
from pathlib import Path
repo=Path(sys.argv[1])
baseline=Path(sys.argv[2])
name=sys.argv[3]
src=sys.argv[4]
message=sys.argv[5]
head="722176f4049ce651dc283ec3665aeb73e9eca884"
env=dict(os.environ,GIT_INDEX_FILE=str(baseline.parent/(name.replace("/","_")+".index")))
def git(*a,data=None):
    r=subprocess.run(["git","-c","user.name=Codex","-c","user.email=codex@openai.com",*a],cwd=repo,env=env,input=data,capture_output=True,check=True)
    return r.stdout.decode().strip()
git("read-tree",head)
blob=git("hash-object","-w","--stdin",data=baseline.read_bytes())
git("update-index","--add","--cacheinfo",f"100644,{blob},{src}")
tree=git("write-tree")
commit=git("commit-tree",tree,"-p",head,"-m",message)
git("update-ref","refs/heads/"+name,commit)
print(commit)
print(git("show","--stat","--oneline",commit))
