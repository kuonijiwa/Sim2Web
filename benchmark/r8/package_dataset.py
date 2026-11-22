"""Prepare reproducible local example-input archives and a Zenodo draft."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import yaml


EXAMPLES = {"A":"flac3d_cavern_iv2", "B":"flac3d_slope_exac23", "C":"3dec_slope", "D":"flac3d_pit_case4",
            "E":"ogs_slope", "F":"3dec_slope_case_f", "STAGES":"flac3d_cavern_stages"}
CREATORS = ["Cheng, Yongjin", "Chu, Weijiang", "Xie, Liangfu", "Meng, Qingxiang", "Yang, Shu", "Yu, Jiabao"]


def archive_case(source, target):
    config = source/"sim2web.yaml"
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    members = {"case.yaml":config}
    for stage in data["input"]["stages"]:
        name = PurePosixPath(stage["file"])
        assert name.parts[0] == "input" and ".." not in name.parts, name
        members[name.as_posix()] = source.joinpath(*name.parts)
    with ZipFile(target,"w",compression=ZIP_DEFLATED,compresslevel=6) as archive:
        for name, location in members.items():
            info = ZipInfo(name)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with archive.open(info,"w",force_zip64=True) as dest, location.open("rb") as original:
                shutil.copyfileobj(original,dest,length=1024*1024)
        readme = (f"# {data['title']}\n\n{data.get('description','')}\n\n"
                  "These VTUs and the case configuration are prepared for CC BY 4.0.\n\n"
                  "```sh\nsim2web build case.yaml\nsim2web validate case.yaml\nsim2web serve site\n```\n")
        info = ZipInfo("README.md")
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info,readme)
    with ZipFile(target) as archive:
        assert archive.namelist() == [*members,"README.md"] and archive.testzip() is None, target
    with target.open("rb") as stream:
        sha256 = hashlib.file_digest(stream,"sha256").hexdigest()
    return {"example":source.name, "archive":target.name, "members":[*members,"README.md"], "bytes":target.stat().st_size,
            "sha256":sha256, "url":f"https://zenodo.org/records/RECORD_ID/files/{target.name}?download=1"}


parser = argparse.ArgumentParser()
parser.add_argument("examples",type=Path)
parser.add_argument("output",type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
records = {}
for case, name in EXAMPLES.items():
    source = args.examples/name
    assert (source/"README.md").is_file(), source
    records[case]=archive_case(source,args.output/f"Sim2Web_case_{case}.zip")
    print(case,records[case]["bytes"],records[case]["sha256"],flush=True)
(args.output/"SHA256SUMS").write_text("".join(f"{x['sha256']}  {x['archive']}\n" for x in records.values()),encoding="ascii")
(args.output/"README.md").write_text("# Sim2Web example input data\n\n"
    "Each archive contains the input VTU file or files, a `case.yaml` and a README. "
    "Build and validate after extraction with `sim2web build case.yaml` and `sim2web validate case.yaml`. "
    "Use `SHA256SUMS` to verify the archives. The dataset is prepared for release under CC BY 4.0.\n",encoding="utf-8")
metadata={"title":"Sim2Web example simulation datasets", "upload_type":"dataset", "license":"cc-by-4.0",
          "creators":[{"name":n} for n in CREATORS],
          "description":"Input VTUs and reproducible configurations for Cases A–F and the five-stage FLAC3D underground cavern example."}
(args.output/".zenodo.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
manifest={"schema":"sim2web-example-data/1","status":"Draft URLs. Replace RECORD_ID after dataset publication.","cases":records}
(args.examples/"DATA_SOURCES.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
