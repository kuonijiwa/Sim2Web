import ast
import json
import statistics
import sys
from pathlib import Path

root, work, repo = map(Path, sys.argv[1:])

def read(path, default=None):
    try:
        return json.loads((root / path).read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def write(path, text):
    (root / path).write_text(text.rstrip()+"\n",encoding="utf-8")

def record(key):
    return read(f"logs/{key}.json",{})

def casefile(k, name):
    return read(f"cases/{k}/{name}",{})

def wbfile(k, name):
    return read(f"workbench/{k}/{name}",{})

def fmt(x, n=3):
    return f"{x:,.{n}f}" if isinstance(x,(float,int)) else "未测"

def validation(k):
    v=casefile(k,"validation_summary.json")
    return v.get("stages",{}),v.get("failures")

def model_metrics(k):
    r=casefile(k,"build_report.json")
    i=casefile(k,"index.json")
    s=next(iter(r.get("stages",[])),{})
    stage=next(iter(i.get("stages",[])),{})
    main=next((x for x in stage.get("layers",[]) if x.get("role")=="primary"),{})
    ext=next((x for x in stage.get("layers",[]) if x.get("kind")=="exterior"),{})
    val,fail=validation(k)
    return dict(stage=stage, primary=main, exterior=ext, sections=s.get("section_count"),
                vtp_bytes=s.get("output_bytes"), all_bytes=casefile(k,"site_size.json").get("full_site_without_validation_bytes"),
                seconds=record(f"034_build_{k}").get("duration_seconds"),
                kernel_seconds=r.get("seconds_total"), validate_seconds=record(f"035_validate_{k}").get("duration_seconds"),
                validate_exit=record(f"035_validate_{k}").get("exit_code"),
                stress_unit_check=s.get("stress_unit_check"), validation=val, failures=fail)

def traces(k):
    p=root/f"cases/{k}/paraview_gui_native_trace.py"
    if not p.is_file():
        return None
    lines=p.read_text(encoding="utf-8-sig").splitlines()
    result={"lines_total":len(lines),"nonblank_noncomment":sum(bool(s.strip()) and not s.lstrip().startswith("#") for s in lines),
            "file":f"cases/{k}/{p.name}"}
    try:
        tree=ast.parse("\n".join(lines))
        calls=[n.func.id if isinstance(n.func,ast.Name) else n.func.attr for n in ast.walk(tree)
               if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))]
        result["slice_calls"]=calls.count("Slice")
        result["export_calls"]=calls.count("ExportView")
        result["reader_calls"]=calls.count("XMLUnstructuredGridReader")
        result["trace_origin_assignments"]=sum(".SliceType.Origin =" in s for s in lines)
        result["trace_complete"]=bool(result["slice_calls"] and result["export_calls"] and result["reader_calls"] and result["trace_origin_assignments"])
    except SyntaxError:
        result["trace_complete"]=False
    return result

def median(v):
    return statistics.median(v) if v else None

