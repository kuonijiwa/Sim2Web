import numpy as np
import pytest
import pyvista as pv

from sim2web.config import config_from_dict
from sim2web.fields import DISPLAY_SUFFIX, OutputContract, attach_source_ids, principal_values

from conftest import base_config


def _rotation(a, b, c):
    ca, sa, cb, sb, cc, sc = np.cos(a), np.sin(a), np.cos(b), np.sin(b), np.cos(c), np.sin(c)
    rx = np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]])
    ry = np.array([[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]])
    rz = np.array([[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]])
    return rz @ ry @ rx


@pytest.mark.parametrize("order", ["XX,YY,ZZ,XY,YZ,XZ", "XX,YY,ZZ,XY,XZ,YZ"])
def test_principal_values_of_rotated_tensor(order):
    principal = np.array([-30.0, -12.0, 4.0])
    r = _rotation(0.3, -0.7, 1.1)
    t = r @ np.diag(principal) @ r.T
    comp = {"XX": t[0, 0], "YY": t[1, 1], "ZZ": t[2, 2], "XY": t[0, 1], "YZ": t[1, 2], "XZ": t[0, 2]}
    row = np.array([[comp[k] for k in order.split(",")]])
    np.testing.assert_allclose(principal_values(row, order.split(","))[0], principal, atol=1e-12)


def test_wrong_component_order_changes_principal_values():
    """Declaring the wrong shear order is not harmless: the tensor changes."""
    t = np.array([[-10.0, 1.0, 4.0], [1.0, -6.0, 0.5], [4.0, 0.5, -2.0]])
    flac = np.array([[t[0, 0], t[1, 1], t[2, 2], t[0, 1], t[1, 2], t[0, 2]]])
    right = principal_values(flac, "XX,YY,ZZ,XY,YZ,XZ".split(","))
    wrong = principal_values(flac, "XX,YY,ZZ,XY,XZ,YZ".split(","))
    assert not np.allclose(right, wrong)


def test_output_contract_roles(tmp_path):
    cfg = config_from_dict(base_config("x.vtu"), tmp_path)
    contract = OutputContract(cfg)
    mesh = pv.Plane(i_resolution=1, j_resolution=1)
    attach_source_ids(mesh)
    mesh.point_data["Group_ID"] = np.array([0, 0.5, 0.5, 1])  # an averaged category
    mesh.point_data["Stress_XX"] = np.ones(4)               # an averaged cell field
    mesh.cell_data["Stress_XX"] = np.array([2.0])
    mesh.cell_data["Unrelated"] = np.array([7.0])
    contract.prune(mesh)
    ranges = {}
    contract.finalize(mesh, is_section=False, ranges=ranges)
    assert "Unrelated" not in mesh.cell_data
    assert "Group_ID" not in mesh.point_data
    assert "Stress_XX" not in mesh.point_data and "Stress_XX" + DISPLAY_SUFFIX in mesh.point_data
    assert ranges["Stress_XX"] == [2.0, 2.0]


def test_sections_do_not_claim_point_provenance(tmp_path):
    cfg = config_from_dict(base_config("x.vtu"), tmp_path)
    mesh = pv.Plane(i_resolution=1, j_resolution=1)
    attach_source_ids(mesh)
    OutputContract(cfg).finalize(mesh, is_section=True, ranges={})
    assert "Source_Point_ID" not in mesh.point_data
    assert "Source_Cell_ID" in mesh.cell_data


def test_nonfinite_values_are_refused(tmp_path):
    cfg = config_from_dict(base_config("x.vtu"), tmp_path)
    mesh = pv.Plane(i_resolution=1, j_resolution=1)
    attach_source_ids(mesh)
    mesh.point_data["X_Disp"] = np.array([0, np.nan, 0, 0])
    with pytest.raises(ValueError, match="Nonfinite"):
        OutputContract(cfg).finalize(mesh, is_section=False, ranges={})
