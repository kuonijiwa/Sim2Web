"""Collect the measured r6 records and render Table 6 without filling gaps."""
import argparse
import csv
import json
import math
import shutil
import statistics as st
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("scratch",type=Path)
p.add_argument("--complete",action="store_true")
a=p.parse_args()
w=a.scratch
root=Path(__file__).resolve().parents[2]
ev=root/"paper_evidence/web_slicing_figures_stages"
dest=ev/"web_slicing"
dest.mkdir(parents=True,exist_ok=True)

def read(path,default=None):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else default

def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def md(path,data):
    path.write_text(data.rstrip()+"\n",encoding="utf-8")

def pct(values,fraction):
    xs=sorted(values)
    if not xs:return None
    k=(len(xs)-1)*fraction
    lo=math.floor(k)
    hi=math.ceil(k)
    return xs[lo]+(xs[hi]-xs[lo])*(k-lo)

def median(values):
    vals=list(values)
    return st.median(vals) if vals else None

def quant(values):
    return [pct(values,.5),pct(values,.95)]

def ready_breakdown(r,method):
    if method=="B":
        return {k:median(x["first"]["ready"].get(k) for x in r if x["first"]["ready"] and k in x["first"]["ready"])
                for k in ("download","parse","index","firstCut")}
    if method=="W":
        raw=[t for x in r for t in x["first"]["ready"] if t.get("role")=="section"]
        return {k:median(t[k] for t in raw if k in t) for k in ("fetchMs","parseMs")}
    return {}

def summarize(r):
    first=[x for x in r["cold"] if x.get("first")]
    switches=[x.get("timing",{}).get("ms") for x in r["switches"]]
    switches=[x for x in switches if isinstance(x,(int,float))]
    num=lambda selector:max((selector(x) or 0 for x in r["cold"]),default=0) or None
    s=r.get("server") or {}
    cpu_start=r.get("switchCpuStart") or {}
    cpu_end=r.get("switchCpuEnd") or {}
    agreement={i["index"]:i["vtk_reference_agreement"] for i in s.get("allEvents",[]) if "vtk_reference_agreement" in i}
    ready=ready_breakdown(first,r["method"]) if first else {}
    return {
      "cold_first_count":len(first),"cold_attempts":len(r["cold"]),"cold_ok_count":sum(x["status"]=="ok" for x in r["cold"]),
      "switch_count":len(switches),
      "first_seconds":median(x["first"]["ms"]/1000 for x in first),
      "first_bytes":median(sum(x.get("transferAtFirst",{}).values()) for x in first),
      "first_rx_bytes":median(x["transferAtFirst"]["httpBytes"]+x["transferAtFirst"]["incomingWsBytes"] for x in first),
      "ready_ms":ready,"js_heap_bytes":num(lambda x:x.get("jsHeapPeak",0)),
      "chrome_rss_bytes":num(lambda x:(x.get("memory") or {}).get("chrome_rss",0)),
      "server_peak_bytes":num(lambda x:(x.get("memory") or {}).get("python_rss",0)) if s else None,
      "server_start_ms":s.get("startupWallMs"),"server_source_read_s":(s.get("load") or {}).get("source_read_s"),
      "server_model_derive_s":(s.get("load") or {}).get("model_and_derive_s"),
      "server_first_cut_s":(s.get("load") or {}).get("first_cut_s"),
      "s_cpu_seconds":cpu_end["server_cpu_s"]-cpu_start["server_cpu_s"] if s and cpu_end and cpu_start else None,
      "switch_median_p95_ms":quant(switches),
      "warmup_median_p95_ms":quant([x["timing"]["ms"] for x in r.get("warmup",[])]),
      "cached_w_switches":sum(bool(x["timing"].get("cached")) for x in r["switches"]) if r["method"]=="W" else None,
      "ws_in_bytes_per_switch_median":median(x["wire"]["wsIn"] for x in r["switches"]) if s else None,
      "server_matches_vtk":{str(k):v for k,v in agreement.items()},
      "server_switch_cut_median_ms":median(x["cut_s"]*1000 for x in s.get("allEvents",[])[11:] if "cut_s" in x),
      "browser_gpus":sorted(set(x["first"]["gpu"] for x in first if x["first"].get("gpu"))),
      "errors":[{"run":x["run"],"error":x.get("error"),"crash":bool(x.get("crashed"))} for x in r["cold"] if x.get("error") or x.get("crashed")],
    }

