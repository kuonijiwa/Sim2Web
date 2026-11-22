"""End-to-end builds of synthetic models with analytically known results."""
import json

import numpy as np
import pytest
import pyvista as pv

from sim2web.config import config_from_dict
from sim2web.diagnostics import analytical_interpolation_check, excavation_sensitivity
from sim2web.pipeline import build
from sim2web.validate import validate_package

from conftest import base_config, displacement, make_block_model

SECTIONS = {"placement": "explicit", "positions": {"x": [2.5, 5.25], "y": [4.5], "z": [3.3, 6.7]}}


def _cfg(tmp_path, path, **over):
    data = base_config(path.name, **over)
    data["sections"].update(SECTIONS)
    return config_from_dict(data, tmp_path)


def _read(cfg, rel):
    return pv.read(cfg.cache_dir.parent / rel)


@pytest.mark.parametrize("tetra", [False, True])
def test_excavation_surface_is_the_void_box(tmp_path, tetra):
    grid, void = make_block_model(tetra=tetra)
    path = tmp_path / "m.vtu"
    grid.save(path)
    cfg = _cfg(tmp_path, path)
    result = build(cfg, log=lambda *_: None)
    stage = json.loads(result.index_path.read_text())["stages"][0]
    layers = {l["id"]: l for l in stage["layers"]}
    exc = _read(cfg, layers["excavation"]["file"])
    assert exc.area == pytest.approx(96.0, rel=1e-6)          # 6 faces of a 4 x 4 x 4 box
    # every excavation face belongs to a retained (non-void) source cell
    ids = np.asarray(exc.cell_data["Source_Cell_ID"])
    assert not void[ids].any()
    ext = _read(cfg, layers["exterior"]["file"])
    # complete boundary of the retained solid: 6 outer faces of the 10 m cube,
    # both sides of the group seam at z = 5 minus the 4 x 4 hole of the void,
    # and the 96 m2 of cavity walls
    assert ext.area == pytest.approx(600.0 + 2 * (100.0 - 16.0) + 96.0, rel=1e-6)
    assert stage["void"]["cells"] == int(void.sum())


def test_section_values_reproduce_a_linear_field_exactly(tmp_path, block_model):
    path, grid, _ = block_model
    cfg = _cfg(tmp_path, path)
    result = build(cfg, log=lambda *_: None)
    stage = json.loads(result.index_path.read_text())["stages"][0]
    n = 0
    for axis, entries in stage["sections"].items():
        for e in entries:
            sec = _read(cfg, e["file"])
            pts = np.asarray(sec.points, dtype=np.float64)
            assert np.allclose(pts[:, "xyz".index(axis)], e["value"], atol=1e-5)
            exact = displacement(pts)
            for k, comp in enumerate(("X_Disp", "Y_Disp", "Z_Disp")):
                np.testing.assert_allclose(sec.point_data[comp], exact[:, k], atol=2e-7)
            np.testing.assert_allclose(sec.point_data["TotalDisplacement"], np.linalg.norm(exact, axis=1), atol=4e-7)
            assert "Source_Point_ID" not in sec.point_data
            n += 1
    assert n == 5


def test_build_is_deterministic(tmp_path, block_model):
    path, _, _ = block_model
    cfg = _cfg(tmp_path, path)
    first = build(cfg, log=lambda *_: None)
    snapshot = {p.relative_to(cfg.cache_dir): p.read_bytes() for p in cfg.cache_dir.rglob("*")
                if p.is_file() and p.name != "build_report.json"}
    build(cfg, log=lambda *_: None)
    again = {p.relative_to(cfg.cache_dir): p.read_bytes() for p in cfg.cache_dir.rglob("*")
             if p.is_file() and p.name != "build_report.json"}
    assert snapshot == again
    assert first.index_path.name == "index.json"


def test_validation_passes_and_detects_tampering(tmp_path, block_model):
    path, _, _ = block_model
    cfg = _cfg(tmp_path, path)
    build(cfg, log=lambda *_: None)
    report = validate_package(cfg, log=lambda *_: None)
    assert report["failures"] == []
    s = report["stages"]["s1"]
    assert s["exact_arrays"] > 0 and s["exact_mismatches"] == 0
    assert s["interpolated_arrays"] > 0 and s["max_interp_nrmse"] < 1e-6
    # tamper with one product: the validator must notice
    stage = json.loads((cfg.cache_dir / "index.json").read_text())["stages"][0]
    target = cfg.cache_dir.parent / stage["layers"][0]["file"]
    mesh = pv.read(target)
    mesh.cell_data["Stress_XX"] = np.asarray(mesh.cell_data["Stress_XX"]) * 1.001
    mesh.save(target)
    report = validate_package(cfg, log=lambda *_: None)
    assert any("Stress_XX" in f for f in report["failures"])
    assert any("hash" in f for f in report["failures"])


