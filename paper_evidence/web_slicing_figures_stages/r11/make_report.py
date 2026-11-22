"""Write the Chinese caption notes and copy the command ledger from the run logs."""
import csv
import hashlib
import json
import sys
from pathlib import Path


run = Path(sys.argv[1])
output = run / "delivery"
figures = json.loads((output/"print_check.json").read_text(encoding="utf-8"))["figures"]
records = [json.loads(path.read_text(encoding="utf-8-sig")) for path in (run/"logs").glob("r11_*.json")]
records.sort(key=lambda item: item["started_at"])
with (output/"COMMANDS.csv").open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=list(records[0]))
    writer.writeheader()
    writer.writerows(records)


def sha(file):
    return hashlib.sha256((run / file).read_bytes()).hexdigest()


def scale(legend):
    lo, hi = legend["range"]
    return f"[{lo:.10g}, {hi:.10g}] {legend['unit']}"


def angles(panel):
    return " / ".join(f"{v:g}°" for v in panel["angles_deg"])


def layers(panel):
    names = {"layer:exterior": "外表面", "layer:excavation": "开挖面", "section": "剖面"}
    return "、".join(f"{names[k]} {v['opacity']:.0%}（{v['color']}）" for k,v in panel["geometry"].items())


fig2, fig3, fig4, fig5, fig6, fig7 = (figures[str(i)] for i in range(2,8))
workbench = fig2["panels"]
right = workbench["b"]
build = fig2["build"]
validation = fig2["validation"]["stages"]["EXC12_dis"]
probe = fig3["probe"]
min_stress = next(row["text"] for row in probe["rows"] if row["name"] == "Stress_Min_Principal")
window = fig3["panels"]["window"]
render = fig6["render"]
stage = fig7["panels"]["I-1"]
fence = chr(96)*3
lines = [
    "# Sim2Web 论文插图 r11",
    "",
    "2026-11-23，Windows 工作站。按稿件文件夹中的任务说明和版式草图重做图 2–7，图 1 沿用现有版本。",
    "已在实际发布查看器的 Colour map 下拉列表中核对 Turbo，并在截图中检查当前色谱为 Turbo、色带数为 8。"
    "因此无需添加色谱预设，本次提交集中在论文证据目录。",
    "",
    "| 下载的输入 | SHA-256 |",
    "|---|---|",
    f"| CODEX_TASK_r11_figure_redesign.md | {sha('CODEX_TASK_r11_figure_redesign.md')} |",
    f"| figure_wireframes.png | {sha('figure_wireframes.png')} |",
    "",
    "## 图 2 · 算例 D 工作台与发布结果",
    "",
    f"(a) EXC12_dis 的工作台六个步骤和通过验证后的诊断栏。第 3 步“Geometry and excavation”为当前步骤。"
    f"六步名义印刷字号 {workbench['a_steps']['font_pt']:.2f} pt，诊断正文 {workbench['a_diagnostics']['font_pt']:.2f} pt。",
    "",
    "| 诊断 | 截图中的文字 |",
    "|---|---|",
]
for row in fig2["diagnostics"]:
    lines.append(f"| {row['title']} | {row['value']} |")
