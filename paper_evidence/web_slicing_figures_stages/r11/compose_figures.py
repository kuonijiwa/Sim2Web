"""Compose six r11 figures at their final physical size."""
import hashlib
import json
import math
import os
import shutil
import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


root = Path(sys.argv[1])
captures = root / "captures"
plots = root / "plots"
delivery = root / "delivery"
delivery.mkdir(exist_ok=True)
DPI = 600
WIDTH = 16.5
PT_CM = 72 / 2.54
WHITE = "#ffffff"
INK = "#222a31"
FRAME = "#d2d5d8"
fonts = Path(os.environ["WINDIR"]) / "Fonts"
figures = {}


def cm(value):
    return round(value * DPI / 2.54)


def font(pt, bold=False):
    return ImageFont.truetype(str(fonts / ("arialbd.ttf" if bold else "arial.ttf")), round(pt * DPI/72))


def text(draw, x, y, value, pt, anchor="la", bold=False):
    draw.text((cm(x), cm(y)), value, fill=INK, font=font(pt, bold), anchor=anchor)


def heading(draw, x, y, label, title):
    text(draw, x, y, f"({label})", 9, "ls", True)
    text(draw, x+.53, y, title, 7.5, "ls")


def read(file):
    return json.loads(file.read_text(encoding="utf-8-sig"))


def rgb(file):
    with Image.open(file) as image:
        return image.convert("RGB")


def sheet(height):
    return Image.new("RGB", (cm(WIDTH), cm(height)), WHITE)


def place(canvas, source, x, y, width):
    height = width * source.height/source.width
    canvas.paste(source.resize((cm(width), cm(height)), Image.Resampling.LANCZOS), (cm(x), cm(y)))
    return source.width*2.54/width


def centered(canvas, source, x, y, width, height):
    actual_w = min(width, height*source.width/source.height)
    actual_h = actual_w*source.height/source.width
    dpi = place(canvas, source, x+(width-actual_w)/2, y+(height-actual_h)/2, actual_w)
    return dpi, actual_w


def frame(draw, x, y, w, h):
    draw.rectangle(tuple(map(cm, [x,y,x+w,y+h])), outline=FRAME, width=2)


def bounds(image, chromatic=False):
    pixels = np.asarray(image)
    if chromatic:
        selected = (pixels.max(axis=2)-pixels.min(axis=2) > 18) & (pixels.min(axis=2) < 231)
    else:
        selected = pixels.min(axis=2) < 240
    y, x = np.nonzero(selected)
    assert len(x), "Empty rendered panel"
    return int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)


def crop_box(image, box, padx=.04, pady=.06):
    x, y, xx, yy = box
    dx, dy = round((xx-x)*padx), round((yy-y)*pady)
    return max(0,x-dx), max(0,y-dy), min(image.width,xx+dx), min(image.height,yy+dy)


def color_crop(image, padx=.06, pady=.06):
    return image.crop(crop_box(image, bounds(image, chromatic=True), padx, pady))


def save(number, image, filename, min_pt, panels, **details):
    file = delivery / filename
    image.save(file, dpi=(DPI, DPI), optimize=True)
    with Image.open(file) as result:
        assert result.mode == "RGB"
        assert math.isclose(result.info["dpi"][0], 600, abs_tol=.01)
        assert abs(result.width*2.54/DPI-WIDTH) < .012
    assert all(panel["effective_dpi"] >= 599.98 for panel in panels.values())
    data = file.read_bytes()
    assert len(data) <= 9_000_000
    figures[str(number)] = {
        "file": file.name, "width_cm": WIDTH, "height_cm": image.height*2.54/DPI,
        "pixels": list(image.size), "dpi": DPI, "minimum_text_pt": min_pt,
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "panels": panels,
        **details,
    }
    proof = image.copy()
    proof.thumbnail((1220, 1200), Image.Resampling.LANCZOS)
    proof.save(root/f"proof_{number}.png")
    print(number, file.name, image.size, len(data), "bytes")


