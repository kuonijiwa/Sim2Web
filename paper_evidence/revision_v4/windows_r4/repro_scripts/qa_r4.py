import json,sys
from pathlib import Path
from PIL import Image
p=Path(sys.argv[1])
def r(path):
    return json.loads((p/path).read_text(encoding="utf-8-sig"))
checks={}
for k in "ABCDEF":
    build=r(f"logs/034_build_{k}.json")
    validation=r(f"logs/035_validate_{k}.json")
    info=r(f"cases/{k}/validation_summary.json")
    assert build["exit_code"]==validation["exit_code"]==0 and info["failures"]==[],k
    checks[f"case_{k}_build_validate"]=[build["duration_seconds"],validation["duration_seconds"]]
for k in "ACD":
    stage=r(f"cases/{k}/index.json")["stages"][0]
    raw=r(f"cases/{k}/paraview_gui_trace_audit.json")
    assert raw["exact_section_positions_match"] and raw["slices"]==sum(map(len,stage["sections"].values()))
    sub="paraview_corrected/" if k in "AC" else ""
    get=lambda n:r(f"cases/{k}/{sub}{n}.json")
    scene=get("scene_arrays")
    assert scene["actors_with_all_principal_stresses"]==scene["actors"]==raw["slices"]+1
    assert scene["actors_with_displacement_magnitude"]==scene["actors"]
    a=get("glance_split_geometry_browser")
    assert len(a["runs"])==3 and all(t.get("count",0)>=10000 and t.get("firstImageMs",0)>0 for t in a["runs"])
    b=r(f"cases/{k}/sim2web_browser.json")
    assert len(b["runs"])==3 and all(t["verificationPassed"] for t in b["runs"])
    checks[f"case_{k}_comparison"]={"trace_lines":raw["total_lines"],"glance_frames_ms":[x["firstImageMs"] for x in a["runs"]],
                                     "sim2web_frames_ms":[x["navigationToFirstImageMs"] for x in b["runs"]]}
for k in "DF":
    assert r(f"workbench/{k}/workbench_timing.json")["validation_passed"]
    for example in (f"cases/{k}/viewer_1600x900.png",)+(('cases/F/viewer_p5_p95_1600x900.png',) if k=="F" else ('cases/D/excavation_from_below_1600x900.png',)):
        with Image.open(p/example) as pic:
            assert pic.size==(1600,900)
            pic.verify()
    assert r(f"logs/027_principal_{k}.json")["exit_code"]==0
m=r("cases/H/r3_r4_difference.json")
assert m["stress_max_abs"]==m["displacement_max_abs"]==0
assert r("logs/107_final_fix_bundle.json")["exit_code"]==0
assert r("logs/016_realdata.json")["exit_code"]==0
checks["D_and_F_screenshots"]="1600x900 checked"
checks["raw_models_and_sites_in_delivery"]=sum(f.suffix.lower() in {".vtu",".vtp",".odb",".e",".vtkjs",".html"} for f in p.rglob("*") if f.is_file())
assert checks["raw_models_and_sites_in_delivery"]==0
(p/"delivery_checks.json").write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
print(json.dumps(checks,indent=2))