def test_label_strategy_and_misclassification_diagnostics(tmp_path):
    grid, void = make_block_model(near_null_cell=True)
    path = tmp_path / "m.vtu"
    grid.save(path)
    stress_cfg = _cfg(tmp_path, path)
    result = build(stress_cfg, log=lambda *_: None)
    diag = result.stages[0].report["void_diagnostics"]
    # the stress criterion takes the near-null retained cell for a void cell ...
    assert diag["void_cells"] == void.sum() + 1
    # ... and the label comparison exposes the disagreement
    assert diag["label_agreement"]["criterion_only"] == 1
    label_cfg = _cfg(tmp_path, path, **{"geometry.excavation.strategy": "labels"})
    result = build(label_cfg, log=lambda *_: None)
    assert result.stages[0].report["void_diagnostics"]["void_cells"] == void.sum()


def test_sensitivity_is_flat_across_the_stress_gap(tmp_path, block_model):
    path, _, _ = block_model
    cfg = _cfg(tmp_path, path)
    out = excavation_sensitivity(cfg, thresholds=[1e-12, 1e-8, 1e-2], tolerances=[1e-7, 1e-6, 1e-3],
                                 log=lambda *_: None)
    assert all(r["jaccard_vs_baseline"] == 1.0 for r in out["rows"])
    assert all(r["jaccard_vs_labels"] == 1.0 for r in out["rows"])


def test_analytical_check_reports_exact_interpolation(tmp_path, block_model):
    path, _, _ = block_model
    cfg = _cfg(tmp_path, path)
    out = analytical_interpolation_check(cfg, per_axis=2, log=lambda *_: None)
    assert out["rows"] and out["all_within_rounding_bound"]
    assert out["max_relative_error_float64"] < 1e-7


def test_multistage_build_has_global_ranges(tmp_path):
    files = []
    for k, scale in enumerate((1.0, 2.0)):
        grid, _ = make_block_model()
        grid.point_data["Displacement"] = grid.point_data["Displacement"] * scale
        path = tmp_path / f"stage_{k + 1}.vtu"
        grid.save(path)
        files.append(path)
    data = base_config("unused")
    data["input"] = {"glob": "stage_*.vtu"}
    data["sections"].update(SECTIONS)
    cfg = config_from_dict(data, tmp_path)
    index = json.loads(build(cfg, log=lambda *_: None).index_path.read_text())
    assert [s["id"] for s in index["stages"]] == ["stage_1", "stage_2"]
    g = index["ranges"]["TotalDisplacement"]
    s2 = index["stages"][1]["fields"]["TotalDisplacement"]
    assert g["max"] == s2["max"] > index["stages"][0]["fields"]["TotalDisplacement"]["max"]


def test_explicit_void_field_strategy(tmp_path):
    grid, void = make_block_model(labels=False)
    grid.cell_data["Excavated"] = void.astype(np.int8)
    path = tmp_path / "m.vtu"
    grid.save(path)
    cfg = _cfg(tmp_path, path, **{"geometry.excavation.strategy": "field",
                                  "geometry.excavation.void_field": "Excavated"})
    result = build(cfg, log=lambda *_: None)
    assert result.stages[0].report["void_diagnostics"]["void_cells"] == void.sum()


def test_declared_order_must_match_component_names(tmp_path):
    from sim2web.config import ConfigError
    grid, _ = make_block_model(stress_order="XX,YY,ZZ,XY,XZ,YZ")   # file names XZ before YZ
    path = tmp_path / "m.vtu"
    grid.save(path)
    cfg = _cfg(tmp_path, path)                                  # configuration says XY,YZ,XZ
    with pytest.raises(ConfigError, match="declares XX,YY,ZZ,XY,XZ,YZ"):
        build(cfg, log=lambda *_: None)
    # 'from_file' adopts the names written in the file
    cfg = _cfg(tmp_path, path, **{"fields.stress.order": "from_file"})
    stage = json.loads(build(cfg, log=lambda *_: None).index_path.read_text())["stages"][0]
    assert stage["stress_component_order"]["order"] == "XX,YY,ZZ,XY,XZ,YZ"
    assert validate_package(cfg, log=lambda *_: None)["failures"] == []


def test_validator_flags_an_order_the_build_was_told_to_ignore(tmp_path):
    grid, _ = make_block_model(stress_order="XX,YY,ZZ,XY,XZ,YZ")
    path = tmp_path / "m.vtu"
    grid.save(path)
    cfg = _cfg(tmp_path, path, **{"fields.stress.check_file_order": False})
    build(cfg, log=lambda *_: None)
    failures = validate_package(cfg, log=lambda *_: None)["failures"]
    assert any("differs from the file's ComponentName" in f for f in failures)
    assert any("Stress_" in f and "Principal" in f for f in failures)   # wrong principal stresses are caught


def test_from_file_without_component_names_is_an_error(tmp_path):
    from sim2web.config import ConfigError
    grid, _ = make_block_model(name_components=False)
    path = tmp_path / "m.vtu"
    grid.save(path)
    cfg = _cfg(tmp_path, path, **{"fields.stress.order": "from_file"})
    with pytest.raises(ConfigError, match="does not name the components"):
        build(cfg, log=lambda *_: None)


