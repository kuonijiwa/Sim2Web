"""Reproduce Figure 5 from the published Case A VTU."""
import json
import os
import sys
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.ticker import MaxNLocator
import numpy as np
import pyvista as pv
import vtk

from sim2web.fields import principal_values

source, output = map(Path, sys.argv[1:3])
output.mkdir(parents=True, exist_ok=True)
for name in ("arial.ttf", "arialbd.ttf"):
    font_manager.fontManager.addfont(Path(os.environ["WINDIR"]) / "Fonts" / name)
mpl.rcParams.update({"font.family": "Arial", "font.size": 7, "pdf.fonttype": 42,
                     "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7})
mesh = pv.read(source)
stress = np.asarray(mesh.cell_data["Stress"], dtype=np.float64)
keep = np.abs(stress).max(axis=1) > 1e-8
filt = vtk.vtkTensorPrincipalInvariants()
filt.SetInputData(mesh)
filt.Update()
vtk_data = pv.wrap(filt.GetOutput()).cell_data
generic = np.sort(np.column_stack([vtk_data[f"Stress - Sigma {k}"] for k in (1, 2, 3)]), axis=1)[keep]
order = ["XX", "YY", "ZZ", "XY", "XZ", "YZ"]
declared = principal_values(stress, order)[keep]

width, height = 16.5, 6.85
fig = plt.figure(figsize=(width / 2.54, height / 2.54))
cmap = LinearSegmentedColormap.from_list("density", ["#e1edf9", "#447bb6", "#0b2c53"])
histograms = []
panels = []
for i, (k, title) in enumerate(zip((2, 1, 0), ("σ1 maximum", "σ2 intermediate", "σ3 minimum"))):
    x_pos = .083 + .276 * i
    ax = fig.add_axes([x_pos, .215, .225, .65])
    x, y = declared[:, k], generic[:, k]
    lo, hi = min(x.min(), y.min()), max(x.max(), y.max())
    if k == 2:
        ax.axhspan(0, hi, facecolor="#f9efea", zorder=0)
    histograms.append(ax.hexbin(x, y, gridsize=70, extent=(lo, hi, lo, hi),
                                mincnt=1, linewidths=0, cmap=cmap, norm=LogNorm()))
    ax.plot([lo, hi], [lo, hi], "--", color="#455666", lw=.7)
    ax.set(xlim=(lo, hi), ylim=(lo, hi))
    ax.set_aspect("equal")
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.grid(alpha=.18, linewidth=.35)
    err = float(np.max(np.abs(x-y)))
    range_error = 100 * err / np.ptp(x)
    mismatch = int(np.count_nonzero((y > 0) & (x <= 0)))
    annotation = f"Max |Δ| {err:.2f} MPa\n{range_error:.1f}% of range"
    if k == 2:
        annotation += f"\n{mismatch:,} tensile only\nin generic result"
    ax.text(.96, .035, annotation, transform=ax.transAxes, ha="right", va="bottom", fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "#d9e0e5", "pad": 2.8})
    fig.text(x_pos, .884, f"({chr(97+i)})", fontsize=9, fontweight="bold")
    fig.text(x_pos + .047, .884, title, fontsize=7.5)
    panels.append({"label": title, "maximum_error_MPa": err, "pct_range": float(range_error),
                   "tensile_only_generic": mismatch, "stress_range_MPa": [float(lo), float(hi)]})

max_bin = int(max(h.get_array().max() for h in histograms))
for hist in histograms:
    hist.set_norm(LogNorm(vmin=1, vmax=max_bin))
cb = fig.colorbar(histograms[0], cax=fig.add_axes([.876, .275, .021, .54]),
                  ticks=[v for v in (1, 10, 100, 1000, 10000, 100000) if v <= max_bin])
cb.ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda value, _: f"{value:,.0f}"))
cb.ax.tick_params(labelsize=7)
cb.solids.set_rasterized(False)
cb.set_label("Cells per bin", size=8)
fig.text(.024, .55, "Generic filter (MPa)", va="center", ha="center", rotation=90, fontsize=8)
fig.text(.474, .09, "Principal stress using the declared order (MPa)", ha="center", fontsize=8)
fig.savefig(output / "fig5_principal_stress.pdf")
fig.savefig(output / "fig5_principal_stress.png", dpi=600, facecolor="white")
check = {"width_cm": width, "height_cm": height, "min_font_pt": 7, "case": "A",
         "kept_cells": int(keep.sum()), "order": order, "panels": panels, "bin_colour_range": [1, max_bin]}
(output / "fig5_plot.json").write_text(json.dumps(check, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps(check, ensure_ascii=False))
