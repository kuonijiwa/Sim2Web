"""Build the r8 report from measured outputs and a command ledger."""
import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mb(n):
    return f"{n / 1e6:.3f}" if n is not None else "—"


def percentile(values, p):
    ordered = sorted(values)
    k = (len(ordered)-1)*p
    a,b = math.floor(k),math.ceil(k)
    return ordered[a]+(k-a)*(ordered[b]-ordered[a])


parser=argparse.ArgumentParser()
parser.add_argument("evidence",type=Path)
parser.add_argument("logs",type=Path)
parser.add_argument("dataset",type=Path)
args=parser.parse_args()
d=args.evidence
rows=[read(p) for p in sorted(args.logs.glob("*.json"))]
ledger={r["id"]:r for r in rows}
with (d/"COMMANDS.csv").open("w",encoding="utf-8-sig",newline="") as file:
    w=csv.DictWriter(file,fieldnames=["id","command","cwd","started_at","exit_code","duration_seconds"],extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

audit=read(d/"example_audit.json")
survey=read(d/"site_survey/stage_list.json")
remote=read(d/"site_survey/file_sizes.json")
figure=read(d/"stage_figure_print_check.json")
manifest=read(Path("examples/DATA_SOURCES.json"))
assert read(args.dataset/".zenodo.json")["license"]=="cc-by-4.0"
assert all((args.dataset/item["archive"]).stat().st_size==item["bytes"] for item in manifest["cases"].values())
text=["# Sim2Web r8 验证和交付", "", "基线 `ae5b84d`，分支 `r8/release`。原生命令、退出码和耗时见 `COMMANDS.csv`。", "",
      "## Part 0 · r7 插图", "", "两张 600 dpi PNG、原尺寸校样 PDF 和 `print_check.json` 单独上传。"
      "结果 bundle 按不超过 9 MB 切分，`SHA256SUMS` 同时给出完整 bundle 和分卷的 SHA-256。"
      "恢复时按文件名顺序拼接 `.part00`、`.part01` 等，再核对完整文件。Git LFS 的 VTU 和 VTP 在 Git bundle 中以指针记录。", "",
      "## Part C · 算例 D 和 F", "", "| 算例 | 层 | r4 / r8 面数 | r4 / r8 VTP 字节 | r4 / r8 剖面数 | r4 / r8 数据产品字节 |",
      "|---|---|---:|---:|---:|---:|"]
for case in ("D","F"):
    data=audit[case]
    r4=next(iter(data["r4"]["stages"].values()))
    r8=next(iter(data["r8"]["stages"].values()))
    for layer,new in r8["layers"].items():
        old=r4["layers"][layer]
        text.append(f"| {case} | {layer} | {old['faces']:,} / {new['faces']:,} | {old['bytes']:,} / {new['bytes']:,} | "
                    f"{r4['sections']} / {r8['sections']} | {r4['product_bytes']:,} / {r8['product_bytes']:,} |")
    assert not data["r8"]["failures"]
text.append("")
for case in ("D","F"):
    a=audit[case]
    text.append(f"- {case} 的完整 `site` 为 {a['r8']['site_bytes']:,} 字节，r4 为 {a['r4']['site_bytes']:,} 字节，差值 {a['whole_site_delta_bytes']:+,} 字节。独立验证通过。"
                +("阶段产品统计逐项一致。" if a["product_records_match"] else "阶段产品统计差异见 `example_audit.json`。"))
    if a["size_changes"]:
        text[-1]+="大小有变化的文件为 "+"、".join(f"`{name}`（{delta:+,} 字节）" for name,delta in a["size_changes"].items())+"。"
exc=next(iter(audit["D"]["r8"]["stages"].values()))["excavation"]
text.extend([f"- D 开挖面积 {exc['area']:.3f} m²。独立验证摘要放在例子的发布包内。", "", "### 测试", "",
             "| 套件 | 结果 | 退出码 | 耗时（s） |", "|---|---|---:|---:|"])
for id,title in (("012_python_default","Python 常规"),("013_viewer","查看器"),("014_workbench","工作台"),("016_realdata","Python realdata")):
    job=ledger[id]
    log=(args.logs.parent/job["log"]).read_text(encoding="utf-8-sig",errors="replace")
    if id.startswith(("013","014")):
        m=re.search(r"\bpass\s+(\d+)",log)
        label=f"{m[1]} passed" if m else "见命令记录"
    else:
        matches=re.findall(r"^.*\b(?:passed|failed|skipped|error)\b.* in \d+\.?\d*s.*$",log,re.M)
        label=matches[-1].strip("= ") if matches else "见命令记录"
    text.append(f"| {title} | {label} | {job['exit_code']} | {job['duration_seconds']:.2f} |")
assert all(ledger[x]["exit_code"]==0 for x in ("012_python_default","013_viewer","014_workbench","016_realdata"))
text.extend(["", "默认 Python 的 realdata 由环境变量单独启用。D、F 加入当前配置验证。历史产品的字节回归仍只对拥有参考样本的 A、B、C 执行。",
             "测试对 `site_v01` 的引用为 " + ("、".join(audit["site_v01_test_references"]) or "0 条。现有字节回归读取 `output/model_cache/`。"),
             "搜索到的 `site_v01` 目录为 " + ("、".join(audit["site_v01_directories"]) or "0 个。"),
             "", "### Git LFS 和 Zenodo 数据包", "",
             "| 算例 | Git LFS 输入（MB） | Git LFS `site/`（MB） | Git LFS `output/`（MB） | 实际 `site`（MB） | Zenodo ZIP（MB） |",
             "|---|---:|---:|---:|---:|---:|"])
for case, record in audit["lfs"].items():
    text.append(f"| {case} | {mb(record['input']['bytes'])} | {mb(record['site']['bytes'])} | {mb(record['output']['bytes'])} | "
                f"{mb(record['built_site_on_disk_bytes'])} | {mb(manifest['cases'][case]['bytes'])} |")
text.extend(["", f"A–F 的已跟踪 LFS 合计 {audit['lfs_logical_A_to_F_bytes']:,} 字节。"
             f"按 SHA-256 对对象去重后为 {audit['lfs_unique_A_to_F_bytes']:,} 字节。MB 按 1,000,000 字节计。"
             "A–C 的 `output/` 是随仓库提供的历史回归产品，A–C 和 E 的本地 `site/` 大小取实有 r4 工作站构建。E 继续提供由求解器生成输入的流程。",
             f"本地 `dist/zenodo_dataset/` 备有 {len(manifest['cases'])} 个经 CRC 和 SHA-256 核验的 ZIP、校验清单、README 和 CC BY 4.0 的 Zenodo 元数据草稿。"
             "草稿作者按稿件顺序。`tools/fetch_example_data.py` 检查 ZIP 字节数、SHA-256 和成员，`examples/DATA_SOURCES.json` 保留待发表的记录 ID。",
             "", "## Part D · 五个施工步", "", f"用 Chrome {survey['chrome']} 打开公开站并保存截图。索引为旧版按施工步名分组的结构，未声明 schema。"
             "模型为 FLAC3D 地下洞室。每个施工步均列出开挖面、X/Y/Z 剖面和 12 个字段标识。字段包括位移、主应力、法向应力与组别。",
             "", "| 旧站施工步 | 表面字节 | 剖面数 X/Y/Z | 剖面字节合计 | 取得大小的文件数 |", "|---|---:|---|---:|---:|"])
for s in survey["stages"]:
    t=next((r for r in remote if r["id"]==s["id"]),{})
    counts=s["sectionCounts"]
    fmt=lambda n:f"{n:,}" if n is not None else "未取得"
    text.append(f"| {s['id']} | {fmt(t.get('surfaceBytes'))} | {counts['x']} / {counts['y']} / {counts['z']} | "
                f"{fmt(t.get('sectionsBytes'))} | {t.get('measuredFiles',0)}/{1+sum(counts.values())} |")
text.extend(["", "旧站大小来自已列出产品的 HTTP HEAD 响应。请求逐个发送，每秒最多两次。未取得尺寸的响应按记录保留。",
             "本地用用户提供的五个源 VTU 按公开索引顺序构建，沿用旧站索引中的剖面位置。新版 `sim2web-index/2`，完整独立验证通过。",
             "", "| 阶段 | 源单元 | 开挖面面数 | 开挖面积（m²） | 剖面数 | VTP 数据产品字节 |", "|---|---:|---:|---:|---:|---:|"])
for name, s in audit["STAGES"]["stages"].items():
    b=s["excavation"]
    text.append(f"| {name} | {s['source_cells']:,} | {b['faces']:,} | {b['area']:.3f} | {s['sections']} | {s['product_bytes']:,} |")
text.extend(["", "### Chrome 阶段切换", "", "1600×900，三次新浏览器进程，禁用 HTTP 缓存和邻近预取。"
             "第二组使用 CDP 的 20/5 Mbit/s、50 ms。切换由原版查看器 API 执行，计时到第二个动画帧，网络量为 CDP 的 HTTP 编码字节。",
             "返回已经访问的阶段时，保留产品加载器原有的内存缓存。原始数据按每次切换保存。", "",
             "| 网络 | 首帧中位数（ms） | 首帧中位传输（MB） | 切换样本 | 合计中位 / P95（ms） | 轴保留 | 位置保留 |",
             "|---|---:|---:|---:|---:|---:|---:|"])
net_data={}
for net in ("LAN","4G"):
    trials=read(d/f"stage_benchmark_{net}.json")["runs"]
    assert len(trials)==3 and all(len(r["switches"])==8 and not r["errors"] for r in trials)
    switches=[s for row in trials for s in row["switches"]]
    net_data[net]=switches
    times=[x["latencyMs"] for x in switches]
    text.append(f"| {net} | {statistics.median(r['firstFrameMs'] for r in trials):.1f} | {mb(statistics.median(r['firstFrameBytes'] for r in trials))} | "
                f"{len(switches)} | {statistics.median(times):.1f} / {percentile(times,.95):.1f} | "
                f"{sum(x['axisKept'] for x in switches)}/{len(switches)} | {sum(x['positionKept'] for x in switches)}/{len(switches)} |")
text.extend(["", "| 网络 | 切换 | 中位传输（MB） | 中位 / P95（ms） |", "|---|---|---:|---:|"])
for net, switches in net_data.items():
    for pair in dict.fromkeys((s["from"],s["to"]) for s in switches):
        events=[s for s in switches if (s["from"],s["to"])==pair]
        latency=[s["latencyMs"] for s in events]
        text.append(f"| {net} | {pair[0]} → {pair[1]} | {mb(statistics.median(s['encodedHttpBytes'] for s in events))} | "
                    f"{statistics.median(latency):.1f} / {percentile(latency,.95):.1f} |")
lo,hi=figure["capture_state"]["limits"]
text.extend(["", "### 印刷图", "", f"I-1、II-2、IV-2 从同一正交相机截取，使用最小主应力和共同色标 {lo:.3f} 至 {hi:.3f} MPa。"
             "范围取五个阶段合并的开挖面面值 P5–P95，端点外钳位。"
             f"图宽 {figure['width_cm']} cm，PNG 标称 600 dpi，色标最小字高 {figure['legend_min_text_pt']:.2f} pt。"
             "截图注入 CSS 和像素核验见 `stage_figure_print_check.json`。", "", "Firefox 为可选，未补测。", ""])
(d/"REPORT_r8.md").write_text("\n".join(text),encoding="utf-8")
print("Report built with",len(rows),"recorded commands")