def browsers(k):
    sub="paraview_corrected/" if k in "AC" else ""
    pvcase=casefile(k,sub+"glance_split_geometry_browser.json")
    if not any("firstImageMs" in x for x in pvcase.get("runs",[])) and k=="D":
        fallback=casefile(k,sub+"glance_split_model_event.json")
        if fallback.get("runs"):
            pvcase=fallback
    clock_source=sub+("glance_split_geometry_browser.json" if casefile(k,sub+"glance_split_geometry_browser.json") else "glance_split_model_event.json")
    interaction=casefile(k,sub+"glance_geometry_interaction.json")
    interaction_runs=interaction.get("runs",[])
    scase=casefile(k,"sim2web_browser.json")
    vruns=pvcase.get("runs",[])
    sruns=scase.get("runs",[])
    ext=casefile(k,"field_switch.json")
    planned=(root/f"cases/{k}/paraview_corrected/scene_kitware_size.json") if k in "AC" else (root/f"cases/{k}/scene_kitware_size.json")
    measured_bytes=read(planned.relative_to(root),{}).get("bytes") if planned.is_file() else None
    return {
        "ParaView_Glance":{"first_image_ms":[x["firstImageMs"] for x in vruns if "firstImageMs" in x],
            "median_first_image_ms":median([x["firstImageMs"] for x in vruns if "firstImageMs" in x]),
            "rendered_runs":len([x for x in vruns if "firstImageMs" in x]),"planned_runs":3,
            "export_bytes":measured_bytes,"vtkjs_export_bytes":pvcase.get("exportBytes"),"glance_viewer_bytes":pvcase.get("viewerBytes"),"clock_source":f"cases/{k}/"+clock_source,"runs":vruns,
            "field_switch_ms":next((x.get("fieldSwitchMs") for x in interaction_runs if x.get("fieldSwitchVerified")),None),
            "section_switch_ms":next((x.get("sectionVisibilityToggleTwoActorsMs") for x in interaction_runs if x.get("sectionSwitchVerified")),None),
            "interaction_qualification":"Glance actors have individual visibility switches. The recorded two-actor action is an optional proxy, no section slider.",
            "interaction_trials":interaction_runs},
        "Sim2Web":{"first_image_ms":[x["navigationToFirstImageMs"] for x in sruns],
            "median_first_image_ms":median([x["navigationToFirstImageMs"] for x in sruns]),
            "median_section_switch_ms":median([x["sectionSwitchMedianMs"] for x in sruns]),
            "median_startup_bytes":median([x["startupBytes"] for x in sruns]),
            "field_switch_ms":ext.get("median_ms"),"all_viewer_checks_passed":all(x["verificationPassed"] for x in sruns) if sruns else None,
            "browser":sruns[0].get("browser") if sruns else None,"renderer":sruns[0].get("renderer") if sruns else None}
    }

manual={
    "A":(4,"对同一 absmax 再取互补空区分支；提取空区面；按接触容差筛出实体一侧的相邻面；将筛选结果单独着色并导出。"),
    "C":(0,"本协议仅要求边坡外表面，不设坑腔层。若需要与 Sim2Web 外表面等效，还要单独去除块体间内部面。"),
    "D":(3,"剔除模型六个盒面；对剩余候选面两侧采样并排除实体–实体界面；将剩余坑面单独着色并导出。")
}
sz=lambda b: f"{int(b):,} B（{b/1e6:.3f} MB）" if b is not None else "未测"
pr_root=repo/"paper_evidence/revision_v4"
m={}
for k in "ABCD EF".replace(" ",""):
    m[k]=model_metrics(k)
comp={}
nums=[]
def row(position,value,source,note=""):
    nums.append([position,str(value),source,note])

