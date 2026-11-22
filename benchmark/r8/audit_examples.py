"""Compare the r8 outputs with r4 and account for Git LFS assets."""
import argparse
import json
import subprocess
from pathlib import Path


EXAMPLES={"A":"flac3d_cavern_iv2", "B":"flac3d_slope_exac23", "C":"3dec_slope", "D":"flac3d_pit_case4",
          "E":"ogs_slope", "F":"3dec_slope_case_f", "STAGES":"flac3d_cavern_stages"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def file_sizes(site):
    return {file.relative_to(site).as_posix():file.stat().st_size for file in site.rglob("*") if file.is_file()}


def figures(site):
    index=load(site/"model_cache/index.json")
    report=load(site/"model_cache/build_report.json")
    validation=load(site/"validation/validation_summary.json")
    result={"schema":index["schema"], "validation_passed":not validation["failures"],"failures":validation["failures"],
            "site_bytes":sum(file_sizes(site).values()), "stages":{}}
    for spec,row in zip(index["stages"],report["stages"],strict=True):
        assert spec["id"]==row["stage"]
        result["stages"][spec["id"]]={"source_cells":spec["source"]["cells"],
             "layers":{l["id"]:{"faces":l["cells"],"bytes":l["bytes"]} for l in spec["layers"]},
             "sections":row["section_count"],"product_bytes":row["output_bytes"],"excavation":row["excavation_boundary"]}
    return result


parser=argparse.ArgumentParser()
parser.add_argument("legacy",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
data={}
for case in ("D","F"):
    old_site=args.legacy/case/"site"
    new_site=Path("examples")/EXAMPLES[case]/"site"
    baseline=figures(old_site)
    current=figures(new_site)
    old_sizes,new_sizes=file_sizes(old_site),file_sizes(new_site)
    assert current["validation_passed"] and not current["failures"]
    data[case]={"r4":baseline,"r8":current,"product_records_match":baseline["stages"]==current["stages"],
                "whole_site_delta_bytes":current["site_bytes"]-baseline["site_bytes"],
                "size_changes":{name:new_sizes.get(name,0)-old_sizes.get(name,0) for name in sorted(old_sizes.keys()|new_sizes.keys())
                                if old_sizes.get(name)!=new_sizes.get(name)}}
data["STAGES"]=figures(Path("examples")/EXAMPLES["STAGES"]/"site")
assert data["STAGES"]["validation_passed"] and not data["STAGES"]["failures"]

lfs=json.loads(subprocess.check_output(["git","lfs","ls-files","--json"],encoding="utf-8"))["files"]
unique={}
for case,name in EXAMPLES.items():
    group=[x for x in lfs if x["name"].startswith(f"examples/{name}/")]
    refs={kind:[x for x in group if x["name"].startswith(f"examples/{name}/{kind}/")]
          for kind in ["input","site","output"]}
    data.setdefault("lfs",{})[case]={kind:{"files":len(files),"bytes":sum(x["size"] for x in files),
           "all_materialized":all(x["checkout"] and x["downloaded"] for x in files)} for kind,files in refs.items()}
    if case!="STAGES":
        unique.update({x["oid"]:x["size"] for files in refs.values() for x in files})
    if case in ("D","F","STAGES"):
        assert refs["input"] and refs["site"] and all(x["checkout"] and x["downloaded"] for x in group),case
    site=(Path("examples")/name/"site") if case in ("D","F","STAGES") else args.legacy/case/"site"
    data["lfs"][case]["built_site_on_disk_bytes"]=sum(f.stat().st_size for f in site.rglob("*") if f.is_file())
data["lfs_unique_A_to_F_bytes"]=sum(unique.values())
data["lfs_logical_A_to_F_bytes"]=sum(data["lfs"][c][kind]["bytes"] for c in "ABCDEF" for kind in ("input","site","output"))
data["site_v01_directories"]=sorted(path.as_posix() for path in Path("examples").rglob("site_v01") if path.is_dir())
rg=subprocess.run(["git","grep","-ni","site_v01","--","tests"],capture_output=True,encoding="utf-8")
assert rg.returncode in (0,1),rg.stderr
data["site_v01_test_references"]=rg.stdout.splitlines()
args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("D/F exact stage product matches",data["D"]["product_records_match"],data["F"]["product_records_match"])
print("LFS A-F logical and unique bytes",data["lfs_logical_A_to_F_bytes"],data["lfs_unique_A_to_F_bytes"])
