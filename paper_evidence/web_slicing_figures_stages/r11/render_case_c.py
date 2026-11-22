"""Render full and matched detail views of the two archived Case C surfaces."""
import json
import sys
from pathlib import Path

import matplotlib as mpl
import numpy as np
import pyvista as pv
from matplotlib.colors import ListedColormap
from PIL import Image

before, after, output = map(Path, sys.argv[1:4])
output.mkdir(parents=True, exist_ok=True)
index = json.loads((after.parents[1] / "index.json").read_text(encoding="utf-8"))
metadata = index["stages"][0]["fields"]["TotalDisplacement"]
limits = [metadata["p5"], metadata["p95"]]
bands = 8
palette = mpl.colormaps["turbo"](np.linspace(0, 1, bands))[:, :3]
size = 2700, 1650
ratio = size[0] / size[1]
azimuth, elevation, roll = np.deg2rad([298., 31., -30.])
sight = np.array([np.cos(elevation)*np.cos(azimuth), np.cos(elevation)*np.sin(azimuth), np.sin(elevation)])
up = np.array([-np.sin(elevation)*np.cos(azimuth), -np.sin(elevation)*np.sin(azimuth), np.cos(elevation)])
right = np.cross(up, sight)
right, up = right*np.cos(roll)-up*np.sin(roll), right*np.sin(roll)+up*np.cos(roll)
exterior = pv.read(after)
xy = exterior.points @ np.stack([right, up]).T
mins, maxs = np.min(xy, axis=0), np.max(xy, axis=0)
width, height = maxs - mins
scale = max(width/ratio, height) / 1.79
center_u, center_v = (mins + maxs) / 2
center = center_u*right + center_v*up + (np.asarray(exterior.center) @ sight)*sight
window = (0.46, 0.46, 0.76, 0.76)
fraction = window[2] - window[0]
assert np.isclose(fraction, window[3] - window[1])
x = (window[0] + window[2])/2
y = (window[1] + window[3])/2
zoom_center = center + right * (x-.5)*2*scale*ratio + up * (.5-y)*2*scale


def render(surface, file, target, view_scale, wire=False, field=None):
    plot = pv.Plotter(off_screen=True, window_size=size)
    try:
        plot.set_background("white")
        if wire:
            plot.add_mesh(surface, style="wireframe", color="#45494d", line_width=.7,
                          opacity=.46, lighting=False, show_scalar_bar=False)
        else:
            plot.add_mesh(surface, scalars=field, preference="point", cmap=ListedColormap(palette),
                          clim=limits, n_colors=bands, opacity=1, lighting=False,
                          show_scalar_bar=False, interpolate_before_map=True)
        plot.camera_position = (target+1800*sight, target, up)
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = view_scale
        plot.show(screenshot=str(output / file), auto_close=False)
    finally:
        plot.close()


panels = {}
for key, file, data, array, count, size_bytes in (
    ("a", before, pv.read(before), "Displacement_Magnitude", 917062, 187591097),
    ("b", after, exterior, "TotalDisplacement", 21293, 2620417),
):
    assert (data.n_cells, file.stat().st_size) == (count, size_bytes)
    top, bottom = f"surface_{key}.png", f"detail_{key}.png"
    render(data, top, center, scale, field=array)
    render(data, bottom, zoom_center, scale*fraction, wire=True)
    panels[key] = {"surface": top, "detail": bottom, "faces": count, "bytes": size_bytes, "field_array": array}

raw = [np.asarray(Image.open(output / panel["surface"]).convert("RGB")).astype(np.int16) for panel in panels.values()]
occupied = np.any(raw[0] < 248, axis=2) | np.any(raw[1] < 248, axis=2)
difference = np.max(np.abs(raw[0]-raw[1]), axis=2)
check = {
    "renderer": f"PyVista {pv.__version__}", "viewport": size, "camera": [(center+1800*sight).tolist(), center.tolist(), up.tolist()],
    "zoom_focal": zoom_center.tolist(), "parallel_scale": scale, "detail_parallel_scale": scale*fraction,
    "view_angles_deg": [298., 31., -30.], "roi_fraction_xyxy": window, "panels": panels,
    "colormap": "matplotlib turbo", "range": limits, "bands": bands, "band_rgb": palette.tolist(),
    "field": "TotalDisplacement", "unit": "m", "range_mode": "p5_p95",
    "opaque_fraction_pixels_within_20_rgb": float(np.mean(difference[occupied] <= 20)),
    "opaque_mean_max_channel_delta": float(np.mean(difference[occupied])),
    "detail_style": {"color": "#45494d", "width": .7, "opacity": .46, "scalars": None},
}
(output / "fig6.json").write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
print(json.dumps(check))
