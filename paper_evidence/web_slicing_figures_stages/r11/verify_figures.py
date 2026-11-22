"""Check r11 deliverables before generating the report and publishing."""
import hashlib
import json
import math
import sys
from pathlib import Path

from PIL import Image
from pypdf import PdfReader


directory = Path(sys.argv[1])
rows = json.loads((directory/"print_check.json").read_text(encoding="utf-8"))["figures"]
assert list(rows) == list("234567")
for key, row in rows.items():
    source = directory/row["file"]
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == row["sha256"]
    assert len(data) == row["bytes"] <= 9_000_000
    with Image.open(source) as image:
        assert image.mode == "RGB" and list(image.size) == row["pixels"]
        assert all(math.isclose(v,600,abs_tol=.01) for v in image.info["dpi"])
        assert math.isclose(image.width * 2.54 / 600, 16.5, abs_tol=.012)
        image.verify()
    for panel in row["panels"].values():
        assert panel["effective_dpi"] >= 600
        color = panel["legend"]
        if color:
            assert "turbo" in color["cmap"].lower(), color
            assert color["range"][0] < color["range"][1], color
            if key != "5":
                assert color["bands"] == 8
    print(f"Fig {key}: RGB, {row['pixels']}, {row['bytes']:,} bytes, individual DPI OK")
assert rows["2"]["panels"]["a_steps"]["font_pt"] >= 6
assert rows["2"]["panels"]["a_diagnostics"]["font_pt"] >= 5
assert rows["3"]["viewport"] == {"width":1600, "height":900}
assert not rows["3"]["css"]
assert rows["3"]["probe"]["isSection"]
assert [p["faces"] for p in rows["7"]["panels"].values()] == [20142,27837,49677]
page, = PdfReader(str(directory/"fig5_principal_stress.pdf")).pages
assert math.isclose(float(page.mediabox.width)*2.54/72,16.5,abs_tol=.01)
assert not page.images
fonts = [str(ref.get_object()["/BaseFont"]) for ref in page["/Resources"]["/Font"].values()]
assert all("Arial" in font for font in fonts)
print("Fig 5 PDF: one 16.5 cm-wide vector page, Arial, zero embedded raster images")
