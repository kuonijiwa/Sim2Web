"""Create the 600 dpi publication PNG with one shared colour legend."""
import argparse
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


parser = argparse.ArgumentParser()
parser.add_argument("captures",type=Path)
parser.add_argument("figure",type=Path)
parser.add_argument("checks",type=Path)
args = parser.parse_args()
meta = json.loads((args.captures/"capture.json").read_text(encoding="utf-8"))
px_per_cm = 600/2.54
width = 16.5
gap = 0.2
panel_width = (width-2*gap)/3
labels_h = 12.2/72*2.54
images = [Image.open(args.captures/info["file"]).convert("RGB") for info in meta["panels"].values()]
assert all(im.size == images[0].size for im in images)
panel_height = panel_width*images[0].height/images[0].width
legend = Image.open(args.captures/meta["legend"]["file"]).convert("RGB")
legend_height = width*legend.height/legend.width
height = labels_h+panel_height+gap+legend_height
dims = (math.ceil(width*px_per_cm),math.ceil(height*px_per_cm))
master = Image.new("RGB",dims,"white")
draw = ImageDraw.Draw(master)
font = ImageFont.truetype(str(Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts/arialbd.ttf"),75)
yp = round(labels_h*px_per_cm)
legend_y = round((labels_h+panel_height+gap)*px_per_cm)
checks = {"width_cm":width,"height_cm":height,"gap_cm":gap,"panel_label_pt":9,"capture_state":{
    "stages":meta["stages"],"field":meta["field"],"limits":meta["limits"],
    "limits_method":meta["limits_method"],"common_camera":meta["camera"]},"panels":{}}
for n,(stage,img) in enumerate(zip(meta["stages"],images)):
    x=n*(panel_width+gap)
    left=round(x*px_per_cm)
    right=round((x+panel_width)*px_per_cm)
    image_height=round((labels_h+panel_height)*px_per_cm)-yp
    draw.text((left,yp-14),f"({chr(97+n)}) {stage}",fill="#1c2630",font=font,anchor="ls")
    master.paste(img.resize((right-left,image_height),Image.Resampling.LANCZOS),(left,yp))
    dpi=img.width*2.54/panel_width
    assert dpi>=600
    checks["panels"][stage]={"capture_pixels":list(img.size),"width_cm":panel_width,"effective_dpi":dpi}
master.paste(legend.resize((dims[0],dims[1]-legend_y),Image.Resampling.LANCZOS),(0,legend_y))
glyph_height = min(x["inkHeightCssPx"] for x in meta["legend"]["text"])
pt = glyph_height*(72/2.54)*width/(legend.width/meta["legend"]["dsf"])
assert pt>=6,pt
checks.update(legend_min_text_pt=pt, legend_capture_pixels=list(legend.size),model_css=meta["modelCss"],legend_css=meta["legendCss"])
master.save(args.figure,dpi=(600,600),optimize=True)
args.checks.write_text(json.dumps(checks,indent=2)+"\n",encoding="utf-8")
print(dims, f"{width} x {height:.3f} cm", f"Shared legend minimum {pt:.3f} pt", args.figure.stat().st_size, "bytes")