def tick(v):
    if abs(v) < 1e-15:
        return "0"
    return format(Decimal(f"{v:.3g}"), "f").replace("-", "−")


def colors(bar):
    return [tuple(round(v*255) for v in band) for band in bar]


def field_legend(shot):
    coloring = shot["state"]["coloring"]
    unit = shot["unit"]
    field = coloring["name"]
    factor = 1e-6 if unit == "Pa" else 1
    label = {
        "Stress_Min_Principal": "σ3 (MPa)", "Stress_Max_Principal": "σ1 (MPa)",
        "TotalDisplacement": "|u| (m)", "Y_Disp": "u_y (m)",
    }[field]
    return {"title": label, "unit": "MPa" if unit == "Pa" else unit,
            "source_unit": unit, "source_range": [coloring["min"], coloring["max"]],
            "range": [coloring["min"]*factor, coloring["max"]*factor], "cmap": coloring["colormap"],
            "bands": coloring["bands"], "rgb": [row["color"] for row in shot["legend"]]}


def marks(bar):
    lo, hi = bar["range"]
    return [lo, (lo+hi)/2, hi]


def vertical(draw, x, y, height, bar, bar_width=.16):
    text(draw, x, y-.20, bar["title"], 7.5, "ls")
    palette = colors(bar["rgb"])
    for i, color in enumerate(reversed(palette)):
        yy = y + i*height/len(palette)
        bottom = y+(i+1)*height/len(palette)
        draw.rectangle(tuple(map(cm, [x,yy,x+bar_width,bottom])), fill=color)
    for i, mark in enumerate(reversed(marks(bar))):
        yy = y+i*height/2
        draw.line(tuple(map(cm, [x+bar_width, yy, x+bar_width+.08, yy])), fill=INK, width=2)
        text(draw, x+bar_width+.14, yy, tick(mark), 7, "lm")


def horizontal(draw, y, bar):
    x, span, height = 4.6, 7.3, .17
    palette = colors(bar["rgb"])
    for i, color in enumerate(palette):
        xx = x+i*span/len(palette)
        right = x+(i+1)*span/len(palette)
        draw.rectangle(tuple(map(cm,[xx,y,right,y+height])), fill=color)
    for i, mark in enumerate(marks(bar)):
        xx = x+i*span/2
        draw.line(tuple(map(cm,[xx,y+height,xx,y+height+.06])), fill=INK, width=2)
        text(draw, xx, y+height+.11, tick(mark), 7, "ma")
    text(draw, x+span+.32, y+height/2, bar["title"], 7.5, "lm")


def panel(shot, dpi, legend=None):
    return {"effective_dpi": dpi, "legend": legend or field_legend(shot),
            "settings": {k:v for k,v in shot["settings"].items() if k != "cam"},
            "camera": shot["state"]["camera"], "angles_deg": shot["angles"],
            "geometry": shot["state"]["geometry"], "ground_z_m": shot.get("ground")}


