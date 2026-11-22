import csv,json,sys
from pathlib import Path
from PIL import Image
root,work=map(Path,sys.argv[1:])
def read(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))
entries=[]
for p in sorted((root/"logs").glob("*.json")):
    o=read(p)
    if isinstance(o,dict) and "command" in o:
        entries.append(o)
by_id={r["id"]:r for r in entries}
with (root/"COMMANDS.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["id","started_at","cwd","command","exit_code","duration_seconds","log"])
    w.writeheader()
    w.writerows([{k:r.get(k) for k in w.fieldnames} for r in entries])
base=(work/"report_base.md").read_text(encoding="utf-8-sig")
short=(root/"comparison_results.md").read_text(encoding="utf-8-sig")
base=base.replace("\n## 7. 交付与命令记录","\n"+short.replace("# Windows ParaView / Glance 与 Sim2Web 对比","### 可复核的比较摘要")+"\n## 7. 交付与命令记录")
snap=[]
for k in "ABCDEF":
    d=root/"cases"/k
    b=read(d/"build_report.json")
    idx=read(d/"index.json")["stages"][0]
    a=next(v for v in idx["layers"] if v["role"]=="primary")
    s=read(d/"site_size.json")
    v=read(d/"validation_summary.json")
    snap.append((k,a["cells"],a["bytes"],b["stages"][0]["section_count"],b["stages"][0]["output_bytes"],
       int(s["full_site_without_validation_bytes"]),by_id[f"034_build_{k}"]["duration_seconds"],
       by_id[f"035_validate_{k}"]["duration_seconds"],len(v["failures"])))
rows=["","### 单次构建结果","","| 案例 | 主表面面数 | 主表面 B | 剖面 | 全部 VTP B | 完整站点 B | 构建 s | 验证 s | 验证失败 |","|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
rows.extend("| "+f"{k} | {n:,} | {p:,} | {c:,} | {v:,} | {b:,} | {t:.3f} | {s:.3f} | {f}"+" |" for k,n,p,c,v,b,t,s,f in snap)
base=base.replace("\n## 3. Abaqus","\n"+"\n".join(rows)+"\n\n## 3. Abaqus")
images={}
for p in sorted(root.rglob("*.png")):
    try:
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            images[str(p.relative_to(root)).replace("\\","/")]=list(im.size)
    except OSError:
        continue
wanted=["cases/D/viewer_1600x900.png","cases/D/excavation_from_below_1600x900.png","cases/F/viewer_1600x900.png"]
assert all(images[n]==[1600,900] for n in wanted)
(root/"screenshots_dimensions.json").write_text(json.dumps(images,indent=2)+"\n",encoding="utf-8")
manual=["","### GUI 与后台命令索引","","- ParaView 桌面在 Tools → Start Trace 开始录制，A 从 File → Open 和 Apply 读取，然后通过 View → Python Shell → Run Script 运行 `repro_scripts/pv_gui_trace.py`。批量启动本身不产生 CLI 退出码，桌面脚本有逐案成功或错误状态。","- Glance 首轮、自带模板和启用主应力前的探测各自保留，退出码或停止证据见日志 072、073、081、109。","- `COMMANDS.csv` 含执行目录、起始时间、完整命令和日志路径。Windows 工作台各子命令见 `workbench/*/commands.json`。各外部 ParaView argv 见 `cases/*/paraview{_corrected/, _command.json}` 对应目录。","","| 编号 | 实际命令或记录的操作 | 退出码 | wall s | 关键输出 |","|---|---|---:|---:|---|"]
for q in entries:
    cmd=q["command"].replace("|","\\|").replace("`","'").replace("\n"," ")
    loc=q["log"]
    manual.append(f"| {q['id']} | `{cmd}` | {q['exit_code']} | {q['duration_seconds']:.3f} | [{Path(loc).name}]({loc}) |")
(root/"REPORT.md").write_text(base.rstrip()+"\n"+"\n".join(manual)+"\n",encoding="utf-8")
print("Commands",len(entries),"verified image headers",len(images))
