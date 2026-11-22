import ast,json,sys
from collections import Counter
from pathlib import Path
trace,idx,out=map(Path,sys.argv[1:])
raw=trace.read_text(encoding="utf-8-sig")
code=ast.parse(raw)
reader=0
exports=[]
slices={}
for n in code.body:
    if isinstance(n,ast.Assign) and len(n.targets)==1:
        k=n.targets[0]
        v=n.value
        if isinstance(k,ast.Name) and isinstance(v,ast.Call) and isinstance(v.func,ast.Name):
            if v.func.id=="Slice":
                slices[k.id]={"normal":[1,0,0]}
            if v.func.id=="XMLUnstructuredGridReader":
                reader+=1
        if isinstance(k,ast.Attribute) and k.attr in ("Origin","Normal") and isinstance(k.value,ast.Attribute) and k.value.attr=="SliceType" and isinstance(k.value.value,ast.Name):
            slice_name=k.value.value.id
            if slice_name in slices:
                slices[slice_name][k.attr.lower()]=ast.literal_eval(v)
    if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=="ExportView":
        exports.append(ast.literal_eval(n.value.args[0]))
by_loc=Counter()
for data in slices.values():
    if "origin" in data:
        axis=max(range(3),key=lambda i:abs(data["normal"][i]))
        by_loc["xyz"[axis],round(data["origin"][axis],8)]+=1
expected=json.loads(idx.read_text(encoding="utf-8-sig"))["stages"][0]["sections"]
by_index=Counter((axis,round(v["value"],8)) for axis,vals in expected.items() for v in vals)
report={"native_trace":trace.name,"total_lines":len(raw.splitlines()),
        "effective_lines":sum(bool(l.strip()) and not l.lstrip().startswith("#") for l in raw.splitlines()),
        "reader_calls":reader,"slices":len(slices),"with_position":sum(by_loc.values()),"export_calls":exports,
        "exact_section_positions_match":by_loc==by_index,
        "missing_positions":list((by_index-by_loc).elements()),"unexpected_positions":list((by_loc-by_index).elements()),
        "scope":"Static AST check of GUI-generated Python trace against positions in Sim2Web index. The desktop separately executed the actual export."}
out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
if not (by_loc==by_index and exports and reader):
    sys.exit(1)
