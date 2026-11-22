"""Engineering-oriented geometry: exterior surfaces, excavation boundary, sections.

All functions take and return PyVista datasets and never renumber the source
identifiers attached by :func:`sim2web.fields.attach_source_ids`.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyvista as pv
import vtk
from scipy.spatial import KDTree
from vtk.util.numpy_support import vtk_to_numpy

REGION = "_sim2web_region"


@dataclass
class SolidPartition:
    """The retained solid, its void complement and its group decomposition."""

    solid: pv.UnstructuredGrid
    void: pv.UnstructuredGrid
    group_codes: np.ndarray | None
    group_values: list
    blocks: list  # per-group sub-meshes (unaveraged)


def partition(mesh, void_mask: np.ndarray, group_array: str | None, constant_fallback: str = "") -> SolidPartition:
    solid = mesh.extract_cells(~void_mask)
    void = mesh.extract_cells(void_mask)
    if group_array:
        codes = np.asarray(solid.cell_data[group_array])
    elif constant_fallback:
        # v0.1 Case C behaviour, kept only for byte-level regression.  The dtype
        # is fixed so the output no longer depends on the platform's C long.
        solid.cell_data[constant_fallback] = np.zeros(solid.n_cells, dtype=np.int32)
        codes = np.asarray(solid.cell_data[constant_fallback])
    else:
        codes = None
    values = list(np.unique(codes)) if codes is not None else [None]
    blocks = []
    for value in values:
        block = solid if codes is None else solid.extract_cells(codes == value)
        if block.n_cells > 0:
            blocks.append(block)
    return SolidPartition(solid, void, codes, values, blocks)


def with_display_points(mesh):
    """Cell-to-point averages for display; cell arrays are passed unchanged."""
    return mesh.cell_data_to_point_data(pass_cell_data=True)


def excavation_boundary(display_solid, void, tolerance: float):
    """Solid-side faces in contact with the void region.

    Candidate vertices are solid-surface vertices within ``tolerance`` of a
    void-surface vertex; the faces incident to them are kept.  The result keeps
    ``Source_Cell_ID`` of the solid cell that owns each face.
    """
    if void.n_cells == 0:
        return None
    solid_surf = display_solid.extract_surface()
    void_surf = void.extract_surface()
    distances, _ = KDTree(void_surf.points).query(solid_surf.points)
    return solid_surf.extract_points(distances < tolerance).extract_surface().clean()


def inner_boundary(display_solid, tolerance: float):
    """Boundary faces of the solid that do not lie on a bounding-box plane.

    For an export in which excavated zones were deleted, these are the
    excavation walls and floor.  A face is on a plane of the bounding box when
    all its vertices are within ``tolerance`` of that plane.
    """
    surface = display_solid.extract_surface()
    if surface.n_cells == 0:
        return None
    offsets, conn = polygons(surface)
    pts = np.asarray(surface.points, dtype=np.float64)
    b = np.asarray(display_solid.bounds, dtype=np.float64)
    on_plane = np.zeros(surface.n_cells, dtype=bool)
    sizes = np.diff(offsets)
    owner = np.repeat(np.arange(surface.n_cells), sizes)
    for axis in range(3):
        for bound in (b[2 * axis], b[2 * axis + 1]):
            near = np.abs(pts[conn, axis] - bound) <= tolerance
            all_near = np.bincount(owner, weights=near, minlength=surface.n_cells) == sizes
            on_plane |= all_near
    inner = surface.extract_cells(np.flatnonzero(~on_plane))
    if inner.n_cells == 0:
        return None
    return inner.extract_surface(pass_pointid=False, pass_cellid=False).clean()


def exterior_surface(part: SolidPartition, split_by_group: bool):
    """Exterior surface; with groups, internal group boundaries are retained."""
    if not split_by_group or part.group_codes is None:
        return with_display_points(part.solid).extract_surface()
    pieces = [with_display_points(block).extract_surface() for block in part.blocks]
    return pv.merge(pieces, merge_points=False)


def polygons(poly) -> tuple[np.ndarray, np.ndarray]:
    """``(offsets, connectivity)`` of the polygon cells of a PolyData."""
    cells = poly.GetPolys()
    return (vtk_to_numpy(cells.GetOffsetsArray()).astype(np.int64),
            vtk_to_numpy(cells.GetConnectivityArray()).astype(np.int64))


def _location_ids(points: np.ndarray, quantum: float) -> np.ndarray:
    q = np.round(np.asarray(points, dtype=np.float64) / quantum).astype(np.int64)
    _, ids = np.unique(q, axis=0, return_inverse=True)
    return ids.ravel()


def coincident_faces(surface, quantum: float | None = None) -> np.ndarray:
    """Boolean mask of faces whose vertex set coincides with another face.

    In a block model these are block-to-block contact faces: interior to the
    solid, but exposed by surface extraction because the blocks share no nodes.
    """
    offsets, conn = polygons(surface)
    if quantum is None:
        b = np.asarray(surface.bounds, dtype=float)
        quantum = 1e-7 * float(np.linalg.norm(b[1::2] - b[0::2]) or 1.0)
    loc = _location_ids(surface.points, quantum)[conn]
    sizes = np.diff(offsets)
    width = int(sizes.max()) if sizes.size else 0
    keys = np.full((len(sizes), width), -1, dtype=np.int64)
    col = np.arange(len(conn)) - np.repeat(offsets[:-1], sizes)
    keys[np.repeat(np.arange(len(sizes)), sizes), col] = loc
    keys.sort(axis=1)
    _, inverse, counts = np.unique(keys, axis=0, return_inverse=True, return_counts=True)
    return counts[inverse.ravel()] > 1


def _inside_solid(solid, points: np.ndarray, tolerance: float) -> np.ndarray:
    """True where a point lies inside a cell of ``solid`` (vtkProbeFilter mask)."""
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

    geometry = pv.UnstructuredGrid(solid.cells, solid.celltypes, np.asarray(solid.points, dtype=np.float64))
    geometry.cell_data["_one"] = np.ones(geometry.n_cells, dtype=np.uint8)
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(points, dtype=np.float64), deep=True))
    target = vtk.vtkPolyData()
    target.SetPoints(pts)
    probe = vtk.vtkProbeFilter()
    probe.SetInputData(target)
    probe.SetSourceData(geometry)
    probe.ComputeToleranceOff()
    probe.SetTolerance(tolerance)
    # locate cells with a cell locator: the default point-locator strategy
    # fails in block models whose blocks share no nodes
    probe.SetFindCellStrategy(vtk.vtkCellLocatorStrategy())
    probe.Update()
    out = probe.GetOutput()
    return vtk_to_numpy(out.GetPointData().GetArray(probe.GetValidPointMaskArrayName())).astype(bool)


def enclosed_faces(surface, solid, relative_offset: float = 0.02, candidates: np.ndarray | None = None) -> np.ndarray:
    """Boolean mask of surface faces that are enclosed by the solid on both sides.

    For every face, sample points (the centroid and the midpoints between the
    centroid and each vertex) are moved a small distance along the face normal
    to *both* sides.  A face is internal when every moved point lies inside
    some cell of ``solid``: one side inside its own block, the other inside a
    neighbour.  This finds block contacts whose two sides are meshed
    differently (non-conforming contacts), which a vertex-matching test misses.
    A face with any sample point outside the solid is kept as exterior.
    """
    n = surface.n_cells
    mask = np.zeros(n, dtype=bool)
    faces = np.arange(n) if candidates is None else np.flatnonzero(candidates)
    if faces.size == 0:
        return mask
    offsets, conn = polygons(surface)
    pts = np.asarray(surface.points, dtype=np.float64)
    sizes = np.diff(offsets)
    owner = np.repeat(np.arange(n), sizes)
    centroid = np.zeros((n, 3))
    np.add.at(centroid, owner, pts[conn])
    centroid /= sizes[:, None]
    normals = np.asarray(surface.compute_normals(cell_normals=True, point_normals=False, split_vertices=False,
                                                 consistent_normals=False, auto_orient_normals=False)
                         .cell_data["Normals"], dtype=np.float64)
    area = np.asarray(surface.compute_cell_sizes(length=False, volume=False).cell_data["Area"], dtype=np.float64)
    delta = relative_offset * np.sqrt(np.maximum(area, 1e-300))
    # sample points: centroid, and centroid-to-vertex midpoints
    sel = np.isin(owner, faces)
    samples = [centroid[faces]]
    sample_face = [faces]
    mids = 0.5 * (centroid[owner[sel]] + pts[conn[sel]])
    samples.append(mids)
    sample_face.append(owner[sel])
    samples = np.vstack(samples)
    sample_face = np.concatenate(sample_face)
    shift = normals[sample_face] * delta[sample_face, None]
    b = np.asarray(solid.bounds, dtype=float)
    tol = 1e-9 * float(np.linalg.norm(b[1::2] - b[0::2]) or 1.0)
    inside = _inside_solid(solid, np.vstack([samples + shift, samples - shift]), tol)
    both = inside[: len(samples)] & inside[len(samples):]
    ok = np.ones(n, dtype=bool)
    np.logical_and.at(ok, sample_face, both)
    mask[faces] = ok[faces]
    return mask


def split_internal_faces(surface, solid=None, method: str = "geometric"):
    """Return ``(outer, internal, n_internal)`` of an extracted block-model surface.

    ``coincident`` removes faces whose vertices coincide with another face
    (conforming contacts only).  ``geometric`` additionally removes faces that
    are enclosed by the solid on both sides (non-conforming contacts).
    """
    mask = coincident_faces(surface)
    if method == "geometric" and solid is not None:
        mask |= enclosed_faces(surface, solid, candidates=~mask)
    if not mask.any():  # nothing to remove: return the surface untouched
        return surface, None, 0
    outer = surface.extract_cells(np.flatnonzero(~mask)).extract_surface(pass_pointid=False, pass_cellid=False)
    internal = surface.extract_cells(np.flatnonzero(mask)).extract_surface(pass_pointid=False, pass_cellid=False)
    return outer, internal, int(mask.sum())


def count_regions(mesh) -> int:
    """Number of connected mesh regions (cells linked through shared points)."""
    return int(_regions_in_input_order(mesh).max() + 1) if mesh.n_cells else 0


def label_regions(mesh) -> int:
    """Attach connected-region numbers (e.g. 3DEC blocks) as a helper cell array."""
    mesh.cell_data[REGION] = _regions_in_input_order(mesh)
    return int(mesh.cell_data[REGION].max() + 1) if mesh.n_cells else 0


def _regions_in_input_order(mesh) -> np.ndarray:
    flt = vtk.vtkConnectivityFilter()
    flt.SetInputData(mesh)
    flt.SetExtractionModeToAllRegions()
    flt.ColorRegionsOn()
    ids = vtk.vtkIdFilter()
    ids.SetInputData(mesh)
    ids.SetCellIdsArrayName("_cid")
    ids.PointIdsOff()
    ids.Update()
    flt.SetInputData(ids.GetOutput())
    flt.Update()
    out = pv.wrap(flt.GetOutput())
    region = np.empty(mesh.n_cells, dtype=np.int64)
    region[np.asarray(out.cell_data["_cid"])] = np.asarray(out.cell_data["RegionId"])
    return region


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def section_positions(bounds, cfg_sections) -> dict[str, np.ndarray]:
    """Axis-aligned section positions for the configured placement rule."""
    axis_bounds = {"x": (bounds[0], bounds[1]), "y": (bounds[2], bounds[3]), "z": (bounds[4], bounds[5])}
    out: dict[str, np.ndarray] = {}
    step = cfg_sections.spacing
    for axis in ("x", "y", "z"):
        if axis not in cfg_sections.axes:
            continue
        lo, hi = axis_bounds[axis]
        extra = cfg_sections.positions.get(axis, [])
        if cfg_sections.placement == "explicit":
            locs = np.unique(np.asarray(extra, dtype=float))
        elif cfg_sections.placement == "integer_grid":
            locs = np.arange(int(lo), int(hi), step)
            if extra:
                locs = np.unique(np.concatenate((locs, extra)))
        else:  # interior
            span = hi - lo
            if span <= 0:
                locs = np.array([])
            else:
                local = step if span > step * 2 else max(span / 10.0, 0.1)
                locs = np.arange(lo + local, hi, local)
            if extra:
                locs = np.unique(np.concatenate((locs, extra)))
        out[axis] = locs
    return out


def _origin(axis, value):
    return [value if axis == "x" else 0, value if axis == "y" else 0, value if axis == "z" else 0]


def section_whole(display_solid, axis: str, value, min_points: int):
    """Section of one (already averaged) solid; ``None`` if too small."""
    cut = display_solid.slice(normal=axis, origin=_origin(axis, value))
    if cut.n_points > min_points and cut.n_cells > 0:
        return cut.clean()
    return None


def section_per_group(display_blocks, axis: str, value, min_points: int):
    """Section of each group separately, merged without welding group seams."""
    parts = []
    for block in display_blocks:
        cut = block.slice(normal=axis, origin=_origin(axis, value))
        if cut.n_points > min_points and cut.n_cells > 0:
            parts.append(cut)
    if not parts:
        return None
    return pv.merge(parts, merge_points=False).clean()


def section_discontinuous(display_solid, axis: str, value, min_points: int):
    """Section that merges coincident vertices only within one mesh region.

    The cut is computed without point merging; vertices are then merged when
    they coincide *and* their polygons come from the same connected region
    (``REGION``), so nodal jumps across block contacts are preserved.
    """
    plane = vtk.vtkPlane()
    plane.SetOrigin(*_origin(axis, value))
    plane.SetNormal(*{"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis])
    cutter = vtk.vtkCutter()
    cutter.SetInputData(display_solid)
    cutter.SetCutFunction(plane)
    cutter.SetLocator(vtk.vtkNonMergingPointLocator())
    cutter.Update()
    raw = pv.wrap(cutter.GetOutput())
    if raw.n_points <= min_points or raw.n_cells == 0:
        return None
    offsets, conn = polygons(raw)
    sizes = np.diff(offsets)
    region = np.asarray(raw.cell_data[REGION])
    b = np.asarray(display_solid.bounds, dtype=float)
    quantum = 1e-7 * float(np.linalg.norm(b[1::2] - b[0::2]) or 1.0)
    q = np.round(np.asarray(raw.points, dtype=np.float64)[conn] / quantum).astype(np.int64)
    owner = np.repeat(region, sizes)
    loc = np.unique(np.column_stack([owner, q]), axis=0, return_inverse=True)[1].ravel()
    # polygons that collapse to fewer than three distinct locations are dropped
    poly = np.repeat(np.arange(len(sizes)), sizes)
    distinct = np.unique(np.column_stack([poly, loc]), axis=0)[:, 0]
    keep = np.bincount(distinct, minlength=len(sizes)) >= 3
    used = keep[poly]
    _, first, new_ids = np.unique(loc[used], return_index=True, return_inverse=True)
    src_points = conn[used][first]
    kept_sizes = sizes[keep]
    faces = np.insert(new_ids.ravel(), np.r_[0, np.cumsum(kept_sizes)[:-1]], kept_sizes) if kept_sizes.size else np.zeros(0, int)
    out = pv.PolyData(np.asarray(raw.points)[src_points], faces=faces)
    for name in raw.point_data.keys():
        out.point_data[name] = np.asarray(raw.point_data[name])[src_points]
    for name in raw.cell_data.keys():
        if name != REGION:
            out.cell_data[name] = np.asarray(raw.cell_data[name])[keep]
    return out


def format_position(value) -> str:
    value = float(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


# --------------------------------------------------------------------------- #
# Mesh-quality summary used by the build report and by ``sim2web check``
# --------------------------------------------------------------------------- #
def triangle_quality(mesh, relative_area: float = 1e-12) -> dict:
    """Count zero-/near-zero-area triangles after triangulation.

    A triangle is *degenerate* when its area is below
    ``relative_area * L**2``, where ``L`` is the diagonal of the product's
    bounding box.  Their total area and the source cells they belong to are
    reported so that their effect can be judged.
    """
    tri = mesh.triangulate()
    faces = tri.faces.reshape(-1, 4)[:, 1:] if tri.n_cells else np.zeros((0, 3), dtype=int)
    if faces.size == 0:
        return {"triangles": 0, "degenerate": 0}
    p = np.asarray(tri.points, dtype=np.float64)
    area = 0.5 * np.linalg.norm(np.cross(p[faces[:, 1]] - p[faces[:, 0]], p[faces[:, 2]] - p[faces[:, 0]]), axis=1)
    b = np.asarray(tri.bounds, dtype=float)
    diag = float(np.linalg.norm(b[1::2] - b[0::2]))
    limit = relative_area * diag * diag
    bad = area <= limit
    unique_faces = np.unique(np.sort(faces, axis=1), axis=0).shape[0]
    report = {"triangles": int(len(faces)), "degenerate": int(bad.sum()),
              "criterion": f"area <= {relative_area:g} * bbox_diagonal^2", "area_limit": limit,
              "degenerate_area_fraction": float(area[bad].sum() / area.sum()) if area.sum() > 0 else 0.0,
              "duplicate_triangles": int(len(faces) - unique_faces),
              "invalid_indices": int((faces < 0).sum() + (faces >= tri.n_points).sum())}
    if bad.any() and "Source_Cell_ID" in tri.cell_data:
        report["degenerate_source_cells"] = int(np.unique(np.asarray(tri.cell_data["Source_Cell_ID"])[bad]).size)
    return report
