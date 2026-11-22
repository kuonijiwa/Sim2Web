"""Checks on the published cavern, slope, and excavation pit models.

These tests need the Git LFS models (``git lfs pull``) and take a few minutes.
They are skipped when only LFS pointer files are present or when
``SIM2WEB_REALDATA`` is not set::

    SIM2WEB_REALDATA=1 pytest -m realdata
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

from sim2web.config import load_config
from sim2web.pipeline import build
from sim2web.validate import validate_package

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "A": "flac3d_cavern_iv2",
    "B": "flac3d_slope_exac23",
    "C": "3dec_slope",
    "D": "flac3d_pit_case4",
    "F": "3dec_slope_case_f",
}

# Settings that restore the v0.1 behaviour, so that products can be compared
# byte for byte with the published v0.1 hash records.  v0.1 read the FLAC3D
# shear components in the order XY,YZ,XZ although the files declare XY,XZ,YZ.
V01_COMMON = ["sections.magnitude=interpolated", "geometry.exterior.internal_faces=keep",
              "sections.preserve_discontinuities=false"]
V01 = {
    "A": V01_COMMON + ["fields.stress.order=XX,YY,ZZ,XY,YZ,XZ", "fields.stress.check_file_order=false"],
    "B": V01_COMMON + ["fields.stress.order=XX,YY,ZZ,XY,YZ,XZ", "fields.stress.check_file_order=false"],
    "C": V01_COMMON,
}
LEGACY_NAME = {"excavation": "cavity_surface.vtp", "exterior": "full_model.vtp"}


def _has_model(case):
    vtu = next((ROOT / "examples" / CASES[case] / "input").glob("*.vtu"), None)
    return vtu is not None and vtu.stat().st_size > 10_000


def _ulp_only_difference(new_path: Path, old_path: Path) -> str | None:
    """None if two VTPs differ only by <= 1 Float32 ULP in principal stresses.

    Eigenvalues are computed by LAPACK, whose CPU-specific kernels may round a
    value that lies on a Float32 rounding midpoint differently.  Everything
    else must be identical.
    """
    a, b = pv.read(new_path), pv.read(old_path)
    if a.n_points != b.n_points or a.n_cells != b.n_cells or not np.array_equal(a.points, b.points) \
            or not np.array_equal(a.faces, b.faces):
        return "geometry differs"
    for kind in ("point_data", "cell_data"):
        ca, cb = getattr(a, kind), getattr(b, kind)
        if list(ca.keys()) != list(cb.keys()):
            return f"{kind} names differ"
        for name in ca.keys():
            x, y = np.asarray(ca[name]), np.asarray(cb[name])
            if x.dtype != y.dtype:
                return f"{name} dtype differs"
            if x.dtype.kind in "USO":
                if not np.array_equal(x.astype(str), y.astype(str)):
                    return f"{name} differs"
                continue
            if np.array_equal(x, y):
                continue
            if not name.endswith("_Principal") or x.dtype != np.float32:
                return f"{name} differs"
            ulps = np.abs(x.view(np.int32).astype(np.int64) - y.view(np.int32).astype(np.int64))
            if ulps.max() > 1:
                return f"{name} differs by {int(ulps.max())} ULP"
    return None


pytestmark = [pytest.mark.realdata, pytest.mark.slow,
              pytest.mark.skipif(not (os.environ.get("SIM2WEB_REALDATA") or os.environ.get("SIMWEBVIEW_REALDATA")), reason="set SIM2WEB_REALDATA=1")]


@pytest.mark.parametrize("case", sorted(V01))
def test_v01_products_are_reproduced(case, tmp_path):
    """All v0.1 products byte for byte, or differing only by 1 ULP in principal stresses."""
    if not _has_model(case):
        pytest.skip("Git LFS model not present")
    cfg = load_config(ROOT / "examples" / CASES[case] / "sim2web.yaml",
                      V01[case] + [f"output.dir={tmp_path.as_posix()}", "output.viewer=false"])
    build(cfg, quality=False, log=lambda *_: None)
    record = json.loads((ROOT / "tests" / "data" / "v01_hashes" / f"hashes_{case}.json").read_text())
    stage = json.loads((cfg.cache_dir / "index.json").read_text())["stages"][0]
    produced = {f"{stage['id']}/{LEGACY_NAME[l['kind']]}": l["file"] for l in stage["layers"]}
    legacy_sections = [k for k in record if "/slice_" in k]
    for axis, entries in stage["sections"].items():
        for e in entries:
            match = [k for k in legacy_sections if k.split("/slice_")[1].startswith(f"{axis}_")
                     and abs(float(k.rsplit("_", 1)[1][:-4]) - e["value"]) < 5e-3]
            assert len(match) == 1, (axis, e["value"])
            produced[match[0]] = e["file"]
    assert set(produced) == {k for k in record if k.endswith(".vtp")}
    reference_dir = ROOT / "examples" / CASES[case] / "output" / "model_cache"
    mismatches = {}
    for legacy, rel in produced.items():
        new = cfg.cache_dir.parent / rel
        digest = hashlib.sha256(new.read_bytes()).hexdigest()
        if digest == record[legacy]:
            continue
        old = reference_dir / legacy
        if old.exists() and old.stat().st_size > 10_000 and \
                hashlib.sha256(old.read_bytes()).hexdigest() == record[legacy]:
            reason = _ulp_only_difference(new, old)
            if reason is None:
                continue  # 1-ULP rounding of an eigenvalue; recorded by the evidence scripts
        else:
            reason = "hash differs (v0.1 reference VTP not available for value comparison)"
        mismatches[legacy] = {"expected": record[legacy], "actual": digest, "reason": reason}
    assert not mismatches, mismatches
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.mark.parametrize("case", sorted(CASES))
def test_current_configuration_validates(case, tmp_path):
    if not _has_model(case):
        pytest.skip("Git LFS model not present")
    cfg = load_config(ROOT / "examples" / CASES[case] / "sim2web.yaml",
                      [f"output.dir={tmp_path.as_posix()}", "output.viewer=false"])
    build(cfg, quality=False, log=lambda *_: None)
    report = validate_package(cfg, sections=5, log=lambda *_: None)
    assert report["failures"] == []
