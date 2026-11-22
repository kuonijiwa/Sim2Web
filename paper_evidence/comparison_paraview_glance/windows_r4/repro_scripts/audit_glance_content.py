import json,sys,zipfile
from pathlib import Path
for case,archive,report in zip(sys.argv[1::3],sys.argv[2::3],sys.argv[3::3]):
 f=Path(archive)
 with zipfile.ZipFile(f) as z:
    scene=json.loads(z.read("index.json"))["scene"]
    scoped=[]
    for item in scene:
        ref=item.get(item["type"],{}).get("url")
        meta=json.loads(z.read(ref+"/index.json"))
        points=[q["data"]["name"] for q in meta.get("pointData",{}).get("arrays",[])]
        cells=[q["data"]["name"] for q in meta.get("cellData",{}).get("arrays",[])]
        scoped.append({"name":item["name"],"points":points,"cells":cells})
 r={"case":case,"archive_bytes":f.stat().st_size,"actors":len(scoped),"slices":len([x for x in scoped if x["name"].startswith("Slice")]),
    "actors_with_displacement_magnitude":sum("Displacement_Magnitude" in a["points"] for a in scoped),
    "actors_with_all_principal_stresses":sum(all(f"Stress - Sigma {i}" in a["cells"] for i in (1,2,3)) for a in scoped),
    "primary_original_ids":{k:[x for x in scoped[0][k] if x.startswith("vtkOriginal")] for k in ("points","cells")},"actor_arrays":scoped}
 Path(report).write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({k:v for k,v in r.items() if k!="actor_arrays"},ensure_ascii=False))
