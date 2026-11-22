"""Download and verify a Sim2Web example archive from its Zenodo record."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import urlopen
from zipfile import ZipFile


def fetch(case, destination, source):
    info = source["cases"][case]
    url = info["url"]
    if "RECORD_ID" in url:
        raise ValueError(f"Case {case} has a placeholder URL. Set the published Zenodo record in the manifest first.")
    if urlparse(url).scheme != "https":
        raise ValueError("Example archives require an HTTPS URL")
    name = info["example"]
    if not name or name in {".", ".."} or name != Path(name).name or ":" in name:
        raise ValueError("Invalid destination name in the manifest")
    target = destination / name
    if target.exists():
        raise FileExistsError(f"Choose an output directory without {target.name}: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sim2web-", dir=destination) as scratch:
        scratch = Path(scratch)
        archive_path = scratch / "download.zip"
        with urlopen(url, timeout=60) as response, archive_path.open("wb") as local:
            if urlparse(response.geturl()).scheme != "https":
                raise ValueError("Example archive redirected away from HTTPS")
            shutil.copyfileobj(response, local, length=1024*1024)
        with archive_path.open("rb") as local:
            digest = hashlib.file_digest(local, "sha256").hexdigest()
        if digest != info["sha256"] or archive_path.stat().st_size != info["bytes"]:
            raise ValueError(f"Example archive failed the SHA-256 or size check: {case}")
        unpacked = scratch / "example"
        with ZipFile(archive_path) as archive:
            entries = archive.namelist()
            if len(entries) != len(set(entries)) or set(entries) != set(info["members"]):
                raise ValueError("The ZIP contents do not match the manifest")
            for name in entries:
                relative = PurePosixPath(name)
                if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
                    raise ValueError(f"Unsafe ZIP member: {name}")
                output = unpacked.joinpath(*relative.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source_file, output.open("wb") as output_file:
                    shutil.copyfileobj(source_file, output_file)
        unpacked.rename(target)
    return target


def main():
    default = Path(__file__).resolve().parents[1] / "examples/DATA_SOURCES.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", help="case letter (A to F) or STAGES")
    parser.add_argument("--manifest", type=Path, default=default)
    parser.add_argument("--output-dir", type=Path, default=Path("downloaded_examples"))
    args = parser.parse_args()
    try:
        source = json.loads(args.manifest.read_text(encoding="utf-8"))
        path = fetch(args.case.upper(), args.output_dir, source)
    except (KeyError, ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")
    print(path)


if __name__ == "__main__":
    main()
