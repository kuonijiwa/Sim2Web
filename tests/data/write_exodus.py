"""Write a tiny multi-step Exodus II file like a MOOSE result (for tests).

8 hexahedra (2x2x2), nodal disp_x/y/z and elemental stress_xx..stress_xz,
three time steps t = 0, 0.5, 1 with values proportional to t.
"""
import sys
import numpy as np
import netCDF4
import pyvista as pv

TIMES = [0.0, 0.5, 1.0]
STRESS = ["xx", "yy", "zz", "xy", "yz", "xz"]
g = pv.ImageData(dimensions=(3, 3, 3)).cast_to_unstructured_grid()
pts = np.asarray(g.points)
conn = g.cell_connectivity.reshape(-1, 8) + 1          # VTK hex order equals Exodus HEX8 order
cen = np.asarray(g.cell_centers().points)

def chars(names, n=33):
    a = np.zeros((len(names), n), dtype="S1")
    for i, s in enumerate(names):
        a[i, :len(s)] = list(s)
    return a

ds = netCDF4.Dataset(sys.argv[1], "w", format="NETCDF3_64BIT_OFFSET")
ds.api_version = np.float32(8.0); ds.version = np.float32(8.0)
ds.floating_point_word_size = np.int32(8); ds.file_size = np.int32(1); ds.title = "sim2web test patch"
for name, size in [("len_string", 33), ("len_line", 81), ("four", 4), ("num_dim", 3), ("num_nodes", len(pts)),
                   ("num_elem", len(conn)), ("num_el_blk", 1), ("num_el_in_blk1", len(conn)),
                   ("num_nod_per_el1", 8), ("num_nod_var", 3), ("num_elem_var", 6), ("time_step", None)]:
    ds.createDimension(name, size)
ds.createVariable("time_whole", "f8", ("time_step",))[:] = TIMES
for i, a in enumerate("xyz"):
    ds.createVariable(f"coord{a}", "f8", ("num_nodes",))[:] = pts[:, i]
ds.createVariable("coor_names", "S1", ("num_dim", "len_string"))[:] = chars(["x", "y", "z"])
ds.createVariable("eb_status", "i4", ("num_el_blk",))[:] = [1]
prop = ds.createVariable("eb_prop1", "i4", ("num_el_blk",)); prop.setncattr("name", "ID"); prop[:] = [1]
ds.createVariable("eb_names", "S1", ("num_el_blk", "len_string"))[:] = chars(["rock"])
c = ds.createVariable("connect1", "i4", ("num_el_in_blk1", "num_nod_per_el1")); c.elem_type = "HEX8"; c[:] = conn
ds.createVariable("name_nod_var", "S1", ("num_nod_var", "len_string"))[:] = chars(["disp_x", "disp_y", "disp_z"])
ds.createVariable("name_elem_var", "S1", ("num_elem_var", "len_string"))[:] = chars([f"stress_{s}" for s in STRESS])
ds.createVariable("elem_var_tab", "i4", ("num_el_blk", "num_elem_var"))[:] = np.ones((1, 6))
for i in range(3):
    v = ds.createVariable(f"vals_nod_var{i + 1}", "f8", ("time_step", "num_nodes"))
    v[:] = np.array([t * 1e-3 * (i + 1) * pts[:, i] for t in TIMES])
for k in range(6):
    v = ds.createVariable(f"vals_elem_var{k + 1}eb1", "f8", ("time_step", "num_el_in_blk1"))
    v[:] = np.array([t * (k + 1) * (1.0 + cen[:, 2]) for t in TIMES])
ds.close()