methods=("B","S-local","S-remote","W")
networks=("LAN","4G")
cases=("A","C")
result={"cases":{},"matrix":{},"units":{"memory_and_transfer": "1 MB = 1,000,000 bytes","first_time": "s","switch_times": "ms"}}
for k in cases:
    meta=read(w/f"data_{k}/case.json",{})
    correct=read(w/f"check_{k}/correctness.json",{})
    check=read(w/f"site_{k}/validation/validation_summary.json",{})
    for n,d in ((f"{k}_positions_and_payload.json",meta),(f"{k}_browser_vtk_correctness.json",correct),(f"{k}_sim2web_validation.json",check)):
        write(dest/n,d)
    result["cases"][k]={"metadata":meta,"browser_vtk_correctness":correct,"sim2web_validation":check}
    for mode in methods:
        for network in networks:
            ident=f"{k}_{mode}_{network}"
            path=w/f"trial_{ident}"
            raw=read(path/"trial.json")
            if raw is None:continue
            result["matrix"][ident]={"metrics":summarize(raw),"trial":raw}
            if a.complete and network=="LAN" and (path/"section_1600x900.png").is_file():
                (dest/"captures").mkdir(exist_ok=True)
                shutil.copyfile(path/"section_1600x900.png",dest/"captures"/f"{ident}.png")
result["websocket_validation"]=read(w/"websocket_probe.json")
result["frame_check"]=read(w/"frame_check.json")
if result["frame_check"]:
    write(dest/"frame_check.json",result["frame_check"])
write(dest/"results.json",result)

def number(x,places=2):
    return f"{x:.{places}f}" if isinstance(x,(int,float)) else "—"
def metric(k,m,n):return result["matrix"].get(f"{k}_{m}_{n}",{}).get("metrics",{})
def g(k,m,n,key):return metric(k,m,n).get(key)
def mb(x):return number(x/1e6) if x is not None else "—"
def pair(x):return " / ".join(number(v,1) for v in x) if x else "—"
def row(n,title,spec):
    f=lambda mode:" / ".join(f"{k} {spec(metric(k,mode,n))}" for k in cases)
    return f"| {title} | {f('B')} | Local {f('S-local')}<br>Remote {f('S-remote')} | {f('W')} |"

table=["# Table 6. Sectioning in the browser on the Windows workstation",
       "", "A / C means Case A followed by Case C. MB uses decimal bytes. Browser memory is peak CDP JS heap / peak summed Chrome working set. "
       "First view uses the median of five cold browser launches. Switch latencies are median / p95 for 50 changes after one ten-position warm-up sweep.",
       ""]
for n in networks:
    table += [f"## {'Site 4G' if n=='4G' else n}","",
              "| Item | Browser-side slicing | Server-side slicing (trame) | Sim2Web build-time sections |",
              "|---|---|---|---|",
              row(n,"Transfer before first section (MB)",lambda r:mb(r.get("first_bytes"))),
              row(n,"Time to first section (s)",lambda r:number(r.get("first_seconds"),3)),
              row(n,"Browser memory peak (MB)",lambda r:mb(r.get("js_heap_bytes"))+" / "+mb(r.get("chrome_rss_bytes"))),
              row(n,"Server memory peak (MB)",lambda r:mb(r.get("server_peak_bytes"))),
              row(n,"Server start + model ready (s)",lambda r:number(r["server_start_ms"]/1000,3) if r.get("server_start_ms") else "—"),
              row(n,"Per-section switch (ms)",lambda r:pair(r.get("switch_median_p95_ms"))),
              row(n,"Server CPU for 50 switches (s)",lambda r:number(r.get("s_cpu_seconds"),3)),
              "| Server needed | Static hosting suffices | Running VTK/trame service | Static hosting suffices |",
              "| Section position | Arbitrary | Arbitrary | Fixed during the build |",
              "| Values checked | JS cuts vs vtkCutter | Server vtkCutter arrays vs independent reference export | sim2web validate |",""]
