# -*- coding: utf-8 -*-
"""Export an Abaqus result (.odb) to a VTU file for Sim2Web.

Run with the Python interpreter shipped with Abaqus (2.7 or 3.x):

    abaqus python abaqus_odb_to_vtu.py job.odb job.vtu [--step NAME] [--frame -1]
                                       [--stress-position auto|centroid|nodal]

What is written
---------------
* nodes of all part instances (coordinates in the model's length unit);
* 3D continuum elements (C3D4/6/8/10/15/20 and reduced/hybrid variants), quadratic
  elements reduced to their corner nodes; other elements (beams, shells,
  connectors) are skipped and counted;
* PointData ``U`` (nodal displacement) with ComponentNames X, Y, Z;
* stress ``S`` with ComponentNames taken from Abaqus' component labels (S11,
  S22, S33, S12, S13, S23 -> XX, YY, ZZ, XY, XZ, YZ), so that Sim2Web reads
  the order from the file:

  - as CellData at the element centroid when the ODB can provide it
    (integration-point output), which is the default;
  - otherwise as PointData: nodal values (``NODAL`` output) or, failing
    that, the average over elements of the element-nodal values
    (``ELEMENT_NODAL``, the averaged contour of Abaqus/CAE).
    ``--stress-position`` forces one of the two;
* CellData ``Instance`` as a category.

Without ``--step`` the last step that contains frames is used.  The script
stops with exit code 2 when the selected step has no frames or when no 3D
continuum element is written, instead of producing an empty file.

STATUS: tested with mocks of the odbAccess API and, in the r3 run, with the
upgraded R2019 crankshaft example ODB from the Abaqus installation.
"""
from __future__ import print_function

import base64
import struct
import sys

import numpy as np
from odbAccess import openOdb
from abaqusConstants import CENTROID, ELEMENT_NODAL, NODAL

VTK = {"C3D4": (10, 4), "C3D10": (10, 4), "C3D6": (13, 6), "C3D15": (13, 6),
       "C3D8": (12, 8), "C3D20": (12, 8)}


def vtk_type(abaqus_type):
    base = abaqus_type.rstrip("HMRITP")  # C3D8R, C3D10M, C3D20RH, C3D8T ... -> C3D8 / C3D10 / C3D20
    while base and base not in VTK and base[-1].isalpha():
        base = base[:-1]
    return VTK.get(base)


def b64(array):
    raw = np.ascontiguousarray(array).tobytes()
    return base64.b64encode(struct.pack("<I", len(raw)) + raw).decode("ascii")


def data_array(name, array, vtk_type_name, names=None):
    comps = 1 if array.ndim == 1 else array.shape[1]
    attrs = ['type="%s"' % vtk_type_name, 'Name="%s"' % name, 'NumberOfComponents="%d"' % comps,
             'format="binary"']
    for i, n in enumerate(names or []):
        attrs.append('ComponentName%d="%s"' % (i, n))
    return "<DataArray %s>%s</DataArray>\n" % (" ".join(attrs), b64(array))


def string_array(name, values):
    text = " ".join(str(v).replace(" ", "_") for v in values)
    # VTK XML string arrays are not trivial; store category codes and a lookup in the name instead
    labels = sorted(set(values))
    codes = np.array([labels.index(v) for v in values], dtype=np.int32)
    return data_array(name, codes, "Int32"), labels, text