# Fig. 2 · actual workbench rail and diagnostics above one another.
fig2 = read(captures/"fig2.json")
left, right = fig2["left"], fig2["right"]
nav = rgb(captures/"steps.png")
diagnostic = rgb(captures/"diagnostics.png")
y = .48
nav_w, diag_w = 3.74, 4.64
nav_h, diag_h = nav_w*nav.height/nav.width, diag_w*diagnostic.height/diagnostic.width
nav_pt = left["font"]["steps"]*nav_w*PT_CM/left["crops"]["steps"]["width"]
diag_pt = left["font"]["diagnostics"]*diag_w*PT_CM/left["crops"]["diagnostics"]["width"]
assert nav_pt >= 6 and diag_pt >= 5
h = nav_h+.24+diag_h
canvas = sheet(y+h+.10)
draw = ImageDraw.Draw(canvas)
heading(draw, .08, .36, "a", "Workbench")
heading(draw, 5.35, .36, "b", "Published result")
nav_dpi = place(canvas, nav, (.28+4.64-nav_w)/2, y, nav_w)
diag_dpi = place(canvas, diagnostic, .08, y+nav_h+.24, diag_w)
frame(draw, .02, y, 4.95, nav_h)
frame(draw, .02, y+nav_h+.24, 4.95, diag_h)
pit = color_crop(rgb(captures/right["file"]), .15, .16)
pit_dpi, model_w = centered(canvas, pit, 5.35, y, 9.34, h)
bar = field_legend(right)
vertical(draw, 14.91, y+(h-4.33)/2, 4.33, bar)
save(2, canvas, "fig2_workbench.png", min(nav_pt, diag_pt, 7),
     {"a_steps": {"effective_dpi": nav_dpi, "legend": None, "font_pt": nav_pt},
      "a_diagnostics": {"effective_dpi": diag_dpi, "legend": None, "font_pt": diag_pt},
      "b": panel(right, pit_dpi)},
     css=[left["css"], right["css"]], diagnostics=left["diagnostic"], browser=fig2["browser"],
     build=left["build"], validation=left["validation"])


# Fig. 3 · the complete native 16:9 viewport, as operated.
fig3 = read(captures/"fig3.json")
image = rgb(captures/fig3["file"])
font_sizes = [pt*WIDTH*PT_CM/fig3["viewport"]["width"] for pt in fig3["uiFontCss"]]
canvas = image.resize((cm(WIDTH), cm(WIDTH*9/16)), Image.Resampling.LANCZOS)
save(3, canvas, "fig3_viewer_interface.png", min(font_sizes),
     {"window": panel(fig3, image.width*2.54/WIDTH)}, css=[], native_font_pt=font_sizes,
     probe=fig3["probe"], section_slider=fig3["slider"], viewport=fig3["viewport"], dsf=fig3["dsf"])


