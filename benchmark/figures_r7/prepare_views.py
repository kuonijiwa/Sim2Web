"""Frame the published geometries for Figure 4 without altering the packages."""
import argparse
import json
from itertools import product
from pathlib import Path

import numpy as np
import pyvista as pv
from scipy.spatial import ConvexHull


# These are the field, section, range and layer settings in the previous figure.
STATES = {
    "A": ("Stress_Min_Principal", "p5_p95", "x", 38, {"excavation": 0.35}),
    "B": ("Stress_Max_Principal", "p5_p95", "y", -185, {"exterior": 0.35, "excavation": 0.6}),
    "C": ("TotalDisplacement", "full", "x", 830, {"exterior": 0.35}),
    "D": ("Y_Disp", "p5_p95", None, None, {"excavation": 1}),
    "E": ("Stress_Min_Principal", "p5_p95", "y", 30, {"exterior": 0.35}),
    "F": ("TotalDisplacement", "p5_p95", "y", 370, {"exterior": 0.28}),
}
WIDTH, HEIGHT = 960, 600
MODEL_COL = (8, 714)
OLD_PROBE_CELL = 1160199


def basis(yaw, pitch, roll):
    yaw, pitch, roll = np.deg2rad([yaw, pitch, roll])
    toward = np.array([np.cos(pitch)*np.cos(yaw), np.cos(pitch)*np.sin(yaw), np.sin(pitch)])
    right = np.array([-np.sin(yaw), np.cos(yaw), 0.0])
    up = np.cross(toward, right)
    return toward, np.cos(roll)*right+np.sin(roll)*up, np.cos(roll)*up-np.sin(roll)*right


def frame(points, panel):
    points = points[ConvexHull(points).vertices]
    top = 146 if panel == "A" else 9
    bottom = 591
    u, v = MODEL_COL
    base_pitch = 58 if panel != "D" else 62
    pitches = (48, 54, 58, 61, 65, 69, 73, 78, 83) if panel == "D" else (22, 32, 41, 48, 54, 58, 62, 69, 77)
    choices = []
    for dyaw, pitch, roll in product(range(-165, 181, 15), pitches, range(-75, 76, 5)):
        toward, right, up = basis(225+dyaw, pitch, roll)
        q = points @ np.column_stack((right, up))
        span = np.ptp(q, axis=0)
        px_per_m = min((v-u)/span[0], (bottom-top)/span[1])
        coverage = px_per_m*span[0]/WIDTH
        default_shift = abs(dyaw)*0.7 + abs(pitch-base_pitch)*1.3 + abs(roll)*1.3
        # Width takes precedence, then minimize changes from the default three-quarter view.
        score = max(0, 0.73-coverage)*20000 + default_shift
        choices.append((score, coverage, pitch, roll, dyaw, toward, right, up, q, px_per_m))
    _, coverage, pitch, roll, dyaw, toward, right, up, q, scale = min(choices, key=lambda item: item[0])
    centre = (points.min(0)+points.max(0))/2
    middle = (q.min(0)+q.max(0))/2
    focal_r = middle[0]-(u+v-WIDTH)/2/scale
    focal_u = middle[1]+(top+bottom-HEIGHT)/2/scale
    focal = focal_r*right+focal_u*up+(centre@toward)*toward
    eye = focal+toward*np.linalg.norm(np.ptp(points, axis=0))*3
    return {
        "camera": [*eye, *focal, *up, (HEIGHT/2)/scale],
        "angles_deg": [225+dyaw, pitch, roll], "projected_model_width_fraction": coverage,
        "right": right, "up": up, "focal": focal, "px_per_m": scale,
    }


parser = argparse.ArgumentParser()
parser.add_argument("model_runs", type=Path)
parser.add_argument("scratch", type=Path)
args = parser.parse_args()
views = {}
for panel, (field, mode, axis, pos, visible) in STATES.items():
    site = args.model_runs / panel / "site"
    index = json.loads((site / "model_cache/index.json").read_text(encoding="utf-8"))
    stage = index["stages"][0]
    assert field in index["fields"] and index["viewer"]["background"] == [1, 1, 1]
    layers = stage["layers"]
    assert visible.keys() <= {layer["id"] for layer in layers}
    meshes = [pv.read(site/layer["file"]) for layer in layers if layer["id"] in visible]
    section = None
    if axis:
        section = next(sec for sec in stage["sections"][axis] if sec["value"] == pos)
        meshes.append(pv.read(site/section["file"]))
    points = np.concatenate([mesh.points for mesh in meshes]).astype(np.float64)
    fitted = frame(points, panel)
    if fitted["projected_model_width_fraction"] < 0.70:
        raise RuntimeError(f"{panel}: best width only {fitted['projected_model_width_fraction']:.3f}")
    views[panel] = {
        "site": str(site), "field": field, "axis": axis, "position_m": pos, "range": mode,
        "layers": [f"{l['id']}:{int(l['id'] in visible)}:{visible.get(l['id'], 1)}" for l in layers],
        **{k: fitted[k] for k in ("camera", "angles_deg", "projected_model_width_fraction")},
    }
    if panel == "A":
        mesh = meshes[-1]
        ids = np.flatnonzero(mesh.cell_data["Source_Cell_ID"] == OLD_PROBE_CELL)
        assert len(ids), "The previous Figure 4 point is missing from the current A section"
        targets = [mesh.get_cell(int(i)).points.mean(0) for i in ids]
        views[panel]["probe_cell_id"] = OLD_PROBE_CELL
        views[panel]["probe_targets"] = []
        views[panel]["probe_projection"] = {
            "right": list(fitted["right"]), "up": list(fitted["up"]), "px_per_m": fitted["px_per_m"],
        }
        for centre in targets:
            delta = centre-fitted["focal"]
            px = WIDTH/2 + delta@fitted["right"]*fitted["px_per_m"]
            py = HEIGHT/2 - delta@fitted["up"]*fitted["px_per_m"]
            views[panel]["probe_targets"].append({"canvas": [px/WIDTH, py/HEIGHT], "world": list(centre)})
    print(f"{panel}: projected model takes {fitted['projected_model_width_fraction']:.2%} of panel width")
(args.scratch/"view_states_local.json").write_text(json.dumps(views, indent=2)+"\n", encoding="utf-8")
