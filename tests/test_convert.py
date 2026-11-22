"""Conversion of solver output to the VTU input (``sim2web convert``).

``tests/data/moose_like_patch.e`` is a small Exodus II file written by
``tests/data/write_exodus.py`` in the layout MOOSE uses: 8 hexahedra, nodal
``disp_x/y/z`` and elemental ``stress_xx`` ... ``stress_xz`` at t = 0, 0.5, 1,
all proportional to t.
"""
import shutil
from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

from sim2web.config import config_from_dict
from sim2web.convert import assemble_components, convert
from sim2web.pipeline import build
from sim2web.validate import validate_package
from sim2web.vtkxml import component_names

from conftest import base_config

EXODUS = Path(__file__).resolve().parent / "data" / "moose_like_patch.e"


def _expected(t):
    g = pv.ImageData(dimensions=(3, 3, 3)).cast_to_unstructured_grid()
    p, c = np.asarray(g.points), np.asarray(g.cell_centers().points)
    disp = np.column_stack([t * 1e-3 * (i + 1) * p[:, i] for i in range(3)])
    stress = np.column_stack([t * (k + 1) * (1.0 + c[:, 2]) for k in range(6)])
    return p, disp, stress


def _sorted_by_position(points, values):
    order = np.lexsort(np.asarray(points).T[::-1])
    return np.asarray(values)[order]


@pytest.mark.parametrize("time, t", [("last", 1.0), ("#1", 0.5), (0.4, 0.5), ("first", 0.0)])
def test_exodus_time_step_is_selected_and_components_assembled(tmp_path, time, t):
    out = tmp_path / "patch.vtu"
    report = convert(EXODUS, out, time=time)
    assert report["exodus"]["time"] == t
    mesh = pv.read(out)
    points, disp, stress = _expected(t)
    assert mesh.n_cells == 8 and mesh.n_points == 27
    # the mesh is not moved by the displacement field
    np.testing.assert_allclose(_sorted_by_position(mesh.points, mesh.points), _sorted_by_position(points, points))
    np.testing.assert_allclose(_sorted_by_position(mesh.points, mesh.point_data["disp"]),
                               _sorted_by_position(points, disp))
    centres = mesh.cell_centers().points
    ref_centres = pv.ImageData(dimensions=(3, 3, 3)).cast_to_unstructured_grid().cell_centers().points
    np.testing.assert_allclose(_sorted_by_position(centres, mesh.cell_data["stress"]),
                               _sorted_by_position(ref_centres, stress))
    names = component_names(out)
    assert names["disp"] == ["X", "Y", "Z"]
    assert names["stress"] == ["XX", "YY", "ZZ", "XY", "YZ", "XZ"]
    assert [a["array"] for a in report["assembled"]] == ["stress"]


def test_time_step_out_of_range_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="out of range"):
        convert(EXODUS, tmp_path / "x.vtu", time="#7")


def test_assembly_orders_components_by_name_not_by_file_order():
    g = pv.ImageData(dimensions=(2, 2, 2)).cast_to_unstructured_grid()
    for k, comp in enumerate(["xz", "xx", "zz", "yz", "xy", "yy"]):      # scrambled file order
        g.cell_data[f"s_{comp}"] = np.full(g.n_cells, float(k))
    g.point_data["u_x"] = np.zeros(g.n_points)                          # incomplete vector: left alone
    done = assemble_components(g)
    assert done[0]["components"] == ["XX", "YY", "ZZ", "XY", "YZ", "XZ"]
    np.testing.assert_array_equal(g.cell_data["s"][0], [1, 5, 2, 4, 3, 0])
    assert "u_x" in g.point_data and "u" not in g.point_data


def test_renamed_arrays_keep_their_values_and_names(tmp_path):
    """Regression: renaming used ``pop``, whose result pointed to freed memory."""
    g = pv.ImageData(dimensions=(3, 3, 3)).cast_to_unstructured_grid()
    g.point_data["U"] = np.asarray(g.points) * 1e-3 + 0.5
    src = tmp_path / "in.vtu"
    g.save(src)
    convert(src, tmp_path / "out.vtu", {"U": ["X", "Y", "Z"]}, {"U": "Displacement"})
    out = pv.read(tmp_path / "out.vtu")
    np.testing.assert_allclose(out.point_data["Displacement"], np.asarray(g.points) * 1e-3 + 0.5)
    assert component_names(tmp_path / "out.vtu")["Displacement"] == ["X", "Y", "Z"]


def test_converted_exodus_result_builds_and_validates(tmp_path):
    vtu = tmp_path / "patch.vtu"
    convert(EXODUS, vtu, rename={"disp": "Displacement", "stress": "Stress"})
    data = base_config(vtu.name, **{
        "fields.stress.order": "from_file", "fields.stress.unit": "Pa",
        "fields.stress.unit_check": False,
        "fields.categories": [{"name": "ElementBlock", "label": "Block"}],
        "geometry.excavation.enabled": False, "geometry.groups.field": "ElementBlock",
    })
    data["sections"].update({"spacing": 0.5})
    cfg = config_from_dict(data, tmp_path)
    build(cfg, log=lambda *_: None)
    assert validate_package(cfg, log=lambda *_: None)["failures"] == []