for k in "ACD":
    base=casefile(k,"paraview_corrected/paraview_baseline_report.json") or casefile(k,"paraview_baseline_report.json")
    pv_exit=casefile(k,"paraview_corrected/paraview_exit.json") or casefile(k,"paraview_exit.json")
    qt=casefile(k,"paraview_gui_result.json")
    pv_trace=traces(k)
    d=casefile(k,"draft_delta.json")
    clicks=wbfile(k,"click_count.json").get("trusted_scripted_clicks")
    bv=browsers(k)
    bg,bs=bv["ParaView_Glance"],bv["Sim2Web"]
    sim=m[k]
    old=casefile(k,"paraview_principal.json")
    if not old:
        try:
            old=json.loads((pr_root/f"paraview_principal_case{k}.json").read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            old={}
    size=base.get("bytes",{})
    gv=bg.get("export_bytes")
    primary=sim["primary"]
    ext=sim["exterior"]
    trace_audit=casefile(k,"paraview_gui_trace_audit.json")
    use_gui=bool(pv_trace and pv_trace.get("trace_complete") and trace_audit.get("exact_section_positions_match"))
    comp[k]={
        "M1":{"ParaView_GUI_native_trace":pv_trace,"ParaView_GUI_trace_positions_audit":trace_audit,"ParaView_mode":"Desktop macro generated native ParaView trace with actual filters, proxy property-change hooks, and export. Original A also manually opened and started from Tools; it is retained separately.",
            "Sim2Web_changed_config_lines":d.get("changed_lines"),"Sim2Web_workbench_clicks_from_seeded_config":clicks},
        "M2":{"ParaView_pvpython_package_seconds":base.get("elapsed_wall_seconds"),"ParaView_pvpython_process_seconds":pv_exit.get("seconds"),
            "Glance_official_reembed_seconds":record(f"112_browser_final_embed_{k}").get("duration_seconds"),
            "ParaView_GUI_macro_seconds":qt.get("seconds"),"ParaView_manually_timed_GUI_seconds":None,
            "Sim2Web_build_seconds":sim["seconds"],"Sim2Web_validate_seconds":sim["validate_seconds"]},
        "M3":{"ParaView_surface_bytes":size.get("surface.vtp"),"ParaView_vtkjs_bytes":size.get("scene.vtkjs"),"ParaView_bundled_html_bytes":size.get("scene.html"),
            "ParaView_official_template_html_bytes":gv,"Sim2Web_primary_bytes":primary.get("bytes"),"Sim2Web_mesh_product_bytes":sim["vtp_bytes"],"Sim2Web_static_site_bytes":sim["all_bytes"]},
        "M4":bv,
        "M5":{"ParaView":old,"ParaView_reordered_with_one_filter":casefile(k,"paraview_principal_reordered.json"),"Sim2Web_exact_mismatches":sum(x.get("exact_mismatches",0) for x in sim["validation"].values()) if sim["validation"] else None},
        "M6":{"ParaView":None,"Sim2Web":sim["stress_unit_check"]},
        "M7":{"ParaView_default_has_separate_excavation":False,"additional_user_steps_for_equivalence":manual[k][0],"steps_description":manual[k][1],
            "step_count_measurement":"Processing operations, excluding baseline operations. For A/D generic VTK results audit geometry separately.",
            "additional_steps_geometry_audit":casefile(k,"paraview_excavation_extras.json"),
            "Sim2Web_excavation_layers":[x["id"] for x in sim["stage"].get("layers",[]) if x.get("kind")=="excavation"]},
        "M8":{"ParaView_extract_surface_faces":base.get("surface_faces"),"ParaView_extract_surface_bytes":size.get("surface.vtp"),"Sim2Web_exterior_faces":ext.get("cells"),"Sim2Web_exterior_bytes":ext.get("bytes"),"Sim2Web_internal_faces":sim["stage"].get("internal_faces")},
        "M9":{"ParaView":"Extract Surface IDs may exist only in intermediate VTP. Glance does not provide direct source VTU point/cell drill-through in this experiment.",
              "Sim2Web":{"source_point_ids":"Source_Point_ID" in primary.get("point_arrays",[]),"source_cell_ids":"Source_Cell_ID" in primary.get("cell_arrays",[])}},
        "M10":{"ParaView_sections":base.get("sections"),"ParaView_archive_audit":{key:val for key,val in casefile(k,("paraview_corrected/" if k in "AC" else "")+"scene_arrays.json").items() if key!="actor_arrays"},"ParaView_interaction":"Slice actors, individual visibility, no ordered section slider.",
               "Sim2Web_sections":sim["sections"],"Sim2Web_interaction":"Axis and section slider."},
        "M11":{"ParaView":"No independent archive-to-VTU verification in the default workflow.","Sim2Web_validate_exit":sim["validate_exit"],
                "Sim2Web_validation_failures":sim["failures"],"Sim2Web_validation":sim["validation"]}
    }
    src=f"cases/{k}"
    pvdir="paraview_corrected/" if k in "AC" else ""
    row(f"表 3 / M1 / 算例 {k}","ParaView "+(f"{pv_trace['lines_total']:,} 行（有效 {pv_trace['nonblank_noncomment']:,}）" if pv_trace else "未取得完整桌面 Trace")+
        f"；Sim2Web 改 {d.get('changed_lines','未测')} 行，{clicks if clicks is not None else '未测'} 次点击",
        f"{src}/paraview_gui_native_trace.py、{src}/paraview_gui_trace_audit.json、{src}/draft_delta.json、workbench/{k}/click_count.json",
        "桌面宏生成的行数与纯手工流程分列。Sim2Web 有序归一化 YAML 差异；点击从已载入配置开始。"+("GUI Trace 包含读入、剖切与导出调用。" if use_gui else "纯手工完整 GUI Trace 尚未实测。"))
    row(f"表 3 / M2 / 算例 {k}",f"ParaView pvpython {fmt(base.get('elapsed_wall_seconds'))} s，桌面宏 {fmt(qt.get('seconds'))} s；Sim2Web 构建 {fmt(sim['seconds'])} s，验证 {fmt(sim['validate_seconds'])} s",
        f"{src}/{pvdir}paraview_baseline_report.json；logs/034_build_{k}.json；logs/035_validate_{k}.json","同机；桌面宏直接导出，pvpython 另含逐个写出 VTP。纯手工操作时间未测；替代模板重封装时间单列于对比 JSON。")
    row(f"表 3 / M3 / 算例 {k}",f"Glance HTML {sz(gv)}；vtkjs {sz(size.get('scene.vtkjs'))}；ParaView 表面 {sz(size.get('surface.vtp'))}；Sim2Web 主表面 {sz(primary.get('bytes'))}、完整站点 {sz(sim['all_bytes'])}",
        f"{src}/{pvdir}paraview_baseline_report.json；{src}/{pvdir}scene_kitware_size.json；{src}/build_report.json；{src}/site_size.json",
        "Glance HTML 使用 Kitware 官方可绘制模板。站点排除验证输出；十进制 MB。")
    row(f"表 3 / M4 / 算例 {k}",f"Glance {fmt(bg['median_first_image_ms'],1)} ms（{bg['rendered_runs']}/3），Sim2Web {fmt(bs['median_first_image_ms'],1)} ms，首帧传输 {sz(bs['median_startup_bytes'])}，剖面切换 {fmt(bs['median_section_switch_ms'],1)} ms",
        f"{bg['clock_source']}；{src}/sim2web_browser.json",
        "Chrome 冷缓存回环测试。使用 Kitware 查看器与同一 vtkjs 文件分开加载的流程。模型几何提交（至少 10,000 个索引）和两次动画帧计时，坐标轴控件已排除。Sim2Web 使用查看器 firstRender。")
    row(f"表 3 / 开挖面手工步骤 / 算例 {k}",f"新增 {manual[k][0]} 个处理操作", "comparison_results.json / M7",manual[k][1]+" 算例 A/D 的追加处理见 cases/"+k+"/paraview_excavation_extras.json。")

for k in "DF":
    d=casefile(k,"paraview_principal.json")
    for comp_key, label in (("min","最小"),("mid","中间"),("max","最大")):
        q=d.get("principal",{}).get(comp_key,{})
        row(f"结果 §4 / 主应力 / {k} / {label}",f"{fmt(q.get('max_abs_error'),6)} MPa（{fmt(q.get('max_error_percent_of_range'),4)}%）",
            f"cases/{k}/paraview_principal.json","百分比分母为正确主应力全色标跨度。")
    q=d.get("principal",{}).get("max",{})
    row(f"结果 §4 / 算例 {k} / 仅通用结果受拉",f"{q.get('cells_positive_generic_but_not_correct','未测')} 个 / {d.get('retained_cells','未测')} 个保留单元",
        f"cases/{k}/paraview_principal.json","最大主应力仅在通用结果中大于 0。")

audit=casefile("D","excavation_audit.json")
ex=audit.get("excavation_boundary") or {}
below=audit.get("depth_audit",{}).get("-57.5",{})
below_tol=audit.get("depth_audit",{}).get("-57.5013",{})
strict=below.get("centroid_below",{}).get("faces")
nominal=below.get("nominal_floor_faces",{}).get("faces")
other=below.get("other_centroids_below",{}).get("faces")
deep=below_tol.get("centroid_below",{}).get("faces")
row("结果 §4 / 算例 D / 开挖面",f"{audit.get('published_excavation_faces','未测')} 面；{fmt(audit.get('published_excavation_area_m2'))} m²；移除 {ex.get('internal_faces_removed','未测')} 面",
    "cases/D/excavation_audit.json；cases/D/build_report.json","面积在发布的 PolyData 上逐面求和。")
row("结果 §4 / 算例 D / 坑底以下",f"面心 z < −57.5 m 为 {strict}；名义坑底 {nominal}；其余 {other}；面心 z < −57.5013 m 为 {deep}",
    "cases/D/excavation_audit.json","同时提供任一、全部顶点低于平面的口径。名义坑底实际坐标约 −57.5003 m。")
row("结果 §4 / 算例 D / 外表面",f"{m['D']['exterior'].get('cells','未测')} 面；{sz(m['D']['exterior'].get('bytes'))}",
    "cases/D/index.json；cases/D/excavation_audit.json","记录 r3–r4 前后版本。")

for k in "ABCDF":
    t=m[k]
    src=f"cases/{k}"
    row(f"表 4 / 算例 {k} / Windows 构建",f"{fmt(t['seconds'])} s",
        f"logs/034_build_{k}.json","单次构建命令 wall clock；验证单独执行。测量期间机器还有并行任务。")
    if k in "DF":
        row(f"表 4 / 算例 {k} / 表面、剖面、完整包",f"主表面 {t['primary'].get('cells','未测')} 面，{sz(t['primary'].get('bytes'))}；剖面 {t['sections']}；VTP 合计 {sz(t['vtp_bytes'])}；完整站点 {sz(t['all_bytes'])}",
            f"{src}/index.json；{src}/build_report.json；{src}/site_size.json","表 4 原有包大小的 VTP 口径与完整静态站点分别列出。")

for k in "DF":
    wb=wbfile(k,"workbench_timing.json")
    steps=wb.get("steps",{})
    worst=[v["ui_latency_worst_s"] for v in steps.values()]
    row(f"结果 §4 / 工作台耗时 / 算例 {k}","；".join(f"{label} {fmt(steps.get(s,{}).get('seconds'))} s" for label,s in zip(("读取","预览","构建","验证"),("read_model (inspect)","preview (surfaces)","build (full)","validate (every 5th section)")))+f"；最慢请求 {fmt(max(worst) if worst else None)} s",
        f"workbench/{k}/workbench_timing.json","验证每 5 个剖面抽 1 个。")
h=casefile("H","r3_r4_difference.json")
row("例 H / MOOSE 自动转换",f"默认 t=2；--time first 得 t=0；应力最大绝对差 {fmt(h.get('stress_max_abs'),6)}；位移最大绝对差 {fmt(h.get('displacement_max_abs'),6)}",
    "cases/H/r3_r4_difference.json；logs/043_moose_last.log；logs/044_moose_first.log","按坐标和单元连通性对齐；将 ZX 与 XZ 视为同一分量。")
for k in "DF":
    shot=root/f"cases/{k}/viewer_1600x900.png"
    row(f"算例 {k} / 查看器图",("1600×900" if shot.is_file() else "未完成"),f"cases/{k}/"+("viewer_p5_p95_1600x900.png" if k=="F" else "viewer_1600x900.png"),"使用仓库 benchmark/screenshots.mjs。")
for num in (15,16,17,20,22):
    row(f"参考文献 [{num}]","作者、年份、刊物、DOI/网页及访问日期见核对表","REFERENCES.md；references_crossref.json","[17] 包含官方源码分量顺序原文。[22] 区分原论文和 3.0 更新。")
for pos, note in [
    ("应用与反馈","稿件未附实际项目清单、人数、反馈原文或可核验出处。"),
    ("代码发布 / C2、C4 / Zenodo DOI","本次核验开发提交 722176f。正式发布、托管名称、正式引用提交及 DOI 待稿件作者提供。"),
    ("数据可用性 / 算例 F 数据权属","本地数据用于授权验证，权属和可公开许可待作者确认。"),
    ("声明格式 / SoftwareX","Elsevier 通用作者政策要求如使用生成式 AI 准备稿件，在参考文献前设独立声明。SoftwareX 本刊指南页面返回 403，投稿端具体字段及事实仍待作者确认。见 REFERENCES.md。"),
    ]:
    row(pos,"待补","manuscript_highlights.json",note)

hdr="# Sim2Web r4 稿件填数表\n\nWindows 11 中文版，同一工作站。MB = 1,000,000 B。路径相对本次交付目录。\n\n"
table=["| 位置 | 数值 | 来源文件 | 备注 |","|---|---|---|---|"]
table += ["| "+" | ".join(str(x).replace("|","\\|").replace("\n"," ") for x in row)+" |" for row in nums]
write("MANUSCRIPT_NUMBERS.md",hdr+"\n".join(table))
write("comparison_results.json",json.dumps({"version":"ParaView 5.13.3 / Sim2Web 722176f / Chrome 160.0.8157.0",
    "host":"Windows 11 build 26300, Intel i7-10750H, 15.8 GiB, Intel UHD Graphics / Quadro P620", "cases":comp},ensure_ascii=False,indent=2))
compmd=["# Windows ParaView / Glance 与 Sim2Web 对比","","| 项目 | A | C | D |","|---|---|---|---|"]
def add(name, fn):
    compmd.append("| "+name+" | "+" | ".join(fn(k,comp[k]) for k in "ACD")+" |")
add("M1 Trace 有效行 / Sim2Web 改行、点击",lambda k,d:f"{(d['M1']['ParaView_GUI_native_trace'] or {}).get('nonblank_noncomment','未测')} / {d['M1']['Sim2Web_changed_config_lines']} 行、{d['M1']['Sim2Web_workbench_clicks_from_seeded_config']} 次")
add("M2 pvpython / Sim2Web 构建 / 验证 (s)",lambda k,d:" / ".join(fmt(d["M2"].get(n)) for n in ("ParaView_pvpython_package_seconds","Sim2Web_build_seconds","Sim2Web_validate_seconds")))
add("M3 Glance 官方模板 HTML / Sim2Web 站点",lambda k,d:sz(d["M3"]["ParaView_official_template_html_bytes"])+" / "+sz(d["M3"]["Sim2Web_static_site_bytes"]))
add("M4 首帧中位数 (ms) Glance / Sim2Web",lambda k,d:fmt(d["M4"]["ParaView_Glance"]["median_first_image_ms"],1)+" / "+fmt(d["M4"]["Sim2Web"]["median_first_image_ms"],1))
add("M5 通用结果误判受拉",lambda k,d:str(d["M5"]["ParaView"].get("principal",{}).get("max",{}).get("cells_positive_generic_but_not_correct","见协议")))
add("M6 Sim2Web 应力量纲",lambda k,d:str((d["M6"].get("Sim2Web") or {}).get("status","见 JSON")))
add("M7 增加分离开挖面的处理操作",lambda k,d:str(d["M7"]["additional_user_steps_for_equivalence"]))
add("M8 ParaView / Sim2Web 外表面面数",lambda k,d:f"{d['M8']['ParaView_extract_surface_faces']} / {d['M8']['Sim2Web_exterior_faces'] if k!='A' else '主层为开挖面'}")
add("M9 Sim2Web 源单元、节点 ID",lambda k,d:"有 / 有" if all(d["M9"]["Sim2Web"].values()) else str(d["M9"]["Sim2Web"]))
add("M10 ParaView / Sim2Web 剖面数",lambda k,d:f"{d['M10']['ParaView_sections']} / {d['M10']['Sim2Web_sections']}")
add("M11 Sim2Web validate 退出码",lambda k,d:str(d["M11"]["Sim2Web_validate_exit"]))
compmd += ["","同机脚本打包与桌面 GUI Trace 是两份证据。Glance 首帧采用分开载入官方查看器和 vtkjs，独立 HTML 使用同一数据并单列体积。逐项目径、全部浏览器试次、验证和原始文件路径见 `comparison_results.json` 与 `MANUSCRIPT_NUMBERS.md`。"]
write("comparison_results.md","\n".join(compmd))
