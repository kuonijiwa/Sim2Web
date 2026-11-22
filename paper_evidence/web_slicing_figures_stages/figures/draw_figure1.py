"""Render and check Figure 1 at the manuscript's physical print size."""
from pathlib import Path
import json
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as MplPath

OUT = Path(__file__).resolve().parent
WIDTH, HEIGHT, DPI = 165, 70, 600
mpl.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none", "pdf.fonttype": 42, "ps.fonttype": 42})
fig = plt.figure(figsize=(WIDTH / 25.4, HEIGHT / 25.4), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set(xlim=(0, WIDTH), ylim=(0, HEIGHT))
ax.axis("off")
ink, gray, blue, green = "#152638", "#526170", "#285985", "#2C6955"
labels = []

def text(x, y, value, size=8.2, bold=False, color=ink):
    label = ax.text(x, y, value, ha="center", va="center", fontsize=size,
                    fontweight="bold" if bold else "normal", color=color, linespacing=1.08, zorder=4)
    labels.append((value, label))
    return label

def rounded(x, y, w, h, edge, face, lw=.7, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.15",
                               linewidth=lw, edgecolor=edge, facecolor=face, zorder=z))

def panel(x, title):
    rounded(x, 18, 36.5, 50.5, "#CDD5DD", "#F1F4F7", z=0)
    text(x+18.25, 65, title, 9.6, True, blue)

def box(x, y, title, subtitle=(), h=9.8, w=32.5, accent=blue):
    rounded(x, y, w, h, "#A9B6C2", "white")
    cx, cy = x+w/2, y+h/2
    if len(subtitle)==2:
        text(cx,y+h-.2-1.45,title,8.35,True,accent)
        text(cx,y+5.05,subtitle[0],8.1)
        text(cx,y+1.7,subtitle[1],8.1)
    elif subtitle:
        text(cx,cy+1.8,title,8.35,True,accent)
        text(cx,cy-1.8,subtitle[0],8.1)
    else:
        text(cx,cy,title,8.35,True,accent)
    return (x,y,w,h)

def arrow(poly, dashed=False, both=False, scale=8.8):
    path = MplPath(poly)
    ax.add_patch(FancyArrowPatch(path=path, arrowstyle="<|-|>" if both else "-|>",
                                mutation_scale=scale, linewidth=.9 if dashed else 1.05,
                                linestyle=(0,(3,2.3)) if dashed else "solid",
                                color=green if dashed else gray, zorder=3))

for x, title in [(2,"Solver results"),(43,"Configure"),(84,"Sim2Web build"),(125,"Publish & verify")]:
    panel(x,title)
# solver results: three inputs grouped, then one arrow to the common VTU
rounded(3.2,33.0,34.1,29.8,"#B9C4CF","#E4EAF0",lw=.6,z=0.5)
box(4,52.2,"Native VTU",("FLAC3D / 3DEC", "OpenGeoSys"))
box(4,41.6,"sim2web convert",("MOOSE · Exodus II", "MED · XDMF · Gmsh"),h=9.8)
box(4,33.8,"Abaqus",("ODB exporter",),h=7.0)
arrow([(20.25,33.0),(20.25,30.4)],scale=7)
rounded(4,19.4,32.5,10.6,"#285985","#E3EDF7",lw=.8)
text(20.25,26.6,"VTU",8.35,True,blue)
text(20.25,22.6,"Named components",8.1)

box(45,50,"CLI / Python API",h=9)
box(45,36,"case.yaml",h=10)
box(45,20,"Workbench",("sim2web gui",),h=10.5)
arrow([(61.25,50),(61.25,46.3)],both=True)
arrow([(61.25,35.7),(61.25,30.5)],both=True)

# build: four steps with real gaps between them
BX,BW=85.25,34
box(BX,54.4,"Input checks",("Tensor order, units",),h=7.6,w=BW)
box(BX,41.2,"Surfaces",("Exterior / excavation", "Interface removal"),h=9.8,w=BW)
box(BX,30.2,"Build-time sections",("Interpolated fields",),h=7.6,w=BW)
box(BX,19.4,"Publisher",("VTP, index.json, IDs",),h=7.6,w=BW)
for start,end in [(54.4,51.2),(41.2,38.0),(30.2,27.2)]:
    arrow([(102.25,start),(102.25,end)],scale=6.5)

box(127,45,"Static package",("site/",),h=10.5)
box(127,29,"Browser viewer",("Vue + vtk.js", "Static host / offline"),h=11)
arrow([(143.25,45),(143.25,40.3)])
arrow([(36.7,24.7),(40,24.7),(40,41),(44.7,41)])
arrow([(77.7,41),(81.3,41),(81.3,58.2),(85.0,58.2)])
arrow([(119.45,23.2),(122.5,23.2),(122.5,50.25),(126.7,50.25)])

rounded(50.5,3.5,64,10.5,"#89AB9D","#EAF3EF")
text(82.5,10.6,"Independent validation",8.8,True,green)
text(82.5,6.5,"sim2web validate",8.1)
arrow([(20.25,19.4),(20.25,8.75),(50.3,8.75)],dashed=True)
arrow([(159.5,50.25),(163,50.25),(163,8.75),(115,8.75)],dashed=True)
arrow([(61.25,14),(61.25,19.8)],dashed=True)

fig.canvas.draw()
renderer = fig.canvas.get_renderer()
violations = []
for value,label in labels:
    bbox = label.get_window_extent(renderer)
    if min(bbox.x0,bbox.y0)<0 or bbox.x1>fig.bbox.width or bbox.y1>fig.bbox.height:
        violations.append(value)
assert not violations, violations
fig.savefig(OUT / "fig1_architecture.tif", dpi=1000, facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
for ext in ("svg","pdf","png","eps"):
    target = OUT / f"fig1_architecture.{ext}"
    fig.savefig(target, dpi=DPI, facecolor="white")
    if ext == "svg":
        lines = target.read_text(encoding="utf-8").splitlines()
        target.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")
print("Figure 1:", WIDTH, "x", HEIGHT, "mm, minimum", min(x.get_fontsize() for _,x in labels), "pt")
print("Raster target:", int(WIDTH/25.4*DPI), "x", int(HEIGHT/25.4*DPI), "px at", DPI, "dpi")
stats={"width_mm":WIDTH,"height_mm":HEIGHT,"aspect":WIDTH/HEIGHT,"minimum_font_pt":min(x.get_fontsize() for _,x in labels),
       "panel_title_pt":9.6,"content_boxes":15,"dpi":DPI,"off_canvas_labels":violations}
(OUT/"figure1_print_check.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8")