table += ["The trame entries count WebSocket payload bytes plus CDP HTTP response bytes. WebSocket framing and TCP overhead are excluded.",
          "Sim2Web's stock LRU served warmed repetitions in this protocol. See results.json for the first, unwarmed sweep and the exact cached flags."]
md(dest/"table6.md","\n".join(table))

checks=["| 公平性检查 | 结果 | 依据 |","|---|---|---|",
        "| 同位置、位移场、色图、窗口和相机 | 是 | 每案从发布索引等距取十个 x 位置。只显示位移模长剖面，均用 jet 八色阶、同案 full range、相同 x 向正交相机和 1600×900 窗口。LAN 和 4G 的末位置实拍与浏览器端并排核对，轮廓重合度见 `frame_check.json`。 |",
        "| 首次加载为新 profile 和冷 HTTP 缓存 | 是 | Chrome 进程逐次新起，CDP 禁用 HTTP 缓存。服务端先加载模型，服务启动和模型准备时间单计。 |",
        "| 重复测试的应用缓存机制等同 | 否 | Sim2Web 保留其默认 VTP 内存 LRU。B 重切，trame 重切并传输。原始记录附首次扫过位置的延迟和 W 的 cached 字段。 |",
        "| 同一帧完成定义 | 是 | 剖面绘制完成或对应剖面编号的服务端图像成功解码后等待两个浏览器动画帧。trame 切换同时核对了服务端修订号。 |",
        "| Site 4G 作用到 trame WebSocket | 是 | 本机 256 KiB 双向回显验证 Chrome CDP 会限速，正式试验不额外叠加帧代理。 |",
        "| 使用可比 GPU | 是 | 浏览器端为 Chrome WebGL 报告的 Intel UHD / ANGLE D3D11。S-remote 的实际模型绘制在服务进程，Chromium 只解码公开样例图像。 |"]
md(dest/"fairness.md","\n".join(checks))

ready_table=["| 网络 | 算例 | 方法 | 首帧样本 | 切换样本 | 准备细项 |","|---|---|---|---:|---:|---|"]
for n in networks:
    for k in cases:
        for m in methods:
            d=metric(k,m,n)
            parts=[]
            if m=="B":parts=[f"{label} {number(d.get('ready_ms',{}).get(key),1)} ms" for key,label in
                             (("download","下载"),("parse","解析"),("index","索引"),("firstCut","首刀"))]
            elif m=="W":parts=[f"首剖面 {label} {number(d.get('ready_ms',{}).get(key),1)} ms" for key,label in (("fetchMs","下载"),("parseMs","解析"))]
            else:parts=[f"服务读原文件 {number(d.get('server_source_read_s'),3)} s",
                        f"读取及准备 {number(d.get('server_model_derive_s'),3)} s",
                        f"首刀 {number(d.get('server_first_cut_s'),3)} s"]
            ready_table.append(f"| {n} | {k} | {m} | {d.get('cold_first_count','—')}/5 | {d.get('switch_count','—')}/50 | {', '.join(parts)} |")

echo=result.get("websocket_validation") or []
echo_txt="，".join(f"{t['name']} {number(median(t['roundtripMs']),1)} ms" for t in echo)
check_list=[]
checked=0
for k in cases:
    stat=result["cases"][k]["browser_vtk_correctness"]
    for s in stat.get("planes",[]):
        if s["passed"]:checked+=1
        ref=s["references"]
        orig=ref["original"]
        check_list.append(f"- {k}, x={s['x']} m。源精度三角形偏差 {orig['triangle_error_percent']:.6g}%、面积偏差 {orig['area_error_percent']:.6g}%、"
                         f"最大匹配位移差 {orig['max_displacement_diff_m']:.4g} m，1 mm 双向未配到 {orig['unmatched_vtk_points']}/{orig['unmatched_browser_points']} 点，"
                         f"最大最近点距离 {orig['largest_nearest_position_gap_m']:.4g} m。传输精度参考双向缺配 {ref['transport_precision']['unmatched_vtk_points']}/{ref['transport_precision']['unmatched_browser_points']}。")
