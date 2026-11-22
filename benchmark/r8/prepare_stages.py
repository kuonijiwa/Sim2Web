"""Prepare the multi-stage example from user-supplied VTUs and the published order."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

import yaml


parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("published_index", type=Path)
parser.add_argument("base_config", type=Path)
parser.add_argument("example", type=Path)
args = parser.parse_args()
published = json.loads(args.published_index.read_text(encoding="utf-8-sig"))
assert len(published) == 5, "Expected the five published cavern stages"
inputs = args.example / "input"
inputs.mkdir(parents=True, exist_ok=True)
config = yaml.safe_load(args.base_config.read_text(encoding="utf-8"))
config.update(title="FLAC3D underground cavern: five construction stages",
              description="Construction sequence for the underground cavern, showing the excavation boundary and common section planes.")
stages = []
planes = {}
for stage, entry in published.items():
    assert re.fullmatch(r"[IV]+-\d+", stage), stage
    base = f"{stage}.vtu"
    source = args.source / base
    assert source.is_file() and source.stat().st_size > 10_000, source
    dest = inputs / base
    if not dest.exists():
        shutil.copy2(source, dest)
    with source.open("rb") as sf, dest.open("rb") as df:
        source_digest = hashlib.file_digest(sf, "sha256").hexdigest()
        assert source_digest == hashlib.file_digest(df, "sha256").hexdigest(), base
    stages.append({"file": f"input/{base}", "name": stage, "label": stage})
    stage_planes = {axis:[float(Path(name).stem.split("_")[-1]) for name in slices]
                    for axis, slices in entry["slices"].items()}
    if not planes:
        planes = stage_planes
    assert stage_planes == planes, f"The published section plans differ for {stage}"
    print(stage, source.stat().st_size, source_digest)
config["input"]["stages"] = stages
config["sections"].update(placement="explicit", positions=planes)
config["viewer"].update(subtitle="Excavation surfaces and common section planes", default_axis="x")
(args.example / "sim2web.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
print("Published-order sections:", {axis:len(positions) for axis, positions in planes.items()})
