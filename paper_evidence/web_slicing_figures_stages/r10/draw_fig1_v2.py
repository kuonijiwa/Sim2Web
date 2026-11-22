"""Figure 1 (v2): Sim2Web workflow, one main row, configuration above, validation below.

Drawn in millimetres at final print size (165 mm wide). Liberation Sans is metric-compatible
with Arial, which Elsevier recommends.
"""
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent
mpl.rcParams.update({
    "font.family": "Liberation Sans",
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
})

W, H = 165.0, 64.0            # mm
MM = 1 / 25.4
fig = plt.figure(figsize=(W * MM, H * MM))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

INK = "#222222"
GREY_FACE, GREY_EDGE = "#F2F2F2", "#7A7A7A"
BLUE_FACE, BLUE_EDGE = "#E6EEF7", "#2F5F8F"
TITLE_PT, BODY_PT = 9.0, 8.0
LW = 0.8
sizes = []


def box(x, y, w, h, title, lines=(), kind="grey", dashed=False):
    face, edge = (BLUE_FACE, BLUE_EDGE) if kind == "blue" else (GREY_FACE, GREY_EDGE)
    if kind == "white":
        face, edge = "white", "#4A4A4A"
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6",
                                fc=face, ec=edge, lw=LW, ls=(0, (3, 2)) if dashed else "-"))
    n = len(lines)
    line_h = 3.9
    block = 4.4 + n * line_h
    top = y + h / 2 + block / 2
    ax.text(x + w / 2, top - 2.2, title, ha="center", va="center", fontsize=TITLE_PT,
            fontweight="bold", color=INK)
    sizes.append(TITLE_PT)
    for i, s in enumerate(lines):
        ax.text(x + w / 2, top - 4.4 - line_h * (i + 0.5), s, ha="center", va="center",
                fontsize=BODY_PT, color=INK)
        sizes.append(BODY_PT)


def arrow(points, dashed=False):
    for (x0, y0), (x1, y1) in zip(points[:-2], points[1:-1]):
        ax.plot([x0, x1], [y0, y1], color=INK, lw=LW, ls=(0, (3, 2)) if dashed else "-",
                solid_capstyle="butt")
    (x0, y0), (x1, y1) = points[-2], points[-1]
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=7,
                                 lw=LW, color=INK, ls=(0, (3, 2)) if dashed else "-",
                                 shrinkA=0, shrinkB=0))


# main row
ROW_Y, ROW_H = 24.0, 18.0
cols = [(1.0, 31.0), (37.0, 31.0), (73.0, 29.0), (107.0, 28.0), (140.0, 24.0)]
box(*cols[0][:1], ROW_Y, cols[0][1], ROW_H, "Solver results",
    ("FLAC3D · 3DEC", "Abaqus · MOOSE", "OpenGeoSys"))
box(cols[1][0], ROW_Y, cols[1][1], ROW_H, "VTU input",
    ("named components", "convert / ODB export"))
box(cols[2][0], ROW_Y, cols[2][1], ROW_H, "sim2web build",
    ("input checks", "surfaces, sections"), kind="blue")
box(cols[3][0], ROW_Y, cols[3][1], ROW_H, "Web package",
    ("VTP + index.json", "source IDs"), kind="blue")
box(cols[4][0], ROW_Y, cols[4][1], ROW_H, "Browser",
    ("viewer,", "no server"), kind="white")

mid = ROW_Y + ROW_H / 2
for (xa, wa), (xb, _) in zip(cols[:-1], cols[1:]):
    arrow([(xa + wa, mid), (xb, mid)])

# configuration above the build step
CFG_X, CFG_W, CFG_Y, CFG_H = 73.0, 29.0, 49.0, 13.0
box(CFG_X, CFG_Y, CFG_W, CFG_H, "case.yaml", ("Workbench or CLI",), kind="blue")
arrow([(CFG_X + CFG_W / 2, CFG_Y), (CFG_X + CFG_W / 2, ROW_Y + ROW_H)])

# independent validation below
VAL_X, VAL_W, VAL_Y, VAL_H = 73.0, 62.0, 2.0, 13.0
box(VAL_X, VAL_Y, VAL_W, VAL_H, "sim2web validate (independent)",
    ("re-reads source VTU and package",), kind="blue", dashed=True)
vtu_cx = cols[1][0] + cols[1][1] / 2
pkg_cx = cols[3][0] + cols[3][1] / 2
arrow([(vtu_cx, ROW_Y), (vtu_cx, VAL_Y + VAL_H / 2), (VAL_X, VAL_Y + VAL_H / 2)], dashed=True)
arrow([(pkg_cx, ROW_Y), (pkg_cx, VAL_Y + VAL_H)], dashed=True)

for ext in ("pdf", "svg", "eps"):
    fig.savefig(OUT / f"fig1_architecture.{ext}")
fig.savefig(OUT / "fig1_architecture.png", dpi=600, facecolor="white")
fig.savefig(OUT / "fig1_architecture.tif", dpi=1000, facecolor="white",
            pil_kwargs={"compression": "tiff_lzw"})
check = {"width_cm": W / 10, "height_cm": H / 10, "min_font_pt": min(sizes),
         "boxes": 8, "font": "Liberation Sans (Arial metrics)"}
(OUT / "print_check.json").write_text(json.dumps(check, indent=1))
print(json.dumps(check))
