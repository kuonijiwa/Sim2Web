"""Conversion of other mesh/result formats to the VTU input of Sim2Web.

Reading goes through `meshio <https://github.com/nschloe/meshio>`_ (optional
dependency: ``pip install "sim2web[convert]"``), which supports among
others Exodus II (MOOSE, Cubit), MED (Code_Aster, Salome), XDMF (FEniCS),
Gmsh, Abaqus ``.inp`` (mesh only), Nastran and legacy VTK files.

Exodus II files (``.e``, ``.exo``, ...) are read with VTK's own reader, which
needs no further dependency and gives access to every time step (default: the
last).  The reader's option to move the mesh by the displacement field is
switched off: results are published on the undeformed mesh.

Many solvers write vector and tensor fields as separate scalar arrays
(MOOSE: ``disp_x``, ``disp_y``, ``disp_z``, ``stress_xx`` ... ``stress_xz``).
Such groups are assembled into one multi-component array whose component
names come from the suffixes, so that the order is documented in the VTU and
checked by ``sim2web build``.  ``component_names`` can stamp names onto
arrays that carry none.
"""
from __future__ import annotations

from pathlib import Path

import os
import re
import shutil
import tempfile

import numpy as np
import pyvista as pv

EXODUS_SUFFIXES = (".e", ".exo", ".ex2", ".exii", ".gen", ".g")
#: Suffixes recognised when assembling separate component arrays.
VECTOR_SUFFIXES = ("X", "Y", "Z")
TENSOR_SUFFIXES = {"XX", "YY", "ZZ", "XY", "YZ", "XZ", "ZX", "YX", "ZY"}

#: Linear 3D cell types accepted downstream.
LINEAR_3D = {10: "tetra", 12: "hexahedron", 13: "wedge", 14: "pyramid", 11: "voxel"}
#: Quadratic cells reduced to their corner nodes (VTK keeps corner nodes first).
TO_LINEAR = {24: (10, 4), 25: (12, 8), 26: (13, 6), 27: (14, 5), 29: (12, 8), 32: (13, 6)}


def to_linear(mesh: pv.UnstructuredGrid) -> tuple[pv.UnstructuredGrid, dict]:
    """Keep 3D cells; reduce quadratic cells to their corner nodes.

    Returns the mesh and a report of what was kept, reduced and dropped.
    Point data on mid-side nodes is not used afterwards; cell data is kept.
    """
    types = np.asarray(mesh.celltypes)
    report = {"kept": {}, "reduced": {}, "dropped": {}}
    keep_cells = []
    new_cells = []
    new_types = []
    offsets = mesh.offset
    conn = mesh.cell_connectivity
    for i, t in enumerate(types):
        ids = conn[offsets[i]:offsets[i + 1]]
        if t in LINEAR_3D:
            new_types.append(t)
            new_cells.append(ids)
            report["kept"][LINEAR_3D[t]] = report["kept"].get(LINEAR_3D[t], 0) + 1
        elif t in TO_LINEAR:
            lt, n = TO_LINEAR[t]
            new_types.append(lt)
            new_cells.append(ids[:n])
            report["reduced"][int(t)] = report["reduced"].get(int(t), 0) + 1
        else:
            report["dropped"][int(t)] = report["dropped"].get(int(t), 0) + 1
            continue
        keep_cells.append(i)
    # renumber nodes so that nodes no longer referenced (mid-side nodes) are dropped
    used = np.unique(np.concatenate(new_cells)) if new_cells else np.zeros(0, dtype=np.int64)
    remap = np.full(mesh.n_points, -1, dtype=np.int64)
    remap[used] = np.arange(used.size)
    flat = (np.concatenate([np.concatenate(([len(c)], remap[c])) for c in new_cells])
            if new_cells else np.zeros(0, dtype=np.int64))
    out = pv.UnstructuredGrid(flat, np.asarray(new_types, dtype=np.uint8), np.asarray(mesh.points)[used])
    for name in mesh.point_data.keys():
        out.point_data[name] = np.asarray(mesh.point_data[name])[used]
    keep = np.asarray(keep_cells, dtype=np.int64)
    for name in mesh.cell_data.keys():
        out.cell_data[name] = np.asarray(mesh.cell_data[name])[keep]
    return out, report


def stamp_component_names(mesh, array: str, names: list[str]) -> None:
    """Write ``ComponentName`` attributes on an array (point or cell data)."""
    for container in (mesh.GetPointData(), mesh.GetCellData()):
        vtk_array = container.GetArray(array)
        if vtk_array is not None:
            if vtk_array.GetNumberOfComponents() != len(names):
                raise ValueError(f"'{array}' has {vtk_array.GetNumberOfComponents()} components, "
                                 f"{len(names)} names given")
            for i, n in enumerate(names):
                vtk_array.SetComponentName(i, n)
            return
    raise KeyError(f"Array '{array}' not found")