overview = f"""# Sim2Web r6 网页剖切验证

基线提交 `f2b4511`，结果分支 `r6/web-slicing`。r6 bundle SHA-256 `678253122390c7ce2ae0522164930b40f85a586c23282fb571768fcb9990ab59`。只执行公开算例 A、C。

## 环境与协议

Windows 11 10.0.26300，Intel i7-10750H，15.8 GiB RAM，Intel UHD / Quadro P620。Chrome 160.0.8157.0、Node 24.19.0、Playwright 1.49.1、Python 3.12.14、VTK 9.5.0、PyVista 0.46.3、NumPy 1.26.4、SciPy 1.11.4、vtk.js 32.14.0（B/W）、trame 4.0.0、trame-vtk 2.11.17、trame-vuetify 3.3.0、psutil 7.2.2、Matplotlib 3.11.2。trame 客户端包含 vue-vtk-js 3.3.5 和 vtk.js 36.0.0，安装后的脚本 SHA-256 与发布源码一致。ParaView 5.13.3 只核对版本，本次服务器直接用 VTK。版本命令见 `../logs/041_runtime_versions.log`、`../logs/042_versions_python.log`、`../logs/063_trame_client_verified.log`。 [trame-vtk 发布脚本](https://raw.githubusercontent.com/Kitware/trame-vtk/a000bddc61214b6977ebfe87a66cca60a804010c/.fetch_externals.sh)

B 收到整个公开体网格，包括顶点、连通关系、单元类型、节点三分量位移和保留单元掩码。按原配置掩码剔除空区，保证与 W 生成剖面的取材区域一致。Float32 坐标与位移，Int32 拓扑，gzip 6。页面发出 HTTP 请求，随后把缓冲区转移给 Worker。Worker 解析、建立 128 个 x 范围桶并裁切四面体、六面体、楔体和金字塔。A、C 显示字段是源节点位移的模长，计算后沿切边插值。该实验字段无需单元到节点平均。按配置标记的空区只影响切哪些单元，体网格传输仍包括它们。

S-local 通过 trame 发送 vtkCutter 的 vtkPolyData 几何，在浏览器用 vtk.js 绘制。S-remote 服务端以窗口原尺寸渲染并传输 JPEG。W 使用构建后的原版查看器和其公开基准 API，关闭预取和外表面可见性。原版启动仍请求主表面。W 首次逐位置的请求发生在 warm-up 扫描，五次重复保留程序正常 LRU。切换的报表分别给出首次扫过和暖缓存统计。

最初的截图显示 W 的裁剪范围遗漏部分远端剖面，且 trame 本地渲染的默认相机遗漏正交投影。W 的基准 HTTP 服务给索引附加一个不透明度为零的单三角面，固定相机裁剪范围。由此新增的 HTTP 请求和字节计入 W 指标，已构建的发布目录和查看器代码保持原样。trame 本地基准在相机序列化中补入正交投影属性。远程基准在 JPEG 角落加入 20 px 编号色块，测量仅接受解码后编号相符的图像。对这些模式的正式矩阵均重测。最终截图的共同裁剪区域按彩色剖面轮廓与 B 对齐，阈值为 IoU ≥ 0.97。

trame 2.11.17 的图像交付在编码仍待完成时按默认 500 ms 延迟再尝试。本次 S-remote 用时包含等待对应剖面 JPEG 到达的时间。浏览器总进程峰值还包括 JPEG 解码和显示过程。

Site 4G 设置为下行 20 Mbit/s、上行 5 Mbit/s、50 ms 延迟。WebSocket 回显实测 {echo_txt}。采用 CDP 本身。传输统计为首帧事件之前完成的 Chrome HTTP 压缩响应（CDP 编码字节）和 WebSocket 消息净负载收发合计。TCP、TLS、WebSocket 帧开销未加进数值。每 100 ms 读取主渲染目标 JSHeapUsedSize 和由试验启动的全部 Chrome 子进程 RSS。Worker 的内存反映在进程 RSS。S 的服务进程使用 Windows 进程峰值 working set。CPU 差值从 50 次切换前后各读取一次。

## 正确性门槛

共 {checked}/6 个核对平面通过。阈值为三角形 ±1%，面积 0.1%，匹配位移模长差 <1e-6 m。C 的源网格与 Float32 传输精度各自保留了一套独立 VTK 参考。C 的源精度在近似平行切边上的少量点超过 1 mm 匹配容差，表中的最大匹配位移差取在容差内的点。相同 Float32 传输精度下逐点双向 1 mm 匹配全部通过。

"""+"\n".join(check_list)+"""

S 的 warm-up 三个位置与独立参考导出的坐标、位移数组、三角形连通性逐项比较，结果在 `results.json` 的 `server_matches_vtk`。W 的 A/C 独立验证摘要随证据提供。

## 公平性检查

"""+"\n".join(checks)+"""

## 准备与分项时长

"""+"\n".join(ready_table)+"""

LAN 和 Site 4G 的完整表格见 `table6.md`。每次首帧与 50 次切换原始数据见 `results.json`。

## 已遇到的问题

旧图 1 的 r5 LFS 远端对象返回 404，使用跳过 LFS 下载完成基线更新。图 1 从任务给出的内容与版式重新绘制。Drive 连接器首次不可用，浏览器预览提供了任务说明。连接器恢复后下载了原始 Markdown 并核对，规范化空白后两份正文一致。

早期 Worker 内的 HTTP 请求未进入页面目标的 CDP 传输计数。最终版本在页面发起下载，再转移缓冲区给 Worker，重新做正确性核对和整套测试。C 的第一版近邻匹配混用了坐标和位移权重，最终校验先按位置容差选择候选，再比对匹配位移。S-remote 的第一版监测画布绘制，随后改用图像载入，最后加上帧编号核对。旧测试命令和失败记录随报告保留，表 6 使用校正后的测量。trame 启动期间 Chrome 报出一个 HTTP 405 资源错误，实际剖面数据和图像通道仍完成了交付。

"""
errors=[f"- {ident}, {issue['run']}：{issue['error']}" for ident,r in result["matrix"].items() for issue in r["metrics"]["errors"]]
if errors:overview+="正式矩阵的错误记录。\n\n"+"\n".join(errors)+"\n"
summary=[]
if all(f"{k}_{m}_{n}" in result["matrix"] for k in cases for m in methods for n in networks):
    summary=[
       f"算例 A 的浏览器端剖切在 4G 下 {g('A','B','4G','cold_first_count')}/5 次冷启动显示首帧，首帧用时中位数 {number(g('A','B','4G','first_seconds'),3)} s，完整体网格 gzip 载荷 {mb(result['cases']['A']['metadata']['gzip_bytes'])} MB。",
       f"4G 下 A 的 trame 几何和图像交付首帧中位数分别为 {number(g('A','S-local','4G','first_seconds'),3)} s 和 {number(g('A','S-remote','4G','first_seconds'),3)} s，两种交付方式均需运行 VTK 服务。",
       f"4G 下 A 的 Sim2Web 首帧总传输 {mb(g('A','W','4G','first_bytes'))} MB，重复切换中位数 {number((g('A','W','4G','switch_median_p95_ms') or [None])[0],1)} ms，重复轮次可复用内存里的 VTP。",
       f"在 LAN 上，算例 A 的浏览器端剖切和 Sim2Web 重复切换中位数分别为 {number((g('A','B','LAN','switch_median_p95_ms') or [None])[0],1)} ms 和 {number((g('A','W','LAN','switch_median_p95_ms') or [None])[0],1)} ms，本次 trame 远程图像模式等待对应图像到达的中位数为 {number((g('A','S-remote','LAN','switch_median_p95_ms') or [None])[0],1)} ms。",
       "浏览器端和服务端剖切支持任意位置，Sim2Web 的剖面位置在构建时固定，发布后若要加入新位置就需要重新构建。"
    ]
