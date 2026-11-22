import numpy as np, pyvista as pv, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFont
from sim2web.fields import principal_values
import vtk

INK, INK2, GRID = "#0b0b0b", "#52514e", "#dcdad4"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,"pdf.fonttype": 42,"ps.fonttype": 42,"svg.fonttype":"none", "axes.edgecolor": INK2, "axes.labelcolor": INK,
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
fig, axes = plt.subplots(1, 3, figsize=(6.5, 2.65), constrained_layout=True)
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
        ax.axhspan(0, hi, color="#FDF3EF", lw=0, zorder=0)
        txt += f"\n{false_t:,} cells tensile\nonly in generic result"
    ax.text(0.97, 0.04, txt, transform=ax.transAxes, va="bottom", ha="right", fontsize=7.2, color=INK,
            bbox=dict(facecolor="white", edgecolor=GRID, boxstyle="round,pad=0.3"))
axes[0].set_ylabel("generic filter, VTK order (MPa)")
fig.supxlabel("principal stress from the component order declared in the file, XX,YY,ZZ,XY,XZ,YZ (MPa)", fontsize=9, color=INK)
cb = fig.colorbar(hb, ax=axes, shrink=0.8, pad=0.01); cb.set_label("cells per bin", color=INK2, fontsize=8)
for ext in ("pdf","eps","svg"): fig.savefig(f"/tmp/figs/print/fig3_principal_caseA.{ext}")
fig.savefig("/tmp/figs/print/fig3_principal_caseA.tif", dpi=600, pil_kwargs={"compression":"tiff_lzw"})
fig.savefig("/tmp/figs/print/fig3_principal_caseA.png", dpi=600)
fig3=fig

# ---- Figure 5: exterior faces published, by internal-face handling
cases = ["Case C (3DEC, 97 MB)", "Case F (3DEC, 75 MB)"]
data = {"keep all faces (generic Extract Surface)": [917062, 693022],
        "remove coincident contact faces": [32800, 30087],
        "remove faces enclosed on both sides (default)": [21293, 19394]}
mb = {"keep all faces (generic Extract Surface)": ["56.7 MB", "42.9 MB"],
      "remove coincident contact faces": ["", "3.9 MB"],
      "remove faces enclosed on both sides (default)": ["2.6 MB", "2.4 MB"]}
colors = [ORANGE, AQUA, BLUE]
fig, ax = plt.subplots(figsize=(6.5, 2.65), constrained_layout=True)
h = 0.24
for i, ((label, vals), c) in enumerate(zip(data.items(), colors)):
    ypos = np.arange(len(cases)) + (i - 1) * (h + 0.03)
    ax.barh(ypos, vals, height=h, color=c, label=label)
    for yv, v, s in zip(ypos, vals, mb[label]):
        ax.text(v + 10000, yv, f"{v:,} faces" + (f"  ({s})" if s else ""), va="center", fontsize=7.2, color=INK)
ax.set_yticks(range(len(cases)), cases)
ax.set_xlabel("faces of the published exterior surface")
ax.set_xlim(0, 1.25e6)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1e3:.0f}k"))
ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)
ax.invert_yaxis()
ax.legend(frameon=False, fontsize=7.2, loc="lower left", bbox_to_anchor=(0, 1.02), ncol=1)
for ext in ("pdf","eps","svg"): fig.savefig(f"/tmp/figs/print/fig5_internal_faces.{ext}")
fig.savefig("/tmp/figs/print/fig5_internal_faces.tif", dpi=1000, pil_kwargs={"compression":"tiff_lzw"})
fig.savefig("/tmp/figs/print/fig5_internal_faces.png", dpi=1000)


import json
from matplotlib.text import Text
out={}
for name,f in (("fig3",fig3),("fig5",fig)):
    w,h=f.get_size_inches(); sizes=[t.get_fontsize() for t in f.findobj(Text) if t.get_text().strip()]
    out[name]={"width_cm":round(w*2.54,2),"height_cm":round(h*2.54,2),"min_font_pt":min(sizes)}
print(json.dumps(out))
json.dump(out,open("/tmp/figs/print/print_check_fig3_fig5.json","w"),indent=1)
