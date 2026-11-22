"""Make the 16.5 cm print masters and check the actual browser captures."""
import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if libs := os.environ.get("SIM2WEB_R7_PDF_LIB"):
    sys.path.append(libs)

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


DPI = 600
PP_CM = 72 / 2.54
PX_CM = DPI / 2.54
FIGURE_WIDTH = 16.5
GAP = 0.2
LABEL_BAND = 12.2 / PP_CM
FONTFILE = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/arialbd.ttf"
pdfmetrics.registerFont(TTFont("FigureLabel", str(FONTFILE)))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rgb(path):
    with Image.open(path) as source:
        return source.convert("RGB")


def model_width(image, letter, record):
    # The left frame contains the scene. The legend and the non-scene probe
    # card have separate reserved rectangles in the original capture.
    dsf = record["deviceScaleFactor"]
    right = math.floor(record["legend"]["x"] * dsf)
    top = math.ceil((record['probe']['card']['y'] + record['probe']['card']['height'] + 1) * dsf) if letter == "a" else 0
    scene = np.asarray(image)[top:, :right]
    mask = (scene.min(axis=2) < 247) & (scene.max(axis=2) - scene.min(axis=2) > 3)
    columns = np.flatnonzero(np.count_nonzero(mask, axis=0) >= dsf)
    assert columns.size, letter
    width = int(columns[-1] - columns[0] + 1)
    return width / image.width, [int(columns[0]), int(columns[-1])]


def trim_bottom_margin(image, scale):
    """Crop near-white rows below the scene, keeping a small print margin."""
    pixels = np.asarray(image)
    # Ignore the near-white app background visible below the embedded viewer.
    occupied = np.flatnonzero((pixels.min(axis=2) < 242).any(axis=1))
    bottom = min(image.height, int(occupied[-1]) + 1 + 4 * scale)
    return image.crop((0, 0, image.width, bottom))


def geometry(capture_dir, fig, records, trim_workbench=False):
    width = FIGURE_WIDTH if fig == 2 else 8.1
    names = "ab" if fig == 2 else "abcdef"
    panels = []
    for letter in names:
        raw = rgb(capture_dir / f"fig{fig}_{letter}.png")
        info = records[letter] if fig == 2 else records[letter.upper()]
        dsf = info["deviceScaleFactor"]
        captured_size = raw.size
        if trim_workbench and fig == 2 and letter == "b":
            raw = trim_bottom_margin(raw, dsf)
        css_width = (info.get("clip") or info["viewport"])["width"]
        assert raw.width == css_width * dsf, (fig, letter, raw.width)
        dpi = raw.width * 2.54 / width
        assert dpi >= DPI, (fig, letter, dpi)
        meaningful = [t for t in info["text"] if fig == 2 or t["role"].startswith("legend_")]
        glyph_pt = width * PP_CM / css_width
        min_ink_px = min(t["inkHeightCssPx"] for t in meaningful)
        min_pt = min_ink_px * glyph_pt
        assert min_pt >= (5 if fig == 2 else 6), (fig, letter, min_pt)
        metadata = {
            "print_width_cm": width, "print_height_cm": width * raw.height / raw.width,
            "capture_px": list(captured_size), "css_viewport_width_px": css_width,
            "device_scale_factor": dsf, "effective_dpi": dpi,
            "smallest_meaningful_glyph_height_pt": min_pt,
            "measurement": "Chrome Canvas actualBoundingBoxAscent + actualBoundingBoxDescent, per visible line, scaled to panel print width",
            "ink_height_css_px_by_role": {role: min(t["inkHeightCssPx"] for t in meaningful if t["role"] == role)
                                           for role in sorted({t["role"] for t in meaningful})},
            "injected_css": info["injectedCss"],
        }
        if fig == 2 and info.get("embeddedCss"):
            metadata["embedded_viewer_css"] = info["embeddedCss"]
        if trim_workbench and fig == 2 and letter == "b":
            metadata["cropped_bottom_px"] = captured_size[1] - raw.height
            metadata["build_string"] = info["buildString"]
        if fig == 4:
            coverage, pixels = model_width(raw, letter, info)
            assert coverage >= 0.70, (letter, coverage)
            metadata.update(model_width_fraction=coverage, model_extent_capture_x_px=pixels)
        panels.append((letter, raw, metadata))
    return panels