def _take(container, name):
    """Remove an array and return an independent copy of its values.

    ``container.pop(name)`` returns a view of the VTK array, whose memory is
    released once the array leaves the dataset; assigning that view again
    would publish whatever later occupies the memory.
    """
    values = np.array(container[name], copy=True)
    container.remove(name)
    return values


def _is_exodus(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() in EXODUS_SUFFIXES or bool(re.search(r"\.e-s\d+$|\.e\.\d+", name))


def read_exodus(path: Path, time: str | float | int = "last") -> tuple[pv.UnstructuredGrid, dict]:
    """Read one time step of an Exodus II file as a single unstructured grid.

    ``time`` is ``"last"`` (default), ``"first"``, an integer step index (as
    ``"#3"`` or ``3``) or a time value (as ``"1.5"`` or ``1.5``; the nearest
    stored time is used).  Element blocks are combined, nodes shared between
    blocks are identified by their global node id, and the block becomes the
    category ``ElementBlock``.
    """
    if os.name == "nt" and not str(path.resolve()).isascii():
        # VTK's Exodus backend opens files through the narrow Windows API.
        # Keep this workaround local to the reader and leave the input intact.
        with tempfile.TemporaryDirectory(prefix="sim2web-exodus-") as scratch:
            target = Path(scratch) / ("input" + path.suffix)
            if not str(target.resolve()).isascii():
                raise ValueError("VTK needs an ASCII path to read Exodus on Windows; set TEMP to an ASCII path")
            shutil.copyfile(path, target)
            return read_exodus(target, time)

    reader = pv.get_reader(str(path))
    reader.enable_all_point_arrays()
    reader.enable_all_cell_arrays()
    reader.disable_displacements()
    reader.reader.SetGenerateGlobalNodeIdArray(True)
    reader.reader.SetGenerateObjectIdCellArray(True)
    times = list(reader.time_values)
    step = None
    if times:
        if time in ("last", None):
            step = len(times) - 1
        elif time == "first":
            step = 0
        elif isinstance(time, str) and time.startswith("#"):
            step = int(time[1:])
        elif isinstance(time, int):
            step = time
        else:
            step = int(np.argmin(np.abs(np.asarray(times) - float(time))))
        if not -len(times) <= step < len(times):
            raise ValueError(f"time step {step} out of range: the file has {len(times)} steps")
        step %= len(times)
        reader.set_active_time_point(step)
    data = reader.read()
    blocks = data["Element Blocks"] if "Element Blocks" in data.keys() else data
    names = [blocks.get_block_name(i) for i in range(blocks.n_blocks)]
    pieces = [(n, b) for n, b in zip(names, blocks) if b is not None and b.n_cells]
    if not pieces:
        raise ValueError(f"No elements in {path}")
    gid_name = "GlobalNodeId"
    gids = np.concatenate([np.asarray(b.point_data[gid_name]) for _, b in pieces])
    unique, first, inverse = np.unique(gids, return_index=True, return_inverse=True)
    points = np.vstack([np.asarray(b.points, dtype=np.float64) for _, b in pieces])[first]
    cells, types, offset = [], [], 0
    for _, b in pieces:
        conn = np.asarray(b.cell_connectivity) + offset
        sizes = np.diff(np.asarray(b.offset))
        flat = np.insert(inverse[conn], np.repeat(np.asarray(b.offset)[:-1], 1), sizes)
        cells.append(flat)
        types.append(np.asarray(b.celltypes))
        offset += b.n_points
    mesh = pv.UnstructuredGrid(np.concatenate(cells), np.concatenate(types), points)
    skip = {gid_name, "PedigreeNodeId", "PedigreeElementId", "GlobalElementId", "ObjectId"}
    for name in pieces[0][1].point_data.keys():
        if name not in skip:
            mesh.point_data[name] = np.concatenate([np.asarray(b.point_data[name]) for _, b in pieces])[first]
    common = set.intersection(*[set(b.cell_data.keys()) for _, b in pieces]) - skip
    for name in pieces[0][1].cell_data.keys():
        if name in common:
            mesh.cell_data[name] = np.concatenate([np.asarray(b.cell_data[name]) for _, b in pieces])
    block = np.concatenate([np.full(b.n_cells, k, dtype=np.int32) for k, (_, b) in enumerate(pieces)])
    mesh.cell_data["ElementBlock"] = block
    # VTK groups disp_x/disp_y/disp_z into a 3-component array named "disp_"
    for name in list(mesh.point_data.keys()):
        arr = mesh.point_data[name]
        if name.endswith("_") and arr.ndim == 2 and arr.shape[1] == 3:
            mesh.point_data[name.rstrip("_")] = _take(mesh.point_data, name)
            stamp_component_names(mesh, name.rstrip("_"), list(VECTOR_SUFFIXES))
    info = {"time_values": times, "time_step": step, "time": times[step] if step is not None else None,
            "element_blocks": {k: n for k, (n, _) in enumerate(pieces)}}
    return mesh, info


def assemble_components(mesh) -> list[dict]:
    """Combine separate component arrays (``stress_xx`` ...) into one array.

    A group is recognised when several arrays of one association share a
    prefix and their suffixes (after the last ``_``) are exactly the three
    vector components x, y, z, or six distinct symmetric-tensor components.
    The component names are the upper-case suffixes, in the order of the
    canonical list (X,Y,Z or XX,YY,ZZ,XY,YZ,XZ), so no order is guessed.
    """
    done = []
    for kind, container in (("point", mesh.point_data), ("cell", mesh.cell_data)):
        groups: dict[str, dict[str, str]] = {}
        for name in container.keys():
            arr = np.asarray(container[name])
            if arr.ndim != 1 or "_" not in name:
                continue
            prefix, suffix = name.rsplit("_", 1)
            if prefix:
                groups.setdefault(prefix, {})[suffix.upper()] = name
        for prefix, members in groups.items():
            keys = set(members)
            if keys == set(VECTOR_SUFFIXES):
                order = list(VECTOR_SUFFIXES)
            elif len(keys) == 6 and keys <= TENSOR_SUFFIXES:
                canonical = {"XX": 0, "YY": 1, "ZZ": 2, "XY": 3, "YX": 3, "YZ": 4, "ZY": 4, "XZ": 5, "ZX": 5}
                if len({canonical[k] for k in keys}) != 6:
                    continue
                order = sorted(keys, key=lambda k: canonical[k])
            else:
                continue
            if prefix in container.keys():
                continue  # would overwrite an existing array
            container[prefix] = np.column_stack([np.asarray(container[members[k]], dtype=np.float64)
                                                 for k in order])
            for k in order:
                container.pop(members[k])
            stamp_component_names(mesh, prefix, order)
            done.append({"array": prefix, "association": kind, "components": order,
                         "from": [members[k] for k in order]})
    return done


def _component_names(mesh) -> dict[str, list[str]]:
    """Component names of the multi-component arrays that have them."""
    out = {}
    for container in (mesh.GetPointData(), mesh.GetCellData()):
        for i in range(container.GetNumberOfArrays()):
            a = container.GetArray(i)
            if a is None or a.GetNumberOfComponents() < 2:
                continue
            names = [a.GetComponentName(k) for k in range(a.GetNumberOfComponents())]
            if all(names):
                out[a.GetName()] = names
    return out


def convert(source: str | Path, target: str | Path, component_names: dict[str, list[str]] | None = None,
            rename: dict[str, str] | None = None, time: str | float | int = "last",
            assemble: bool = True) -> dict:
    """Convert ``source`` to a VTU file suitable for Sim2Web."""
    source, target = Path(source), Path(target)
    exodus = None
    if _is_exodus(source):
        mesh, exodus = read_exodus(source, time)
    elif source.suffix.lower() in (".vtu", ".vtk", ".vtm"):
        mesh = pv.read(source)
    else:
        try:
            import meshio
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Converting this format needs meshio: pip install 'sim2web[convert]'") from exc
        mesh = pv.from_meshio(meshio.read(source))
    if not isinstance(mesh, pv.UnstructuredGrid):
        mesh = mesh.cast_to_unstructured_grid()
    assembled = assemble_components(mesh) if assemble else []
    for old, new in (rename or {}).items():
        for container in (mesh.point_data, mesh.cell_data):
            if old in container:
                kept = _component_names(mesh).get(old)
                container[new] = _take(container, old)
                if kept:
                    stamp_component_names(mesh, new, kept)
    kept = _component_names(mesh)          # to_linear rebuilds the arrays without names
    mesh, report = to_linear(mesh)
    renamed = rename or {}
    requested = {renamed.get(a, a): n for a, n in (component_names or {}).items()}
    for array, names in {**kept, **requested}.items():
        stamp_component_names(mesh, array, names)
    mesh.save(target)
    report.update({"points": int(mesh.n_points), "cells": int(mesh.n_cells),
                   "point_arrays": list(mesh.point_data.keys()), "cell_arrays": list(mesh.cell_data.keys()),
                   "assembled": assembled, "output": str(target)})
    if exodus is not None:
        report["exodus"] = exodus
    return report