# Fig. 4 · six measured renders on the same heading, model and legend grid.
fig4 = read(captures/"fig4.json")
titles = {
    "A": "FLAC3D cavern · σ3", "B": "FLAC3D slope · σ1", "C": "3DEC slope · |u|",
    "D": "FLAC3D pit · u_y", "E": "OpenGeoSys slope · σ3", "F": "3DEC slope · |u|",
}
panel_w, model_w, model_h = 8.07, 6.44, 4.79
step_y = model_h+.51
canvas = sheet(step_y*3+.12)
draw = ImageDraw.Draw(canvas)
curated = {}
for i, (case, shot) in enumerate(fig4.items()):
    x, y = .09+(i%2)*8.24, (i//2)*step_y
    heading(draw, x, y+.36, case.lower(), "Case "+case+" · "+titles[case])
    image = color_crop(rgb(captures/shot["file"]), .12, .07)
    dpi, actual_w = centered(canvas, image, x, y+.46, model_w, model_h)
    vertical(draw, x+6.47, y+1.22, 3.36, field_legend(shot))
    curated[case] = {**panel(shot, dpi), "model_frame_fraction_width": actual_w/panel_w, "bar_fraction_width": .16/panel_w}
save(4, canvas, "fig4_published_cases.png", 7, curated, css=[fig4["A"]["css"]])


# Fig. 5 · recomputed full-resolution plot with vector companion.
fig5 = read(plots/"fig5_plot.json")
image = rgb(plots/"fig5_principal_stress.png")
save(5, image, "fig5_principal_stress.png", 7,
     {key: {"effective_dpi": DPI, **row,
            "legend": {"title": "Cells per bin", "range": fig5["bin_colour_range"], "cmap": "matplotlib turbo",
                       "scale": "log", "bands": None}} for key,row in zip("abc",fig5["panels"])},
     comparison=fig5)
shutil.copyfile(plots/"fig5_principal_stress.pdf", delivery/"fig5_principal_stress.pdf")


# Fig. 6 · the same camera and region before and after removal.
fig6 = read(plots/"fig6.json")
bar = {"title": "|u| (m)", "unit": "m", "range": fig6["range"], "cmap": fig6["colormap"],
       "bands": fig6["bands"], "rgb": fig6["band_rgb"]}
viewport_w, viewport_h = fig6["viewport"]
pan_w = 8.03
top_y = .48
top_h = pan_w*viewport_h/viewport_w
detail_y = top_y+top_h+.82
canvas = sheet(detail_y+top_h+.11)
draw = ImageDraw.Draw(canvas)
x0, y0, x1, y1 = fig6["roi_fraction_xyxy"]
details = {}
for i,(key, row) in enumerate(fig6["panels"].items()):
    x = .10+i*8.26
    title = ("Generic surface" if key=="a" else "Sim2Web")+f" · {row['faces']:,} faces · {row['bytes']/1e6:.1f} MB"
    heading(draw, x, .35, key, title)
    full = rgb(plots/row["surface"])
    dpi = place(canvas, full, x, top_y, pan_w)
    draw.rectangle(tuple(map(cm, [x+x0*pan_w,top_y+y0*top_h,x+x1*pan_w,top_y+y1*top_h])),
                   outline="#be2e27", width=5)
    detail = rgb(plots/row["detail"])
    detail_dpi = place(canvas, detail, x, detail_y, pan_w)
    frame(draw, x, detail_y, pan_w, top_h)
    details[key+"_full"] = {**row, "effective_dpi": dpi, "legend": bar, "opacity": 1}
    details[key+"_detail"] = {"effective_dpi": detail_dpi, "legend": None,
                                "wireframe": fig6["detail_style"], "region": fig6["roi_fraction_xyxy"]}
horizontal(draw, top_y+top_h+.13, bar)
save(6, canvas, "fig6_internal_faces.png", 7, details,
     render={key:value for key,value in fig6.items() if key not in ("panels","band_rgb")})


# Fig. 7 · a common camera, crop and colour scale across the three stages.
fig7 = read(captures/"fig7.json")
stages = fig7["results"]
images = [rgb(captures/shot["file"]) for shot in stages.values()]
boxes = [bounds(image, chromatic=True) for image in images]
common = (min(b[0] for b in boxes), min(b[1] for b in boxes),
          max(b[2] for b in boxes), max(b[3] for b in boxes))
assert all(value > 0 for value in common[:2])
assert common[2] < images[0].width and common[3] < images[0].height, common
common = crop_box(images[0], common, .026, .055)
w = 5.13
h = w * (common[3]-common[1]) / (common[2]-common[0])
y = .46
canvas = sheet(y+h+1.35)
draw = ImageDraw.Draw(canvas)
staged = {}
for i,(stage, shot) in enumerate(stages.items()):
    x = .11+5.56*i
    heading(draw, x, .34, "abc"[i], stage)
    dpi = place(canvas, images[i].crop(common), x, y, w)
    cells = shot["state"]["geometry"]["layer:excavation"]["cells"]
    text(draw, x+w/2, y+h+.16, f"{cells:,} faces", 7.5, "ma")
    staged[stage] = {**panel(shot, dpi), "faces": cells}
    if i < 2:
        yy = y+.55*h
        xx = x+w+.067
        points = [(xx,yy-.10),(xx+.23,yy),(xx,yy+.10)]
        draw.polygon([(cm(px),cm(py)) for px,py in points], fill=INK)
horizontal(draw, y+h+.60, field_legend(shot))
save(7, canvas, "fig7_construction_stages.png", 7, staged,
     common_crop_px=common, common_limits=fig7["range_method"], css=[shot["css"]])


(delivery/"print_check.json").write_text(json.dumps({"figures": figures}, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
