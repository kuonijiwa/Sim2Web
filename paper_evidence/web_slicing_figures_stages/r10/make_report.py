import csv
import json
import math
import sys
from pathlib import Path

run = Path(sys.argv[1])
delivery = run / "delivery"
figures = json.loads((delivery / "print_check.json").read_text(encoding="utf-8"))["figures"]
records = [
    json.loads(file.read_text(encoding="utf-8-sig"))
    for file in (run / "logs").glob("r10_*.json")
]
records.sort(key=lambda record: record["started_at"])
with (delivery / "COMMANDS.csv").open("w", encoding="utf-8-sig", newline="") as output:
    writer = csv.DictWriter(output, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)


def angle(values):
    position, focal = values[:3], values[3:6]
    x, y, z = (a - b for a, b in zip(position, focal))
    return f"方位 {math.degrees(math.atan2(y, x)) % 360:.1f}°，俯视 {math.degrees(math.atan2(z, math.hypot(x, y))):.1f}°"


def limits(values):
    return f"[{values[0]:.10g}, {values[1]:.10g}]"


def style(title, rules):
    fence = "\x60" * 3
    return f"**{title}**\n\n{fence}css\n{rules}\n{fence}"


fig2 = figures["2"]["panels"]["b"]
fig3 = figures["3"]["panels"]["window"]
fig6 = figures["6"]
a = figures["7"]["panels"]["I-1"]
lines = [
    "# Sim2Web 论文插图 r10",
    "",
    "2026-11-22，Windows 工作站。依据 CODEX_TASK_r10_figures.md 制作。"
    "浏览器核对索引在本次开始时已指向 A、C、D。逐条统计 r4 原始记录得到 A 180、C 180、D 270，共 630 次成功。"
    "对应记录位于 paper_evidence/comparison_paraview_glance/windows_r4/cases/ 各算例的 sim2web_browser.json。",
    "",
    "## 图 1 · 处理与发布流程",
    "",
    "沿用批准的工作流图。图示输入、Sim2Web 构建、可发布静态包和独立验证之间的关系。"
    "原矢量 PDF 使用 Liberation Sans，正文 8 pt，标题 9 pt。PNG 转存为 RGB 并保留 600 dpi。",
    "",
    "## 图 2 · 算例 D 工作台与发布结果",
    "",
    "(a) 工作台第 3 步“几何与开挖”的步骤栏与诊断栏。(b) 算例 D 的发布查看器，"
    f"外表面不透明度 35%，开挖面 100%，位移模量 |u| {limits(fig2['legend']['range'])} m，"
    f"Viridis 8 色带，{angle(fig2['camera'])}。"
    "按 r10 说明保留 r9 批准版，SHA-256 完全一致，诊断正文约 5.00 pt，色标刻度 5.97 pt。"
    "沿用的图 2 指标和图注说明见 ../r9/print_check.json 及 ../r9/REPORT_fig2.md。",
    "",
    "## 图 3 · 完整的五施工步网页查看器",
    "",
    "Chrome 1440 × 900 CSS px，deviceScaleFactor 3。算例 A 的 IV-2 施工步，"
    f"最小主应力 σ3 {limits(fig3['legend']['range'])} MPa，Jet 8 色带，{angle(fig3['camera'])}。"
    "开挖图层可见，不透明度 35%。X = 38 m，滑块显示第 33/77 个切面。"
    "实际点选剖面，读数为 Source_Cell_ID 1160199，最小主应力 −6.857 MPa。"
    "原生控件与图例字号实测为 3.41–4.06 pt，低于约 5 pt。编号在合成图中绘制，字号 9 pt 粗体。",
    "",
    "1. 施工步选择框（IV-2）。",
    "2. 物理量选择框（最小主应力）。",
    "3. 图层列表（开挖面）。",
    "4. X 剖面轴选择和位置滑块。",
    "5. 点选读数与 Source_Cell_ID。",
    "6. 色标。",
    "",
    "## 图 4 · A–F 发布结果",
    "",
    "各分图均为平行投影，Jet 8 色带。下表保留供复核的实际色限，图中刻度至多三位有效数字。"
    "B、E 的包以 Pa 记录，合成色标时将标签换算为 MPa。颜色、断点及源应力数组沿用各自发布包。"
    "A 的原生点选也核对到 Source_Cell_ID 1160199，σ3 = −6.857 MPa，读数排在分图下方。",
    "",
    "| 算例 | 字段 | 显示色限 | 剖面 | 方位 / 俯视 / 滚转 |",
    "|---|---|---|---|---|",
]
for case, panel in figures["4"]["panels"].items():
    legend, settings = panel["legend"], panel["settings"]
    section = f"{settings['axis'].upper()} = {settings['pos']} m" if settings["section"] == "1" else "无"
    rotation = " / ".join(f"{value}°" for value in panel["angles_deg"])
    lines.append(f"| {case} | {legend['title'].replace('|', '&#124;')} | {limits(legend['range'])} {legend['unit']} | {section} | {rotation} |")

