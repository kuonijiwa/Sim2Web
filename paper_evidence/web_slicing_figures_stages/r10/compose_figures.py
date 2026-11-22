"""Compose the r10 masters at 165 mm without changing the simulation values."""
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont


run, unchanged = map(Path, sys.argv[1:3])
out = run / "delivery"
out.mkdir(exist_ok=True)
captures = run / "captures"
plots = run / "plots"
DPI, WIDTH = 600, 16.5
PPCM = DPI / 2.54
INK = "#202831"
WHITE = "white"
fonts = Path(os.environ["WINDIR"]) / "Fonts"
figures = {}


def cm(value):
    return round(value * PPCM)


def font(pt, bold=False):
    return ImageFont.truetype(str(fonts / ("arialbd.ttf" if bold else "arial.ttf")), round(pt * DPI / 72))


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rgb(path):
    with Image.open(path) as source:
        return source.convert("RGB")


def show_text(draw, x, y, text, pt, anchor=None, bold=False):
    draw.text((cm(x), cm(y)), text, anchor=anchor, font=font(pt, bold), fill=INK)


def make(height):
    return Image.new("RGB", (cm(WIDTH), cm(height)), WHITE)


def place(image, source, x, y, width):
    height = width * source.height / source.width
    image.paste(source.resize((cm(width), cm(height)), Image.Resampling.LANCZOS), (cm(x), cm(y)))
    return source.width * 2.54 / width


def save(number, image, file, min_pt, panels, extra=None):
    path = out / file
    image.save(path, dpi=(DPI, DPI), optimize=True)
    return inspect(number, path, min_pt, panels, extra)


