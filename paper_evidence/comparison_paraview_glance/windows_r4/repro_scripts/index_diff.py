import json, sys
from pathlib import Path
a,b,out=map(Path,sys.argv[1:])
def changes(x,y,key="$"):
    if type(x)!=type(y):return [(key,x,y)]
    if isinstance(x,dict):
        return [(key+"."+k,x.get(k),y.get(k)) for k in x.keys()^y.keys()] + [v for k in x.keys()&y.keys() for v in changes(x[k],y[k],key+"."+k)]
    if isinstance(x,list):
        return [(key+".length",len(x),len(y))] if len(x)!=len(y) else [v for i,(xv,yv) in enumerate(zip(x,y)) for v in changes(xv,yv,f"{key}[{i}]")]
    return [(key,x,y)] if x!=y else []
D=changes(json.loads(a.read_text(encoding="utf8")),json.loads(b.read_text(encoding="utf8")))
d={"difference_count":len(D),"differences":[{"key":k,"workbench":x,"cli":y} for k,x,y in sorted(D)]}
out.write_text(json.dumps(d,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(len(D)); print([n for n,_,_ in sorted(D)][:28])