lines.extend([
    "",
    f"(b) 同一构建的 EXC12_dis，位移模量 |u| 的 P5–P95 为 {scale(right['legend'])}，"
    f"Turbo 8 档，方位 / 俯视 / 滚转 {angles(right)}，平行投影，无剖面。{layers(right)}。"
    f"灰色地表取自原始外表面在 z = {right['ground_z_m']} m 的 {right['geometry']['layer:exterior']['cells']:,} 个面。"
    f"Sim2Web {build['sim2web']} 的原构建耗时 {build['seconds_total']:.2f} s。"
    f"独立验证检查 {validation['files']} 个产品，精确值不符 {validation['exact_mismatches']}，验证通过。",
    "",
    "## 图 3 · 算例 A 完整发布查看器",
    "",
    f"五施工步包的 IV-2。{fig3['viewport']['width']} × {fig3['viewport']['height']} CSS px，"
    f"deviceScaleFactor {fig3['dsf']}。保留 16:9 完整窗口、应用控件和原生图例，无编号标注。"
    "左栏从上到下显示施工步、物理量、图层和剖面控制，右栏显示点选详情及色标。",
    f"平行投影，方位 / 俯视 / 滚转 {angles(window)}。{layers(window)}。"
    f"最小主应力 σ3 的 P5–P95 为 {scale(window['legend'])}，Turbo 8 档。"
    f"剖面滑块显示 {fig3['section_slider']}。实际点选剖面得到 Source_Cell_ID {probe['sourceCell']}、σ3 = {min_stress}。"
    f"关闭渲染器的光照着色以显示完整色带，按截图中的几何投影框取景。"
    f"界面字体沿用应用样式，名义印刷字号 {min(fig3['native_font_pt']):.2f}–{max(fig3['native_font_pt']):.2f} pt，"
    "色标也保留应用原有的边界刻度。",
    "",
    "## 图 4 · A–F 发布结果",
    "",
    "三行两列。均为平行投影，Turbo 8 档，短标题和三刻度。"
    "B、E 的值按原包的 Pa 渲染，合成色标换算为 MPa。D 提高俯视角展示开挖内部，"
    "灰色上下文是原始外表面 z = 11 m 的地表多边形。C 显示外表面。A 的探针读数集中在图 3。",
    "",
    "| 算例 | 字段 | 色标实际范围 | 剖面 | 方位 / 俯视 / 滚转 | 图层与不透明度 |",
    "|---|---|---|---|---|---|",
])
for key, panel in fig4["panels"].items():
    settings = panel["settings"]
    slice_label = f"{settings['axis'].upper()} = {settings['pos']} m" if settings["section"]=="1" else "无"
    title = panel["legend"]["title"].replace("|","&#124;")
    lines.append(f"| {key} | {title} | {scale(panel['legend'])} | {slice_label} | {angles(panel)} | {layers(panel)} |")

lines.extend([
    "",
    "## 图 5 · 算例 A 主应力核对",
    "",
    f"使用 IV-2 的 {fig5['comparison']['kept_cells']:,} 个非零应力单元重新计算。"
    "横轴是按 XX、YY、ZZ、XY、XZ、YZ 分量顺序计算的参考主应力，纵轴是通用 VTK 过滤器所得主应力，均为 MPa。"
    "方形坐标轴、虚线表示 1∶1，浅色区表示通用结果大于零。"
    f"公共 Turbo 对数色标从 1 到 {fig5['comparison']['bin_colour_range'][1]:,} 个样本/六边形，"
    "三处刻度采用最小值、几何中值和最大值。轴标题 8 pt，刻度和误差框 7 pt。",
    "",
    "| 主应力 | 共同绘图范围（MPa） | 最大绝对误差（MPa） | 占参考范围 | 只在通用结果中受拉的单元 |",
    "|---|---|---:|---:|---:|",
])
for panel in fig5["panels"].values():
    lo, hi = panel["stress_range_MPa"]
    lines.append(f"| {panel['label']} | [{lo:.6g}, {hi:.6g}] | {panel['maximum_error_MPa']:.5f} | "
                 f"{panel['pct_range']:.3f}% | {panel['tensile_only_generic']:,} |")