def inspect(number, path, min_pt, panels, extra=None):
    with Image.open(path) as image:
        assert image.mode == "RGB" and abs(image.info["dpi"][0] - DPI) < .02, path
        assert abs(image.width * 2.54 / DPI - WIDTH) < .015
        assert path.stat().st_size <= 9_000_000
        info = {"width_cm": WIDTH, "height_cm": image.height * 2.54 / DPI, "dpi": DPI,
                "pixels": list(image.size), "smallest_nominal_text_pt": min_pt, "panels": panels,
                "file": path.name, "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    assert all(p["effective_dpi"] >= 599.98 for p in panels.values())
    figures[str(number)] = {**info, **(extra or {})}
    print(number, path.name, info["pixels"], info["bytes"], "B")
    proof = rgb(path)
    proof.thumbnail((1200, 1050), Image.Resampling.LANCZOS)
    proof.save(run / f"proof_{number}.png")


def tick(value):
    if abs(value) < 1e-15:
        return "0"
    return format(Decimal(f"{value:.3g}"), "f").replace("-", "−")


def color(row):
    return tuple(round(value * 255) for value in row["color"])


def physical_field(field, unit):
    if field.startswith("Stress_"):
        number = {"Stress_Min_Principal": 3, "Stress_Mid_Principal": 2, "Stress_Max_Principal": 1}[field]
        return f"σ{number} (MPa)", "MPa", 1e-6 if unit == "Pa" else 1
    return {"TotalDisplacement": "|u| (m)", "Y_Disp": "u_y (m)"}[field], unit, 1


def colour_data(record):
    colouring = record["state"]["coloring"]
    title, unit, mult = physical_field(colouring["name"], record["unit"])
    return {"title": title, "unit": unit, "scale": mult,
            "range": [colouring["min"] * mult, colouring["max"] * mult],
            "source_range": [colouring["min"], colouring["max"]], "source_unit": record["unit"],
            "colourmap": colouring["colormap"], "bands": colouring["bands"]}


def vertical(draw, x, y, height, legend, spec):
    show_text(draw, x, y, spec["title"], 7.75)
    bar_y, bar_h, bar_w = y + .66, height - .88, .22
    for i, band in enumerate(reversed(legend)):
        top = bar_y + i * bar_h / len(legend)
        bottom = bar_y + (i + 1) * bar_h / len(legend)
        draw.rectangle((cm(x), cm(top), cm(x + bar_w), cm(bottom)), fill=color(band))
    lo, hi = spec["range"]
    for i in range(5):
        y_tick = bar_y + i * bar_h / 4
        draw.line((cm(x + bar_w), cm(y_tick), cm(x + bar_w + .075), cm(y_tick)), fill=INK, width=2)
        show_text(draw, x + bar_w + .11, y_tick, tick(hi - (hi-lo)*i/4), 7, anchor="lm")


def horizontal(draw, y, legend, spec):
    x, span, height = 3.7, 9.1, .24
    show_text(draw, WIDTH/2, y, spec["title"], 7.75, anchor="ma")
    y += .43
    for i, band in enumerate(legend):
        draw.rectangle((cm(x+i*span/len(legend)), cm(y),
                        cm(x+(i+1)*span/len(legend)), cm(y+height)), fill=color(band))
    lo, hi = spec["range"]
    for i in range(5):
        x_tick = x + i * span / 4
        draw.line((cm(x_tick), cm(y+height), cm(x_tick), cm(y+height+.075)), fill=INK, width=2)
        show_text(draw, x_tick, y+height+.10, tick(lo+(hi-lo)*i/4), 7, anchor="ma")


def item(record, achieved_dpi, legend=None):
    return {"effective_dpi": achieved_dpi, "legend": legend or colour_data(record),
            "field": record["params"]["field"], "camera": [float(v) for v in record["params"]["cam"].split(",")],
            "settings": record["params"], "angles_deg": record.get("angle")}


# Figure 1 retains the final vector and typographic design.
fig1 = run / "fig1_v2"
vector = rgb(fig1 / "fig1_architecture.png")
save(1, vector, "fig1_architecture.png", 8, {"diagram": {"effective_dpi": DPI, "legend": None}},
     {"font": "Liberation Sans", "caption": "Sim2Web workflow and independent validation"})
shutil.copyfile(fig1 / "fig1_architecture.pdf", out / "fig1_architecture.pdf")

# Figure 2 explicitly stays byte-identical to the approved layout.
f2 = read(unchanged / "print_check.json")
shutil.copyfile(unchanged / "fig2_workbench.png", out / "fig2_workbench.png")
f2_legend = f2["right"]["actors"]["layer:exterior"]["lutRange"]
inspect(2, out / "fig2_workbench.png", f2["left"]["native_step_nominal_pt"], {
    "a": {"effective_dpi": 300 * 4 * 2.54 / 4.23, "legend": None},
    "b": {"effective_dpi": f2["right"]["crop_css"]["width"] * 4 * 2.54 / f2["layout_cm"]["b"],
          "legend": {"range": f2_legend, "unit": "m", "title": "Displacement magnitude (m)",
                     "colourmap": "viridis", "bands": 8},
          "camera": f2["right"]["camera"]},
}, {"retained_sha256": f2["png"]["sha256"], "diagnostic_body_pt": f2["left"]["native_diagnostic_body_nominal_pt"],
    "legend_tick_pt": f2["right"]["nominal_legend_tick_pt"], "panel_left_css": "",
    "panel_right_css": f2["right"]["injected_css"]})
assert figures["2"]["retained_sha256"] == figures["2"]["sha256"]

# Figure 3 uses the complete native window as the background for the leader lines.
f3 = read(captures / "fig3.json")
full = rgb(captures / f3["file"])
height3 = WIDTH * full.height / full.width
canvas = make(height3)
dpi3 = place(canvas, full, 0, 0, WIDTH)
draw = ImageDraw.Draw(canvas)
f3_text = [
    "Stage selector (IV-2)", "Field selector (minimum principal stress)",
    "Layer list (excavation surface)", "Section axis and position slider",
    "Probe value and Source_Cell_ID", "Colour legend",
]
targets = f3["boxes"]
for i, box in enumerate(targets):
    side = 1 if i < 4 else -1
    x = box["x"] + (box["width"] if side == 1 else 0)
    y = box["y"] + box["height"] / 2
    if i == 3:
        y = (y + f3["slider"]["y"] + f3["slider"]["height"] / 2) / 2
        x = f3["slider"]["x"] + f3["slider"]["width"]
    x_bubble = (365 if i in (0, 2) else 390) if side == 1 else x - 63
    u, v = x_bubble / 1440 * WIDTH, y / 1440 * WIDTH
    draw.line((cm(u), cm(v), cm(x / 1440 * WIDTH), cm(v)), fill=INK, width=4)
    radius = cm(.242)
    center = cm(u), cm(v)
    draw.ellipse((center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius),
                 fill=WHITE, outline=INK, width=4)
    show_text(draw, u, v+.003, str(i+1), 9, anchor="mm", bold=True)
min_native = min(f3["font"]) * WIDTH * 72 / (1440 * 2.54)
f3_panel = item(f3, dpi3)
save(3, canvas, "fig3_viewer_interface.png", min_native, {"window": f3_panel},
     {"native_ui_nominal_pt": [size * WIDTH * 72 / (1440 * 2.54) for size in f3["font"]],
      "callout_pt": 9, "callouts": f3_text, "probe": f3["hit"], "injected_css": ""})

# Figure 4 uses a separate slim legend in each half-width panel.
f4 = read(captures / "fig4.json")
canvas = make(14.18)
draw = ImageDraw.Draw(canvas)
f4_panels = {}
for i, (case, record) in enumerate(f4.items()):
    x = .07 + i % 2 * 8.27
    y = .06 + i // 2 * 4.72
    show_text(draw, x, y+.28, f"({chr(97+i)})", 9, anchor="ls", bold=True)
    show_text(draw, x+.59, y+.26, f"Case {case}", 7.5, anchor="ls")
    model = rgb(captures / record["file"])
    effective = place(canvas, model, x, y+.35, 6.43)
    spec = colour_data(record)
    vertical(draw, x+6.48, y+.44, 3.80, record["legend"], spec)
    if case == "A":
        hit = record["probe"]["hit"]
        row = next(row for row in hit["rows"] if row["name"] == record["params"]["field"])
        show_text(draw, x+.12, y+4.55, f"Source_Cell_ID {hit['sourceCell']} · {row['text']}", 7.5, anchor="ls")
    f4_panels[case] = item(record, effective, spec)
save(4, canvas, "fig4_published_cases.png", 7, f4_panels, {"injected_css": f4["A"]["css"]})

# Figure 5 keeps the PDF vector and removes the redundant raster alpha channel.
f5 = read(plots / "fig5_plot.json")
save(5, rgb(plots / "fig5_principal_stress.png"), "fig5_principal_stress.png", 7,
     {chr(97 + i): {"effective_dpi": DPI, **p, "legend": {"range": f5["bin_colour_range"], "unit": "cells/bin"}}
      for i, p in enumerate(f5["panels"])}, {"comparison": f5})
shutil.copyfile(plots / "fig5_principal_stress.pdf", out / "fig5_principal_stress.pdf")

# Figure 6 applies a common crop to both measured surface renders.
f6 = read(plots / "fig6_render.json")
surfaces = {key: rgb(plots / panel["file"]) for key, panel in f6["panels"].items()}
boxes = [ImageChops.difference(im, Image.new("RGB", im.size, WHITE)).getbbox() for im in surfaces.values()]
total_w, total_h = next(iter(surfaces.values())).size
lo = min(b[0] for b in boxes)
hi = max(b[2] for b in boxes)
midpoint = round((lo + hi) / 2)
half = max(965, (hi-lo)//2+45)
crop_left = max(0, min(total_w - 2*half, midpoint-half))
crop_right = min(total_w, crop_left + 2*half)
crop_top = max(0, min(b[1] for b in boxes)-30)
crop_bottom = min(total_h, max(b[3] for b in boxes)+30)
clip6 = crop_left, crop_top, crop_right, crop_bottom
view_w = 7.92
model_height = view_w * (crop_bottom-crop_top)/(crop_right-crop_left)
canvas = make(model_height + 2.38)
draw = ImageDraw.Draw(canvas)
f6_panels = {}
spec6 = {"title": "|u| (m)", "unit": "m", "range": f6["range"], "colourmap": f6["colormap"], "bands": f6["bands"]}
for i, (key, im) in enumerate(surfaces.items()):
    x = .12 + i * 8.33
    row = f6["panels"][key]
    show_text(draw, x, .36, f"({key})", 9, anchor="ls", bold=True)
    show_text(draw, x+.54, .35, ("Contacts retained", "Contacts removed")[i], 7.5, anchor="ls")
    achieved = place(canvas, im.crop(clip6), x, .44, view_w)
    show_text(draw, x+view_w/2, model_height+.77,
              f"{row['faces']:,} faces · {row['bytes']/1e6:.1f} MB", 7.5, anchor="ma")
    f6_panels[key] = {**row, "effective_dpi": achieved, "legend": spec6}
horizontal(draw, model_height+1.23, f6["legend"], spec6)
save(6, canvas, "fig6_internal_faces.png", 7, f6_panels,
     {"render": {key: f6[key] for key in ("renderer", "camera", "parallel_scale", "cut", "opacity", "range_mode")},
      "crop_px": clip6})

# Figure 7 uses one common scale for the original three camera-matched stages.
f7 = read(captures / "fig7.json")
canvas = make(5.18)
draw = ImageDraw.Draw(canvas)
f7_panels = {}
for i, (stage, record) in enumerate(f7["stages"].items()):
    x = .075 + i*5.51
    model_w = 5.31
    show_text(draw, x, .34, f"({chr(97+i)})", 9, anchor="ls", bold=True)
    show_text(draw, x+.55, .33, stage, 7.5, anchor="ls")
    effective = place(canvas, rgb(captures / record["file"]), x, .43, model_w)
    f7_panels[stage] = item(record, effective)
horizontal(draw, 4.12, record["legend"], colour_data(record))
save(7, canvas, "fig7_construction_stages.png", 7, f7_panels,
     {"common_range_method": f7["limits_method"], "injected_css": record["css"]})

(out / "print_check.json").write_text(json.dumps({"figures": figures}, indent=2, ensure_ascii=False)+"\n",
                                     encoding="utf-8")
