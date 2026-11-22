import numpy as np, pyvista as pv, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFont
from sim2web.fields import principal_values
import vtk

INK, INK2, GRID = "#0b0b0b", "#52514e", "#dcdad4"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})
blues = LinearSegmentedColormap.from_list("blues", ["#dbe8f8", "#2a78d6", "#0b2f5c"])

# ---- Figure 3: principal stresses, generic VTK/ParaView filter vs file order (Case A)
m = pv.read("/home/claude/SimWebView/examples/flac3d_cavern_iv2/input/IV-2.vtu")
S = np.asarray(m.cell_data["Stress"], dtype=np.float64)
keep = np.abs(S).max(1) > 1e-8
f = vtk.vtkTensorPrincipalInvariants(); f.SetInputData(m); f.Update()
o = pv.wrap(f.GetOutput())
gen = np.sort(np.column_stack([np.asarray(o.cell_data[f"Stress - Sigma {k}"]) for k in (1, 2, 3)]), axis=1)[keep]
ref = principal_values(S, ["XX", "YY", "ZZ", "XY", "XZ", "YZ"])[keep]
fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.9), constrained_layout=True)
titles = ["(a) σ1, maximum", "(b) σ2, intermediate", "(c) σ3, minimum"]
for k, ax in zip((2, 1, 0), axes):
    x, y = ref[:, k], gen[:, k]
    lo, hi = min(x.min(), y.min()), max(x.max(), y.max())
    hb = ax.hexbin(x, y, gridsize=70, cmap=blues, norm=LogNorm(), mincnt=1, linewidths=0, extent=(lo, hi, lo, hi))
    ax.plot([lo, hi], [lo, hi], color=INK2, lw=1, ls="--")
    err = np.abs(y - x).max()
    ax.set_title(titles[(2, 1, 0).index(k)], fontsize=9, color=INK, loc="left")
    ax.grid(color=GRID, lw=0.5)
    ax.set_aspect("equal")
    txt = f"max |Δ| = {err:.2f} MPa\n({100*err/np.ptp(x):.0f}% of range)"
    if k == 2:
        false_t = int(((y > 0) & (x <= 0)).sum())
        ax.axhspan(0, hi, color=ORANGE, alpha=0.08, lw=0)
        txt += f"\n{false_t:,} cells tensile\nonly in generic result"
    ax.text(0.97, 0.04, txt, transform=ax.transAxes, va="bottom", ha="right", fontsize=7.5, color=INK,
            bbox=dict(facecolor="white", edgecolor=GRID, boxstyle="round,pad=0.3"))
axes[0].set_ylabel("generic filter, VTK order (MPa)")
fig.supxlabel("principal stress from the component order declared in the file, XX,YY,ZZ,XY,XZ,YZ (MPa)", fontsize=9, color=INK)
cb = fig.colorbar(hb, ax=axes, shrink=0.8, pad=0.01); cb.set_label("cells per bin", color=INK2, fontsize=8)
fig.savefig("/tmp/figs/fig3_principal_caseA.png", dpi=300)

# ---- Figure 5: exterior faces published, by internal-face handling
cases = ["Case C (3DEC, 97 MB)", "Case F (3DEC, 75 MB)"]
data = {"keep all faces (generic Extract Surface)": [917062, 693022],
        "remove coincident contact faces": [32800, 30087],
        "remove faces enclosed on both sides (default)": [21293, 19394]}
mb = {"keep all faces (generic Extract Surface)": ["56.7 MB", "42.9 MB"],
      "remove coincident contact faces": ["", "3.9 MB"],
      "remove faces enclosed on both sides (default)": ["2.6 MB", "2.4 MB"]}
colors = [ORANGE, AQUA, BLUE]
fig, ax = plt.subplots(figsize=(7.2, 2.9), constrained_layout=True)
h = 0.24
for i, ((label, vals), c) in enumerate(zip(data.items(), colors)):
    ypos = np.arange(len(cases)) + (i - 1) * (h + 0.03)
    ax.barh(ypos, vals, height=h, color=c, label=label)
    for yv, v, s in zip(ypos, vals, mb[label]):
        ax.text(v + 8000, yv, f"{v:,} faces" + (f"  ({s})" if s else ""), va="center", fontsize=7.5, color=INK)
ax.set_yticks(range(len(cases)), cases)
ax.set_xlabel("faces of the published exterior surface")
ax.set_xlim(0, 1.25e6)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1e3:.0f}k"))
ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
ax.invert_yaxis()
ax.legend(frameon=False, fontsize=7.5, loc="lower left", bbox_to_anchor=(0, 1.02), ncol=1)
fig.savefig("/tmp/figs/fig5_internal_faces.png", dpi=300)

# ---- composites of screenshots
def panel(paths, labels, cols, out, crop=None):
    ims = [Image.open(p).convert("RGB") for p in paths]
    if crop:
        ims = [im.crop(crop(im)) for im in ims]
    w = max(i.width for i in ims); hgt = max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    pad = 24
    canvas = Image.new("RGB", (cols * w + (cols + 1) * pad, rows * hgt + (rows + 1) * pad), "white")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    d = ImageDraw.Draw(canvas)
    for k, (im, lab) in enumerate(zip(ims, labels)):
        r, c = divmod(k, cols)
        x, y = pad + c * (w + pad), pad + r * (hgt + pad)
        canvas.paste(im, (x, y))
        d.rectangle([x, y, x + im.width - 1, y + im.height - 1], outline="#c8c6bf", width=2)
        d.text((x + im.width // 2 - 40, y + 18), lab, fill="#0b0b0b", font=font)
    canvas.save(out)
panel(["/tmp/wb_shots/04_fields_drafted.png", "/tmp/wb_shots/08_built_validated.png"], ["(a)", "(b)"], 2,
      "/tmp/figs/fig2_workbench.png")
panel([f"/tmp/figs/case{c}.png" for c in "ABCDEF"], [f"({c})" for c in "abcdef"], 3, "/tmp/figs/fig4_cases.png")
print("ok")
