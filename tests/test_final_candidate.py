from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pyvista as pv
import pytest

from geosimvis.validation import mesh_summary, section_plane_residual


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
CASES = {
    "flac3d_cavern_iv2": {
        "input": "IV-2.vtu",
        "stage": "IV-2",
        "primary": "cavity_surface.vtp",
    },
    "flac3d_slope_exac23": {
        "input": "exac_23.vtu",
        "stage": "exac_23",
        "primary": "full_model.vtp",
    },
    "3dec_slope": {
        "input": "slopemodel.vtu",
        "stage": "slopemodel",
        "primary": "full_model.vtp",
    },
}


def _vtp_references(value):
    if isinstance(value, str) and value.endswith(".vtp"):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _vtp_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _vtp_references(child)


def _all_text_files():
    extensions = {".py", ".vue", ".js", ".json", ".md", ".html", ".toml"}
    ignored = {"node_modules", ".venv", "dist", "__pycache__", ".pytest_cache"}
    for path in ROOT.rglob("*"):
        if any(part in ignored for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def test_exactly_three_real_3d_cases():
    dirs = sorted(path.name for path in EXAMPLES.iterdir() if path.is_dir())
    assert dirs == sorted(CASES)
    assert not any("2d" in name.lower() for name in dirs)


@pytest.mark.parametrize("case_name", CASES)
def test_representative_vtu_readable(case_name):
    spec = CASES[case_name]
    path = EXAMPLES / case_name / "input" / spec["input"]
    summary = mesh_summary(path)
    assert summary["points"] > 0
    assert summary["cells"] > 0


@pytest.mark.parametrize("case_name", CASES)
def test_processing_script_is_syntactically_executable(case_name):
    script = EXAMPLES / case_name / "processing" / "process.py"
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("case_name", CASES)
def test_manifest_references_existing_vtp(case_name):
    case = EXAMPLES / case_name
    manifest = json.loads((case / "output/model_cache/index.json").read_text(encoding="utf-8"))
    refs = list(_vtp_references(manifest))
    assert refs
    for relative in refs:
        assert not relative.startswith(("/", "\\"))
        assert (case / "output" / relative).is_file(), relative


@pytest.mark.parametrize("case_name", CASES)
def test_primary_output_and_field_associations(case_name):
    spec = CASES[case_name]
    stage_dir = EXAMPLES / case_name / "output/model_cache" / spec["stage"]
    primary = pv.read(stage_dir / spec["primary"])
    assert primary.n_points > 0 and primary.n_cells > 0
    assert any(name.startswith("Stress_") for name in primary.cell_data)
    categorical = [name for name in primary.cell_data if "Material" in name or "Group" in name]
    if case_name != "3dec_slope" or categorical:
        assert categorical
    assert any(name in primary.point_data for name in ("Displacement", "TotalDisplacement"))


@pytest.mark.parametrize("case_name", CASES)
def test_section_plane_residual(case_name):
    section = next((EXAMPLES / case_name / "output/model_cache").rglob("slice_*.vtp"))
    assert section_plane_residual(section) < 1.0e-6


@pytest.mark.parametrize("case_name", CASES)
def test_frontend_source_and_relative_paths(case_name):
    app = EXAMPLES / case_name / "frontend/src/App.vue"
    source = app.read_text(encoding="utf-8")
    assert "model_cache/index.json" in source
    assert "fetch('/model_cache" not in source
    assert "fetch(\"/model_cache" not in source
    assert any(token in source for token in ("CellData", "getCellData", "setScalarModeToUseCellFieldData"))
    assert (app.parents[1] / "vite.config.js").is_file()


def test_3dec_shell_opacity_defaults_to_one():
    source = (EXAMPLES / "3dec_slope/frontend/src/App.vue").read_text(encoding="utf-8")
    assert re.search(r"fullModelOpacity\s*=\s*ref\(1\.0\)", source)


def test_no_private_paths_or_ip_literals():
    drive = re.compile(r"(?i)(?<![A-Za-z])[A-Z]:[\\/]")
    unc = re.compile(r"\\\\[^\\\s]+\\")
    ipv4 = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
    findings = []
    for path in _all_text_files():
        if path == Path(__file__).resolve():
            # This test necessarily contains the detection expressions.
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in (drive, unc, ipv4):
            if pattern.search(text):
                findings.append(str(path.relative_to(ROOT)))
    assert not findings


def test_only_final_stage_names_are_packaged():
    all_names = {path.name for path in EXAMPLES.rglob("*")}
    forbidden = {"I-1", "I-2", "II-1", "II-2", "III-1", "III-2", "III-3"}
    assert not (all_names & forbidden)
    assert not any(re.fullmatch(r"exa?c?_\d+", name) and name != "exac_23" for name in all_names)