def positions(num, panels):
    if num == 2:
        top = 0
        places = []
        for letter, panel, info in panels:
            places.append((0, top, letter, panel, info))
            top += LABEL_BAND + info["print_height_cm"] + GAP
        return places, top-GAP
    w = panels[0][2]["print_width_cm"]
    h = panels[0][2]["print_height_cm"]
    left = (FIGURE_WIDTH-2*w-GAP)/2
    return [(left+(w+GAP)*(i%2), (LABEL_BAND+h+GAP)*(i//2), *panel)
            for i,panel in enumerate(panels)], 3*(LABEL_BAND+h)+2*GAP


def print_pdf(pdf, places, figure_h, left=0, bottom=0):
    pdf.setFont("FigureLabel", 9)
    pdf.setFillColorRGB(0.11, 0.15, 0.19)
    for x,y,letter,im,info in places:
        label_base = figure_h-y-LABEL_BAND+1.7/PP_CM
        pdf.drawString(left+x*PP_CM, bottom+label_base*PP_CM, f"({letter})")
        h = info["print_height_cm"]
        w = info["print_width_cm"]
        pdf.drawImage(ImageReader(im), left+x*PP_CM, bottom+(figure_h-y-LABEL_BAND-h)*PP_CM,
                      width=w*PP_CM, height=h*PP_CM, mask=None)


def write_composite(out, name, places, height):
    # The PDF is the exact physical size. The 600 dpi raster rounds to the next whole pixel.
    dims = (math.ceil(FIGURE_WIDTH*PX_CM), math.ceil(height*PX_CM))
    rgb_out = Image.new("RGB", dims, "white")
    drawing = ImageDraw.Draw(rgb_out)
    font = ImageFont.truetype(str(FONTFILE), round(9/72*DPI))
    for x,y,letter,im,info in places:
        label_base = (y+LABEL_BAND-1.7/PP_CM)*PX_CM
        draw_x = round(x*PX_CM)
        drawing.text((draw_x, round(label_base)), f"({letter})", font=font, fill="#1c2630", anchor="ls")
        draw_y = round((y+LABEL_BAND)*PX_CM)
        end_x = math.ceil((x+info["print_width_cm"])*PX_CM)
        end_y = math.ceil((y+LABEL_BAND+info["print_height_cm"])*PX_CM)
        rgb_out.paste(im.resize((end_x-draw_x, end_y-draw_y), Image.Resampling.LANCZOS), (draw_x, draw_y))
    rgb_out.save(out/f"{name}.tif", compression="tiff_lzw", dpi=(DPI,DPI))
    rgb_out.save(out/f"{name}.png", dpi=(DPI,DPI), optimize=True)
    pdf = canvas.Canvas(str(out/f"{name}.pdf"), pagesize=(FIGURE_WIDTH*PP_CM, height*PP_CM), pageCompression=1)
    print_pdf(pdf, places, height)
    pdf.save()
    page = PdfReader(out/f"{name}.pdf").pages[0]
    assert abs(float(page.mediabox.width)/PP_CM-FIGURE_WIDTH) < 0.00001
    assert abs(float(page.mediabox.height)/PP_CM-height) < 0.00001
    assert all(f"({letter})" in page.extract_text() for _,_,letter,_,_ in places)
    with Image.open(out/f"{name}.tif") as tif:
        assert tif.mode == "RGB" and tif.tag_v2[259] == 5 and tif.info["dpi"] == (DPI,DPI)
        assert tif.size == dims
    with Image.open(out/f"{name}.png") as png:
        assert png.mode == "RGB" and png.size == dims and abs(png.info["dpi"][0]-DPI) < 0.01
    return dims


def contact_sheets(out, specs):
    pdf = canvas.Canvas(str(out/"contact_sheets_100pct.pdf"), pagesize=A4, pageCompression=1)
    pdf.setTitle("Figures 2 and 4 at 100% print size")
    for fig, places, height in specs:
        left = (A4[0]-FIGURE_WIDTH*PP_CM)/2
        top = A4[1]-3.0*PP_CM
        pdf.setFont("FigureLabel", 12)
        pdf.drawString(left, top+1.0*PP_CM, f"Figure {fig} at 100%")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(left, top+0.5*PP_CM, "Print at actual size. Figure width 165 mm.")
        print_pdf(pdf, places, height, left=left, bottom=top-height*PP_CM)
        pdf.showPage()
    pdf.save()
    assert len(PdfReader(out/"contact_sheets_100pct.pdf").pages) == 2


def report(out, summary, probe):
    lines = ["# Sim2Web r7 印刷截图", "", "在 Windows Chrome 中重截图 2 和图 4。图 2 上下排两张，图 4 按 A–F 两列三行。",
             "原尺寸校样在 `contact_sheets_100pct.pdf`，按 100% 打印。两张主图以 16.5 cm 宽交付。",
             "", "## 印刷核验", "", "| 图 | 高度（cm） | 分图 | 截图倍数 | 分图有效 dpi | 最小有效字高（pt） |",
             "|---|---:|---|---:|---:|---:|"]
    for fig, entry in summary.items():
        for letter, panel in entry["panels"].items():
            lines.append(f"| {fig} | {entry['height_cm']:.3f} | ({letter}) | {panel['device_scale_factor']} | {panel['effective_dpi']:.1f} | {panel['smallest_meaningful_glyph_height_pt']:.2f} |")
    coverages = [p["model_width_fraction"] for p in summary["4"]["panels"].values()]
    lines += ["", f"图 4 的模型覆盖分图宽度 {min(coverages):.1%}–{max(coverages):.1%}。"
             "字高按浏览器文字墨迹边界测量，并按分图实际印刷宽度折算。标签统一 9 pt 粗体，位于白色标签区，分图间距为 2 mm。",
             "", "## 画面状态", "", "图 2 从独立工作台工程实际读取算例 E，截图 (a) 显示构建阻塞、应力顺序选择和 16.5 kN/m³ 单位诊断。",
             "截图 (b) 在真实构建和独立验证全部通过后截取，保留构建表、验证摘要与发布查看器。为了让诊断区易读，隔离工程把同一 VTU 的副本命名为 `ogs_slope.vtu`。",
             "", "图 4 的字段、剖面位置、色图、色阶和范围模式按现有稿件复现。六幅色标端点逐幅与原图核对。C 保留 X = 830 m 剖面，E 保留 Y = 30 m 剖面，F 使用 P5–P95。",
             "六幅都收起侧栏并用正交相机重新取景。C 的附加点选卡为排版移除。",
             f"(a) 通过查看器实际点选回原来的 `Source_Cell_ID {probe['cell']}`，读数为 **{probe['minimum_stress']}**。",
             "D、F 的公开拼版与单张图来自本地既有发布包。结果提交包含最终图片和印刷核验所需的版面参数。",
             "", "首次拉取遇到旧图 3 的 Git LFS 对象返回 404，跳过历史图片下载后检出 `92f40f5`。状态核对所用的旧图从 v6 稿件中提取。",
             "命令、退出码和耗时见 `COMMANDS.csv`。构图计算的中间记录留在本机临时目录。", "", "## Playwright 注入 CSS", ""]
    for fig, letter, title in [("2", "a", "图 2(a) 字段与单位"), ("2", "b", "图 2(b) 构建与验证"),
                                ("4", "b", "图 4(a–f) 共用查看器样式")]:
        css = summary[fig]["panels"][letter]["injected_css"]
        lines.extend([f"### {title}", "", "```css", css.strip(), "```", ""])
    a_css = summary["4"]["panels"]["a"]["injected_css"]
    b_css = summary["4"]["panels"]["b"]["injected_css"]
    extra_styles = [("图 2(b) 内嵌查看器", summary["2"]["panels"]["b"]["embedded_viewer_css"]),
                    ("图 4(a) 点选读数卡", a_css.removeprefix(b_css))]
    for title, css in extra_styles:
        lines.extend([f"### {title}", "", "```css", css.strip(), "```", ""])
    (out/"REPORT_r7.md").write_text("\n".join(lines).rstrip()+"\n", encoding="utf-8")


parser = argparse.ArgumentParser()
parser.add_argument("capture_dir", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--figure-2-only", action="store_true",
                    help="Compose the workbench figure and trim its lower blank margin")
args = parser.parse_args()
out = args.output
(out/"panels").mkdir(parents=True, exist_ok=True)
wb = read_json(args.capture_dir/"workbench_capture.json")
figures = [(2, "fig2_workbench", wb)]
if not args.figure_2_only:
    views = read_json(args.capture_dir/"viewer_capture.json")
    figures.append((4, "fig4_cases", views))
summary = {}
specs = []
for num, name, records in figures:
    panels = geometry(args.capture_dir, num, records, trim_workbench=args.figure_2_only)
    placed, height = positions(num, panels)
    assert num != 2 or height <= 17, height
    dims = write_composite(out, name, placed, height)
    specs.append((num, placed, height))
    summary[str(num)] = dict(width_cm=FIGURE_WIDTH, height_cm=height, gap_cm=GAP, label_font_pt=9,
                             composed_resolution_px=list(dims), panels={letter: info for letter,_,info in panels})
    for letter,im,info in panels:
        im.save(out/"panels"/f"fig{num}_{letter}.png", dpi=(info["effective_dpi"],)*2, optimize=True)
    print(f"Figure {num}: {FIGURE_WIDTH:.2f} × {height:.3f} cm, masters {dims[0]} × {dims[1]} px")
    print("Minimum ink height by panel:", ", ".join(f"{a} {i['smallest_meaningful_glyph_height_pt']:.3f} pt" for a,_,i in panels))
if not args.figure_2_only:
    contact_sheets(out, specs)
    report(out, summary, views["A"]["probe"])
(out/"print_check.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

log_dir = args.capture_dir.parent/"logs"
rows = [read_json(p) for p in sorted(log_dir.glob("*.json"))]
with (out/"COMMANDS.csv").open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=["id","command","cwd","started_at","exit_code","duration_seconds"], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