lines.extend([
    "",
    "## 图 5 · 算例 A 主应力对比",
    "",
    "取 IV-2 的 983,438 个非零应力单元。横轴为依据分量名排列计算的主应力，"
    "纵轴为直接交给 vtkTensorPrincipalInvariants 的对应结果，单位均为 MPa。"
    "文件分量序为 XX、YY、ZZ、XY、XZ、YZ。公共色标为每个六边形单元 1–291,332 个样本，采用对数映射。",
    "",
    "| 分图 | 主应力 | 最大绝对误差（MPa） | 占参考范围 | 只在通用结果中受拉的单元 |",
    "|---|---|---:|---:|---:|",
])
for label, panel in figures["5"]["panels"].items():
    lines.append(
        f"| ({label}) | {panel['label']} | {panel['maximum_error_MPa']:.5f} | "
        f"{panel['pct_range']:.3f}% | {panel['tensile_only_generic']:,} |"
    )

lines.extend([
    "",
    "## 图 6 · 算例 C 去除内部面前后",
    "",
    f"PyVista 0.46.3 渲染，平行投影，{angle(fig6['render']['camera'][0] + fig6['render']['camera'][1])}，"
    "平行尺度 411 m。两图保留 Y ≥ 375 m 的部分以露出内部结构，面不透明度均为 62%，"
    f"使用同样的细深色网格边。共享位移模量色限 {limits(fig6['panels']['a']['legend']['range'])} m，Jet 8 色带。"
    "截切用于展示，图中面数和大小对应 r4 整张表面文件。",
    "",
    "| 分图 | 表面 | 面数 | 字节数 | 图中文字 |",
    "|---|---|---:|---:|---|",
    "| (a) | ParaView Extract Surface | 917,062 | 187,591,097 | 917,062 faces · 187.6 MB |",
    "| (b) | Sim2Web 去除内部接触面 | 21,293 | 2,620,417 | 21,293 faces · 2.6 MB |",
    "",
    "数据来自 paper_evidence/comparison_paraview_glance/windows_r4/comparison_results.json 的算例 C 对照记录。"
    "实际渲染使用 r4 留存的 C/surface.vtp 和 slopemodel/exterior_surface.vtp，文件大小与记录相符。",
    "",
    "## 图 7 · 算例 A 的施工步",
    "",
    f"依次为 I-1、II-2、IV-2。仅显示开挖面，{angle(a['camera'])}，三图相机一致。"
    f"最小主应力 σ3 {limits(a['legend']['range'])} MPa，取全部五个施工步开挖面数据合并后的 P5–P95，"
    "共享 Jet 8 色带。",
    "",
    "## 截图 CSS",
    "",
    "图 3 使用原生界面，未注入 CSS。图 4、7 注入同一条规则，用合成图绘制色标。图 6 由 PyVista 渲染。",
    "",
    style("图 4、7", figures["4"]["injected_css"]),
    "",
    "图 2 左栏原始截图没有 CSS 注入。右栏继承 r9 已批准图片中的规则。",
    "",
    style("图 2 右栏（r9）", figures["2"]["panel_right_css"]),
    "",
    "## 印刷核验",
    "",
    "各图宽 16.5 cm，PNG 为 RGB，写入 600 dpi。原生界面字体按实测报告。"
    "合成图使用 Arial 或 Liberation Sans，外置分图标签 9 pt 粗体、色标标题 7.5–8 pt、"
    "刻度 7 pt、轴标题 8 pt、标注 7.5 pt。图 1、5 另附矢量 PDF。"
    "有效分辨率、相机参数、原始色限和 SHA-256 见 print_check.json。",
    "",
    "| 图 | PNG 尺寸（px） | 最小分图有效 dpi | 最小文字（pt） | 文件大小（MB） |",
    "|---|---|---:|---:|---:|",
])
for number, figure in figures.items():
    width, height = figure["pixels"]
    dpi = min(panel["effective_dpi"] for panel in figure["panels"].values())
    lines.append(
        f"| {number} | {width} × {height} | {dpi:.1f} | "
        f"{figure['smallest_nominal_text_pt']:.2f} | {figure['bytes'] / 1e6:.3f} |"
    )

lines.extend([
    "",
    "## 命令、退出码与耗时",
    "",
    "COMMANDS.csv 提供工作目录、开始时间和本地日志名称。"
    "图 4 最初两次定位未命中探针，改用保存的相机投影定位后通过。"
    "图 6 首次渲染遇到 PyVista 的 Plotter 上下文管理器兼容问题，调整关闭方式后重新渲染。"
    "图 5 初稿报告 Arial 缺少 Unicode 下标字形，终稿用基线数字重新导出。",
    "",
    "复现截图时，capture_viewers.mjs 读取 view_states.json 和 stage_states.json。"
    "view_states.json 的站点路径相对于仓库根目录，需先用 examples 下的配置构建相应站点。"
    "图 6 渲染脚本读取上述两份 r4 表面文件。图 1 另附原始绘图脚本。",
    "",
    "| 步骤 | 命令 | 退出码 | 耗时（s） |",
    "|---|---|---:|---:|",
])
for record in records:
    command = record["command"].replace("|", "&#124;").replace("\n", " ")
    lines.append(f"| {record['id']} | \x60{command}\x60 | {record['exit_code']} | {record['duration_seconds']:.3f} |")

(delivery / "REPORT_r10.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