def test_removed_zones_strategy_finds_pit_walls_and_floor(tmp_path):
    """Excavated zones deleted before export: a 4 x 4 x 4 pit open at the top."""
    grid, _ = make_block_model(void_box=(-1, -1), labels=False)       # no void cells
    centers = grid.cell_centers().points
    pit = (np.abs(centers[:, 0] - 5) < 2) & (np.abs(centers[:, 1] - 5) < 2) & (centers[:, 2] > 6)
    solid = grid.extract_cells(np.flatnonzero(~pit))
    array = solid.GetCellData().GetArray("Stress")
    for i, comp in enumerate("XX,YY,ZZ,XY,YZ,XZ".split(",")):
        array.SetComponentName(i, comp)
    path = tmp_path / "pit.vtu"
    solid.save(path)
    cfg = _cfg(tmp_path, path, **{"geometry.excavation.strategy": "removed_zones",
                                  "geometry.excavation.contact_tolerance": 1e-6})
    stage = json.loads(build(cfg, log=lambda *_: None).index_path.read_text())["stages"][0]
    layer = {l["id"]: l for l in stage["layers"]}["excavation"]
    surface = _read(cfg, layer["file"])
    # four walls of 4 x 4 plus the 4 x 4 floor; the ground surface (z = 10) is excluded
    assert surface.area == pytest.approx(5 * 16.0, rel=1e-6)
    assert validate_package(cfg, log=lambda *_: None)["failures"] == []


def test_removed_zones_ignores_unmerged_interfaces_below_the_pit(tmp_path):
    """Zones generated separately share no gridpoints with their neighbours.

    The interface is a boundary of the mesh topology but has rock on both
    sides; it must not be published as excavation surface (Case D, r3 run).
    """
    grid, _ = make_block_model(void_box=(-1, -1), labels=False)
    centers = grid.cell_centers().points
    pit = (np.abs(centers[:, 0] - 5) < 2) & (np.abs(centers[:, 1] - 5) < 2) & (centers[:, 2] > 6)
    core = (np.abs(centers[:, 0] - 5) < 3) & (np.abs(centers[:, 1] - 5) < 3) & (centers[:, 2] < 6)
    rest = grid.extract_cells(np.flatnonzero(~pit & ~core))
    inner = grid.extract_cells(np.flatnonzero(core))
    solid = rest.merge(inner, merge_points=False)
    assert solid.n_points > rest.n_points + 1  # the interface nodes are duplicated
    array = solid.GetCellData().GetArray("Stress")
    for i, comp in enumerate("XX,YY,ZZ,XY,YZ,XZ".split(",")):
        array.SetComponentName(i, comp)
    path = tmp_path / "pit.vtu"
    solid.save(path)
    cfg = _cfg(tmp_path, path, **{"geometry.excavation.strategy": "removed_zones",
                                  "geometry.excavation.contact_tolerance": 1e-6})
    index = json.loads(build(cfg, log=lambda *_: None).index_path.read_text())
    stage = index["stages"][0]
    layer = {l["id"]: l for l in stage["layers"]}["excavation"]
    surface = _read(cfg, layer["file"])
    assert surface.area == pytest.approx(5 * 16.0, rel=1e-6)
    # internal_faces: auto drops the interface from the exterior as well
    assert stage["internal_faces"] == "drop" and stage["mesh_regions"] == 2
    exterior = _read(cfg, {l["id"]: l for l in stage["layers"]}["exterior"]["file"])
    assert exterior.area == pytest.approx(6 * 100.0 - 16.0 + 5 * 16.0, rel=1e-6)
    assert validate_package(cfg, log=lambda *_: None)["failures"] == []


def test_convert_reduces_quadratic_cells_and_stamps_component_names(tmp_path):
    meshio = pytest.importorskip("meshio")
    from sim2web.convert import convert
    from sim2web.vtkxml import component_names

    # one quadratic tetrahedron (10 nodes) with nodal stress, written as Exodus-like legacy VTK by meshio
    pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [.5, 0, 0], [.5, .5, 0], [0, .5, 0],
                    [0, 0, .5], [.5, 0, .5], [0, .5, .5]], dtype=float)
    m = meshio.Mesh(pts, [("tetra10", np.arange(10).reshape(1, 10))],
                    point_data={"U": pts * 1e-3, "S": np.tile(np.arange(6.0), (10, 1))})
    src = tmp_path / "model.vtk"
    m.write(src)
    report = convert(src, tmp_path / "model.vtu", {"S": "XX,YY,ZZ,XY,YZ,XZ".split(",")}, {"U": "Displacement"})
    assert report["reduced"] and report["cells"] == 1 and report["points"] == 4
    assert component_names(tmp_path / "model.vtu")["S"] == ["XX", "YY", "ZZ", "XY", "YZ", "XZ"]
