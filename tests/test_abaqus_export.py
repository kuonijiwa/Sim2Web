"""Test tools/abaqus_odb_to_vtu.py against a mock of the documented odbAccess API.

This checks the VTU writer, element mapping, component naming and the
situations met with real example ODBs in the r3 run (stress only at nodes,
a last step without frames, no continuum elements) without an Abaqus
installation; reading of real .odb files still needs Abaqus.
"""
import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("S11", "S22", "S33", "S12", "S13", "S23")


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Field:
    """A field output whose values exist only at some positions."""

    def __init__(self, by_position, labels=()):
        self._by_position = by_position
        self.componentLabels = labels

    def getSubset(self, region=None, position=None):
        return _Obj(values=self._by_position.get(position, self._by_position.get(None, [])))


def _cube():
    cube = pv.ImageData(dimensions=(3, 2, 2)).cast_to_unstructured_grid()
    nodes = np.asarray(cube.points)
    # two C3D8R hexahedra (Abaqus node order equals VTK hexahedron order)
    hexes = [[0, 1, 4, 3, 6, 7, 10, 9], [1, 2, 5, 4, 7, 8, 11, 10]]
    return nodes, [("C3D8R", [i + 1 for i in h]) for h in hexes]


def _load(monkeypatch, nodes, elements, fields, steps=None):
    inst = _Obj(name="PART-1-1",
                nodes=[_Obj(label=i + 1, coordinates=tuple(c)) for i, c in enumerate(nodes)],
                elements=[_Obj(label=k + 1, type=t, connectivity=tuple(c)) for k, (t, c) in enumerate(elements)])
    steps = steps or {"Step-1": _Obj(name="Step-1", frames=[_Obj(fieldOutputs=fields)])}
    odb = _Obj(steps=steps, rootAssembly=_Obj(instances={"PART-1-1": inst}), close=lambda: None)
    odb_access = types.ModuleType("odbAccess")
    odb_access.openOdb = lambda path, readOnly=True: odb
    constants = types.ModuleType("abaqusConstants")
    constants.CENTROID, constants.NODAL, constants.ELEMENT_NODAL = "CENTROID", "NODAL", "ELEMENT_NODAL"
    monkeypatch.setitem(sys.modules, "odbAccess", odb_access)
    monkeypatch.setitem(sys.modules, "abaqusConstants", constants)
    spec = importlib.util.spec_from_file_location("abaqus_odb_to_vtu", ROOT / "tools" / "abaqus_odb_to_vtu.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _u(nodes):
    u = nodes * 1e-3
    return u, _Field({None: [_Obj(nodeLabel=i + 1, data=tuple(v)) for i, v in enumerate(u)]})


def test_centroid_stress_is_written_as_cell_data(tmp_path, monkeypatch):
    nodes, elements = _cube()
    elements = elements + [("B31", [1, 2])]                       # a beam, skipped
    u, u_field = _u(nodes)
    s = [[-1.0, -2.0, -3.0, 0.1, 0.2, 0.3], [-1.5, -2.5, -3.5, 0.4, 0.5, 0.6], [0, 0, 0, 0, 0, 0]]
    s_field = _Field({"CENTROID": [_Obj(elementLabel=k + 1, data=tuple(v)) for k, v in enumerate(s)]}, LABELS)
    module = _load(monkeypatch, nodes, elements, {"U": u_field, "S": s_field})
    out = tmp_path / "job.vtu"
    assert module.main(["x", "job.odb", str(out)]) == 0

    mesh = pv.read(out)
    assert mesh.n_cells == 2 and mesh.n_points == 12
    assert list(np.unique(mesh.celltypes)) == [12]
    np.testing.assert_allclose(mesh.point_data["U"], u)
    np.testing.assert_allclose(mesh.cell_data["S"], s[:2])
    assert abs(mesh.volume - 2.0) < 1e-12                        # node order gives positive volumes
    from sim2web.vtkxml import component_names
    assert component_names(out)["S"] == ["XX", "YY", "ZZ", "XY", "XZ", "YZ"]


def test_nodal_only_stress_falls_back_to_point_data(tmp_path, monkeypatch):
    """R2020 crankshaft example: S is available at the nodes only."""
    nodes, elements = _cube()
    _, u_field = _u(nodes)
    s = np.column_stack([-nodes[:, 2] - 1, -nodes[:, 2] - 2, -nodes[:, 2] - 3, nodes[:, 0], 0 * nodes[:, 0],
                         nodes[:, 1]])
    s_field = _Field({"NODAL": [_Obj(nodeLabel=i + 1, data=tuple(v)) for i, v in enumerate(s)]}, LABELS)
    module = _load(monkeypatch, nodes, elements, {"U": u_field, "S": s_field})
    out = tmp_path / "job.vtu"
    assert module.main(["x", "job.odb", str(out)]) == 0
    mesh = pv.read(out)
    assert mesh.n_cells == 2 and "S" not in mesh.cell_data
    np.testing.assert_allclose(mesh.point_data["S"], s)


def test_element_nodal_values_are_averaged(tmp_path, monkeypatch):
    nodes, elements = _cube()
    _, u_field = _u(nodes)
    values = []
    for k, (_, conn) in enumerate(elements):                     # element k gives each of its nodes k + 1
        values += [_Obj(nodeLabel=n, data=(k + 1.0,) * 6) for n in conn]
    s_field = _Field({"ELEMENT_NODAL": values}, LABELS)
    module = _load(monkeypatch, nodes, elements, {"U": u_field, "S": s_field})
    out = tmp_path / "job.vtu"
    assert module.main(["x", "job.odb", str(out)]) == 0
    s = pv.read(out).point_data["S"]
    shared = [1, 4, 7, 10]                                       # nodes of the common face
    np.testing.assert_allclose(s[shared, 0], 1.5)
    np.testing.assert_allclose(s[[0, 3, 6, 9], 0], 1.0)


def test_last_step_without_frames_is_skipped(tmp_path, monkeypatch):
    """Plate example: the last steps of the ODB contain no frames."""
    nodes, elements = _cube()
    _, u_field = _u(nodes)
    s_field = _Field({"CENTROID": [_Obj(elementLabel=k + 1, data=(-1.0,) * 6) for k in range(2)]}, LABELS)
    steps = {"Step-1": _Obj(name="Step-1", frames=[_Obj(fieldOutputs={"U": u_field, "S": s_field})]),
             "Step-2": _Obj(name="Step-2", frames=[])}
    module = _load(monkeypatch, nodes, elements, None, steps=steps)
    out = tmp_path / "job.vtu"
    assert module.main(["x", "job.odb", str(out)]) == 0
    assert pv.read(out).n_cells == 2
    assert module.main(["x", "job.odb", str(out), "--step", "Step-2"]) == 2


@pytest.mark.parametrize("elements", [[("B31", [1, 2])], [("S4R", [1, 2, 5, 4])]])
def test_no_continuum_elements_is_an_error(tmp_path, monkeypatch, elements):
    nodes, _ = _cube()
    _, u_field = _u(nodes)
    s_field = _Field({"CENTROID": [_Obj(elementLabel=1, data=(-1.0,) * 6)]}, LABELS)
    module = _load(monkeypatch, nodes, elements, {"U": u_field, "S": s_field})
    out = tmp_path / "job.vtu"
    assert module.main(["x", "job.odb", str(out)]) == 2
    assert not out.exists()