overview+="\n## 结论\n\n"+"\n\n".join(summary)+"\n"
md(dest/"REPORT.md",overview)

total_cold = sum(r["metrics"]["cold_ok_count"] for r in result["matrix"].values())
total_switches = sum(r["metrics"]["switch_count"] for r in result["matrix"].values())
brief=("# Sim2Web r6 验证交付\n\n"
       f"在同一台 Windows 工作站测量公开算例 A、C 的浏览器端剖切、trame 几何和图像交付、Sim2Web 构建时剖面。"
       f"LAN 和模拟 Site 4G 共 {len(result['matrix'])} 组，完成 {total_cold} 次冷启动和 {total_switches} 次计时切换。"
       f"浏览器端与 vtkCutter 对照的剖面通过 {checked}/6。\n\n"+"\n\n".join(summary)+"\n\n")
brief+="## 表 6\n\n"+"\n".join(table[2:])+"\n\n## 公平性\n\n"+"\n".join(checks)+"\n\n"
brief+="## 异常和补测\n\n旧图 LFS 对象下载返回 404。Worker 请求计数修正后重新执行了浏览器端正确性和正式测试。截图发现 Sim2Web 裁剪范围和 trame 本地相机投影存在差异，两种基准的相机校正后重新测量。远程 trame 用编号色块核对 JPEG，剔除上一张剖面的延迟帧。算例 C 的 Float32 传输导致少量原始坐标顶点无法在 1 mm 容差内匹配，按传输精度重切参考后双向全部匹配。所有试验退出码与日志位置见 COMMANDS.csv，详见 `web_slicing/REPORT.md`。\n\n"
brief+="## 图 1\n\n`figures/fig1_architecture.svg`、`figures/fig1_architecture.pdf`、`figures/fig1_architecture.png`（600 dpi）和可编辑的 `figures/draw_figure1.py`。最终印刷尺寸 16.5 × 7.0 cm，最小字号 8.1 pt。\n"
md(ev/"REPORT.md",brief)

