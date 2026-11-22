"""Compare final section silhouettes in a shared area clear of view controls."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def silhouette(path):
    with Image.open(path) as image:
        assert image.size == (1600, 900), (path, image.size)
        pixels = np.asarray(image.convert("RGB"))[:, 410:1180].astype(np.int16)
    return (pixels.max(2) - pixels.min(2) > 80) & (pixels.min(2) < 70)


def bounds(mask):
    y, x = np.nonzero(mask)
    return [int(x.min()) + 410, int(y.min()), int(x.max()) + 410, int(y.max())]


parser = argparse.ArgumentParser()
parser.add_argument("scratch", type=Path)
args = parser.parse_args()
result = {"window_pixels": [1600, 900], "crop_x_pixels": [410, 1180], "section_index": 9, "cases": {}}
for case in ("A", "C"):
    case_data = result["cases"].setdefault(case, {})
    model = json.loads((args.scratch / f"data_{case}/case.json").read_text(encoding="utf-8"))
    case_data["x_m"] = model["positions"][9]
    for network in ("LAN", "4G"):
        net_data = case_data.setdefault(network, {})
        def capture(method):
            return args.scratch / f"trial_{case}_{method}_{network}/section_1600x900.png"

        reference = silhouette(capture("B"))
        for method in ("B", "S-local", "S-remote", "W"):
            mask = silhouette(capture(method))
            intersection = np.count_nonzero(reference & mask)
            union = np.count_nonzero(reference | mask)
            iou = intersection / union
            net_data[method] = {"bounds_px": bounds(mask), "pixels": int(mask.sum()), "iou_against_B": iou}
            assert iou >= 0.97, (case, network, method, iou)

result["passed"] = True
data = json.dumps(result, indent=2) + "\n"
(args.scratch / "frame_check.json").write_text(data, encoding="utf-8")
print(data, end="")
