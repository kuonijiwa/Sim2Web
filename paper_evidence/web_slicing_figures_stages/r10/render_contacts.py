"""Render the measured Case C exterior products with one camera and cut plane."""
import json
import sys
from pathlib import Path

from matplotlib.colors import ListedColormap
import pyvista as pv

before, after, viewer_records, output = map(Path, sys.argv[1:5])
output.mkdir(parents=True, exist_ok=True)
reference = json.loads(viewer_records.read_text(encoding="utf-8"))["C"]
colouring = reference["state"]["coloring"]
index = json.loads((after.parents[1] / "index.json").read_text(encoding="utf-8"))
field_stats = index["stages"][0]["fields"]["TotalDisplacement"]
clim = [field_stats["p5"], field_stats["p95"]]
step = (clim[1] - clim[0]) / colouring["bands"]
legend = [{"color": row["color"], "from": clim[0] + i*step, "to": clim[0] + (i+1)*step}
          for i, row in enumerate(reference["legend"])]
palette = ListedColormap([row["color"] for row in legend])
camera = [(1450., -720., 2740.), (840., 423., 2070.), (0., 0., 1.)]
cut = 375.0
results = {}
for label, path, field, cells, expected_bytes in (
    ("a", before, "Displacement_Magnitude", 917062, 187591097),
    ("b", after, "TotalDisplacement", 21293, 2620417),
):
    surface = pv.read(path)
    assert surface.n_cells == cells and path.stat().st_size == expected_bytes
    clipped = surface.clip(normal=(0, 1, 0), origin=(0, cut, 0), invert=False)
    plot = pv.Plotter(off_screen=True, window_size=(2460, 1810))
    try:
        plot.set_background("white")
        plot.add_mesh(clipped, scalars=field, preference="point", cmap=palette, clim=clim, n_colors=len(legend),
                      show_scalar_bar=False, show_edges=True, edge_color="#37454c", line_width=.65, opacity=.62,
                      lighting=False, interpolate_before_map=True)
        plot.camera_position = camera
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = 411
        plot.show(screenshot=str(output/f"contacts_{label}.png"), auto_close=False)
    finally:
        plot.close()
    results[label] = {"faces": cells, "bytes": expected_bytes, "field_array": field,
                      "file": f"contacts_{label}.png", "cut_cells": clipped.n_cells}
check = {"field": "TotalDisplacement", "unit": "m", "camera": camera, "parallel_scale": 411,
         "range": clim, "range_mode": "p5_p95", "colormap": colouring["colormap"],
         "bands": colouring["bands"], "legend": legend,
         "cut": {"axis": "y", "position_m": cut, "keep": "y >= 375 m"},
         "panels": results, "opacity": .62, "renderer": f"PyVista {pv.__version__}"}
(output/"fig6_render.json").write_text(json.dumps(check, indent=2)+"\n", encoding="utf-8")
print(json.dumps(check))