full_a, full_b = fig6["panels"]["a_full"], fig6["panels"]["b_full"]
factor = full_a["faces"]/full_b["faces"]
lines.extend([
    "",
    "## 图 6 · 算例 C 内部面去除",
    "",
    f"上排两个不透明全模型由 {render['renderer']} 渲染，平行投影，方位 / 俯视 / 滚转 "
    + " / ".join(f"{v:g}°" for v in render["view_angles_deg"]) + "，相机、范围和配色完全相同。"
    f"位移模量 |u| 的 P5–P95 为 {scale(full_a['legend'])}，使用 Matplotlib Turbo 均匀采样 8 色带。"
    f"使用 r4 记录及留存表面文件，(a) {full_a['faces']:,} 面、{full_a['bytes']:,} B（187.6 MB），"
    f"(b) {full_b['faces']:,} 面、{full_b['bytes']:,} B（2.6 MB），相差 {factor:.2f} 倍。"
    f"红框覆盖相同的投影视域，下排在同方向放大 {render['parallel_scale']/render['detail_parallel_scale']:.2f} 倍，"
    f"仅绘制深灰色线框（#45494D，0.7 线宽，{render['detail_style']['opacity']:.0%} 不透明度）。"
    "左边为保留的内部接触面和外部边线，右边为去除后外部边线。"
    f"上排渲染图的非背景像素中，最大通道差不超过 20/255 的占 {render['opaque_fraction_pixels_within_20_rgb']:.5%}。"
    "该比较在叠加红框前进行。面数和文件大小见 comparison_paraview_glance/windows_r4/comparison_results.json。",
    "",
    "## 图 7 · 算例 A 施工步",
    "",
    f"箭头串联 I-1、II-2、IV-2，只显示不透明开挖面。面数分别为 "
    + " / ".join(f"{panel['faces']:,}" for panel in fig7["panels"].values())
    + f"。共用平行投影相机和裁切框，方位 / 俯视 / 滚转 {angles(stage)}，无剖面。"
    f"最小主应力 σ3 使用五施工步开挖面合并后的 P5–P95 {scale(stage['legend'])}，Turbo 8 档。",
    "",
    "## 截图样式和取景设置",
    "",
    "图 2 的工作台沿用原字体和措辞，截图时调整纵向内边距和最小行高。规则如下。",
    "",
    f"{fence}css",
    fig2["css"][0],
    fence,
    "",
    "图 2(b)、4 和 7 隐藏查看器控制栏与原生色标，在合成图上绘制色标。规则如下。",
    "",
    f"{fence}css",
    fig2["css"][1],
    fence,
    "",
    "图 3 无 CSS 注入。截图服务器仅在本地运行时关闭方向标，在截图实例内同步关闭模型光照，"
    "保留原生界面和真实点选事件。透明背景图层设置为 #D9D9D9、20%。"
    "D 的灰色地表取自构建产品中的地表面，源文件和发布产品未改写。图 5、6 分别通过 Matplotlib、PyVista 绘制。",
    "",
    "## 印刷规格和运行记录",
    "",
    "所有 PNG 为 16.5 cm 宽、RGB、600 dpi。图 5 PDF 也是 16.5 cm 宽，字体为 Arial，核对无嵌入栅格图。",
    "逐图有效 DPI、单位、色限、带数、相机参数和 SHA-256 见 print_check.json。",
    "",
    "| 图 | 尺寸（cm） | 最小有效 DPI | 最小文字（pt） | PNG（MB） |",
    "|---|---|---:|---:|---:|",
])
for number, figure in figures.items():
    dpi = min(p["effective_dpi"] for p in figure["panels"].values())
    lines.append(f"| {number} | 16.50 × {figure['height_cm']:.2f} | {dpi:.1f} | "
                 f"{figure['minimum_text_pt']:.2f} | {figure['bytes']/1e6:.3f} |")

lines.extend([
    "",
    "COMMANDS.csv 记录制作命令、退出码、耗时及日志。首次图 2 截图向 Playwright 传入了 URL 对象，"
    "改为实际 URL 字符串后通过。首次图 5 命令的 PowerShell 参数与自动变量重名，修正后成功。",
    "",
    "| 步骤 | 命令 | 退出码 | 耗时（秒） |",
    "|---|---|---:|---:|",
])
for row in records:
    cmd = row["command"].replace("|","&#124;").replace("\n"," ")
    lines.append(f"| {row['id']} | \x60{cmd}\x60 | {row['exit_code']} | {row['duration_seconds']:.3f} |")

(output/"REPORT_r11.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
