import json
from pathlib import Path
import numpy as np
import pyvista as pv
from geosimvis.field_contract import attach_source_ids, prepare_output, public_field

ROOT = Path(__file__).resolve().parents[1]


def test_provenance_and_category_output_contract():
    mesh = pv.Plane(i_resolution=1, j_resolution=1)
    attach_source_ids(mesh)
    mesh.point_data["Group_ID"] = np.array([0, 0.5, 0.5, 1])
    mesh.point_data["Stress_XX"] = np.ones(4)
    mesh.cell_data["Stress_XX"] = np.array([2.0])
    ranges = {}
    prepare_output(mesh, "full_model.vtp", ranges)
    assert "Group_ID" not in mesh.point_data
    assert "Stress_XX" not in mesh.point_data
    assert "Stress_XX_DisplayOnly" in mesh.point_data
    assert ranges["Stress_XX"] == [2.0, 2.0]
    assert "Source_Cell_ID" in mesh.cell_data
    assert not public_field("Source_Cell_ID")
    assert not public_field("Stress_XX_DisplayOnly")


def test_slice_does_not_claim_interpolated_point_ids_as_provenance():
    mesh = pv.Plane(i_resolution=1, j_resolution=1)
    attach_source_ids(mesh)
    prepare_output(mesh, "slice_x_1.vtp", {})
    assert "Source_Point_ID" not in mesh.point_data
    assert "Source_Cell_ID" in mesh.cell_data


def test_case_b_range_covers_actual_displacement():
    output = ROOT / "examples/flac3d_slope_exac23/output/model_cache"
    stage = json.loads((output / "index.json").read_text(encoding="utf-8"))["DefaultModel"]["stages"]["exac_23"]
    lo, hi = stage["global_ranges"]["TotalDisplacement"]
    values = pv.read(output / "exac_23/full_model.vtp").point_data["TotalDisplacement"]
    assert lo <= values.min() <= values.max() <= hi
    assert hi < 0.03


def test_all_source_output_pairs_and_geometry_regression():
    summary = json.loads((ROOT / "paper_evidence/revision_v2/summary.json").read_text())
    for case in summary["cases"].values():
        assert not case["failures"]
        assert case["geometry_identical_to_frozen"] is not False
        assert case["byte_identical_regeneration"]
        assert case["paired_arrays"] > 0