if a.complete:
    (dest/"captures/.gitattributes").write_text("*.png -filter -diff -merge -text\n",encoding="utf-8")
    (ev/"logs").mkdir(exist_ok=True)
    rows=[read(f) for f in sorted((w/"logs").glob("*.json"))]
    names=["id","command","cwd","started_at","duration_seconds","exit_code","log"]
    for row in rows:
        if (w/row["log"]).is_file():
            shutil.copyfile(w/row["log"],ev/row["log"])
    with (ev/"COMMANDS.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,names)
        writer.writeheader()
        writer.writerows([{k:r.get(k) for k in names} for r in rows])
    for k in cases:
        assert result["cases"][k]["browser_vtk_correctness"]["passed"],k
        assert not result["cases"][k]["sim2web_validation"]["failures"],k
    assert len(result["matrix"])==16
    assert result["frame_check"]["passed"]
    for ident, entry in result["matrix"].items():
        m = entry["metrics"]
        trial = entry["trial"]
        assert m["cold_attempts"] == m["cold_first_count"] == m["cold_ok_count"] == 5, (ident, m["errors"])
        assert m["switch_count"] == 50, (ident, m["switch_count"])
        if trial["method"].startswith("S-"):
            agreement = m["server_matches_vtk"]
            assert len(agreement) == 3 and all(all(row.values()) for row in agreement.values()), ident
        if trial["method"] == "S-remote":
            assert all(s["target"] == s["timing"]["paint"]["section"] for s in trial["switches"]), ident
        if trial["method"] == "S-local":
            triangles = {e["index"]: e["triangles"] for e in trial["server"]["allEvents"] if e["phase"] == "switch"}
            assert all(3 * triangles[s["target"]] == s["timing"]["paint"]["count"] for s in trial["switches"]), ident
    print("Collected",len(rows),"recorded commands")
print("Collected",len(result["matrix"]),"case-method-network entries")