def _arg(argv, name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


def _pick_step(odb, step_name):
    if step_name:
        return odb.steps[step_name]
    with_frames = [odb.steps[k] for k in odb.steps.keys() if len(odb.steps[k].frames)]
    return with_frames[-1] if with_frames else None


def _nodal_stress(s_field, inst, node_index, base, n_nodes):
    """Per-node stress of one instance: NODAL output, else averaged ELEMENT_NODAL."""
    for position, label in ((NODAL, "nodal"), (ELEMENT_NODAL, "element-nodal average")):
        values = s_field.getSubset(region=inst, position=position).values
        if not values:
            continue
        total = np.zeros((n_nodes, 6))
        count = np.zeros(n_nodes)
        for v in values:
            k = node_index[v.nodeLabel] - base
            d = list(v.data)[:6]
            total[k, :len(d)] += d
            count[k] += 1
        out = np.full((n_nodes, 6), np.nan)
        hit = count > 0
        out[hit] = total[hit] / count[hit, None]
        return out, label
    return None, None


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    odb_path, out_path = argv[1], argv[2]
    frame_index = int(_arg(argv, "--frame", -1))
    position = _arg(argv, "--stress-position", "auto")
    if position not in ("auto", "centroid", "nodal"):
        print("--stress-position must be auto, centroid or nodal")
        return 1
    odb = openOdb(odb_path, readOnly=True)
    step = _pick_step(odb, _arg(argv, "--step"))
    if step is None or not len(step.frames):
        print("No step with frames in %s (steps: %s)" % (odb_path, ", ".join(odb.steps.keys())))
        return 2
    frame = step.frames[frame_index]
    u_field = frame.fieldOutputs["U"] if "U" in frame.fieldOutputs.keys() else None
    s_field = frame.fieldOutputs["S"] if "S" in frame.fieldOutputs.keys() else None
    labels = [str(c) for c in s_field.componentLabels] if s_field is not None else []
    comp_map = {"S11": "XX", "S22": "YY", "S33": "ZZ", "S12": "XY", "S13": "XZ", "S23": "YZ"}
    stress_names = [comp_map.get(c, c) for c in labels]

    instances = [i for n, i in odb.rootAssembly.instances.items() if n != "ASSEMBLY"]
    # centroid stress where available, unless nodal stress was requested
    centroid = {}
    if s_field is not None and position != "nodal":
        for inst in instances:
            centroid[inst.name] = dict((v.elementLabel, v.data)
                                       for v in s_field.getSubset(region=inst, position=CENTROID).values)
    use_cells = s_field is not None and position != "nodal" and any(centroid.values())
    if position == "centroid" and not use_cells:
        print("No centroid stress in this frame; try --stress-position nodal")
        return 2

    points, conn, offsets, types, inst_of_cell = [], [], [], [], []
    disp, stress, point_stress = [], [], []
    stress_source = None
    skipped = {}
    base = 0
    for inst in instances:
        node_index = {}
        for k, node in enumerate(inst.nodes):
            node_index[node.label] = base + k
            points.append(node.coordinates)
        u = np.zeros((len(inst.nodes), 3))
        if u_field is not None:
            for v in u_field.getSubset(region=inst).values:
                d = list(v.data) + [0.0] * (3 - len(v.data))
                u[node_index[v.nodeLabel] - base] = d[:3]
        disp.append(u)
        if s_field is not None and not use_cells:
            values, stress_source = _nodal_stress(s_field, inst, node_index, base, len(inst.nodes))
            point_stress.append(values if values is not None else np.full((len(inst.nodes), 6), np.nan))
        s_by_label = centroid.get(inst.name, {})
        for e in inst.elements:
            vt = vtk_type(e.type)
            if vt is None or (use_cells and e.label not in s_by_label):
                skipped[e.type] = skipped.get(e.type, 0) + 1
                continue
            code, ncorner = vt
            ids = [node_index[n] for n in e.connectivity[:ncorner]]
            conn.extend(ids)
            offsets.append(len(conn))
            types.append(code)
            inst_of_cell.append(inst.name)
            if use_cells:
                stress.append(list(s_by_label[e.label])[:6])
        base += len(inst.nodes)

    if not types:
        print("No 3D continuum element was written (skipped: %s); nothing to export" % (skipped or "none"))
        odb.close()
        return 2
    points = np.asarray(points, dtype=np.float64)
    disp = np.vstack(disp)
    inst_codes, inst_labels, _ = string_array("Instance", inst_of_cell)
    point_arrays = data_array("U", disp, "Float64", ["X", "Y", "Z"])
    cell_arrays = inst_codes
    if use_cells:
        cell_arrays = data_array("S", np.asarray(stress, dtype=np.float64), "Float64", stress_names) + cell_arrays
        stress_source = "element centroid"
    elif point_stress:
        nodal = np.vstack(point_stress)
        used = np.unique(np.asarray(conn))
        if np.isnan(nodal[used]).any():
            print("Warning: %d element nodes have no stress value" % int(np.isnan(nodal[used]).any(axis=1).sum()))
        point_arrays += data_array("S", nodal, "Float64", stress_names)

    with open(out_path, "w") as f:
        f.write('<?xml version="1.0"?>\n<VTKFile type="UnstructuredGrid" version="1.0" byte_order="LittleEndian" '
                'header_type="UInt32">\n<UnstructuredGrid>\n')
        f.write('<Piece NumberOfPoints="%d" NumberOfCells="%d">\n' % (len(points), len(types)))
        f.write("<PointData>\n" + point_arrays + "</PointData>\n")
        f.write("<CellData>\n" + cell_arrays + "</CellData>\n")
        f.write("<Points>\n" + data_array("Points", points, "Float64") + "</Points>\n")
        f.write("<Cells>\n" + data_array("connectivity", np.asarray(conn, dtype=np.int64), "Int64")
                + data_array("offsets", np.asarray(offsets, dtype=np.int64), "Int64")
                + data_array("types", np.asarray(types, dtype=np.uint8), "UInt8") + "</Cells>\n")
        f.write("</Piece>\n</UnstructuredGrid>\n</VTKFile>\n")
    print("Wrote %s: %d nodes, %d cells; step %s, frame %d" % (out_path, len(points), len(types), step.name,
                                                               frame_index))
    if s_field is None:
        print("No stress output (S) in this frame: only displacement was written")
    else:
        print("Stress components: %s -> %s; position: %s" % (",".join(labels), ",".join(stress_names),
                                                              stress_source))
    print("Instance codes: %s" % ", ".join("%d=%s" % (i, n) for i, n in enumerate(inst_labels)))
    if skipped:
        print("Skipped elements (not 3D continuum or no centroid stress): %s" % skipped)
    odb.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
