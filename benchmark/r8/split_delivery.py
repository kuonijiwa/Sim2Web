"""Prepare and verify a Drive delivery with a decimal 9 MB per-file cap."""
import argparse
import hashlib
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


MAX_BYTES = 9_000_000
CHUNK = 8_800_000


def digest(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


parser=argparse.ArgumentParser()
parser.add_argument("bundle",type=Path)
parser.add_argument("destination",type=Path)
args=parser.parse_args()
target=args.destination
target.mkdir(parents=True,exist_ok=True)
bundle=args.bundle
full=digest(bundle)
parts=[]
joined=hashlib.sha256()
with bundle.open("rb") as stream:
    while data:=stream.read(CHUNK):
        part=target/f"{bundle.name}.part{len(parts):02d}"
        part.write_bytes(data)
        parts.append(part)
        joined.update(part.read_bytes())
assert parts and joined.hexdigest()==full
(target/"SHA256SUMS").write_text(f"{full}  {bundle.name}\n"+
    "".join(f"{digest(part)}  {part.name}\n" for part in parts),encoding="ascii")

paper=Path("paper_evidence/revision_v5")
figures=paper/"figures_r7"
for name in ("fig2_workbench.png","fig4_cases.png","contact_sheets_100pct.pdf","print_check.json"):
    original=figures/name
    if original.suffix==".png" and original.stat().st_size>MAX_BYTES:
        from PIL import Image
        with Image.open(original) as image:
            image.convert("RGB").save(target/(original.stem+".jpg"),quality=95,subsampling=0,dpi=(600,600),optimize=True)
    else:
        shutil.copyfile(original,target/name)

evidence=paper/"r8"
for name in ("REPORT_r8.md","fig_multistage.png"):
    shutil.copyfile(evidence/name,target/name)
survey=evidence/"site_survey"
zip_path=target/"site_survey.zip"
with ZipFile(zip_path,"w",ZIP_DEFLATED) as archive:
    for item in sorted(survey.iterdir()):
        if item.is_file():
            archive.write(item,f"site_survey/{item.name}")
with ZipFile(zip_path) as archive:
    assert archive.testzip() is None
assert zip_path.stat().st_size<=MAX_BYTES
for file in sorted(target.iterdir()):
    assert file.stat().st_size<=MAX_BYTES,file
    print(file.name,file.stat().st_size)
