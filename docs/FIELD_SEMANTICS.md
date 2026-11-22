# Field semantics

## Associations and roles

| Array | Association | Role | Rendering |
|---|---|---|---|
| `TotalDisplacement`, `X_Disp`, `Y_Disp`, `Z_Disp` | PointData | quantitative | interpolated across faces |
| `Stress_XX`, `Stress_YY`, `Stress_ZZ`, `Stress_Min/Mid/Max_Principal` | CellData (zone stress) or PointData (nodal stress), as in the input | quantitative | per cell, or interpolated for nodal stress |
| `<category>_ID` | CellData | categorical | discrete colours, never interpolated |
| `<cell field>_DisplayOnly` | PointData | display only | cell-to-point average; excluded from the field list and from validation claims |
| `Source_Cell_ID` | CellData | provenance | index of the source cell in the input VTU |
| `Source_Point_ID` | PointData | provenance | index of the source node; present only where vertices *are* source nodes (surfaces, not sections) |

Values, units and sign conventions are those of the input. Quantitative arrays
are stored as Float32; the build records the conversion and `sim2web
validate` measures it against Float64 references.

## Principal stresses

Principal values are the eigenvalues of the symmetric tensor assembled in the
declared component order, sorted algebraically: `Min ≤ Mid ≤ Max`. With the
compression-negative convention used by FLAC3D and 3DEC, the most compressive
stress (often called σ1 in rock mechanics) is `Stress_Min_Principal`. The
viewer labels them "minimum/maximum principal stress (algebraic)" to avoid this
ambiguity.

## Surfaces

Exterior and excavation surfaces consist of faces of source cells. Each face
carries the `Source_Cell_ID` of the retained cell it belongs to and copies of
that cell's quantitative and categorical values. Its vertices are source nodes
(`Source_Point_ID`), with exact copies of nodal displacement.

**Block (discontinuous) models.** Where neighbouring blocks share no nodes, as
in 3DEC, every block face is a boundary face of its block, including faces in
contact with the next block. `geometry.exterior.internal_faces: drop` removes
faces whose vertex set coincides with another face, leaving the outer surface;
`layer` publishes the contact faces separately. The default `geometric`
method also finds non-conforming contacts (the two sides meshed differently),
which a vertex-matching test misses. In Case C, 895,769 of the 917,062
extracted faces are block contacts (884,262 of them conforming); a ray-casting
check from 3,000 random directions found the first visible surface unchanged
for every ray that hit the model.

## Sections

Sections are axis-aligned planar cuts computed offline (VTK `vtkCutter`).

* **Cell values** on a section polygon are those of the source cell the polygon
  was cut from (`Source_Cell_ID`); they are exact copies.
* **Point values** on section vertices are new: each vertex lies on a cut edge
  and its value is the linear interpolation of the two edge nodes. For linear
  cell types this is the element's own interpolation, so a linear field is
  reproduced exactly (see `sim2web verify-interpolation`). Section vertices
  carry no `Source_Point_ID`.
* **Nodal stress** on section vertices is the interpolation of the six tensor
  components; principal stresses are then computed from the interpolated
  tensor, not interpolated themselves.
* **Displacement magnitude** on section vertices is, by default, the norm of
  the interpolated displacement vector (`sections.magnitude: vector_norm`).
  Interpolating nodal magnitudes instead (v0.1) gives a different value where
  the displacement direction changes along an edge; in Case B the difference
  reached 0.52 % of the magnitude range.
* **Discontinuities.** By default, coincident vertices produced by adjacent
  cells are merged. In block models this also merges vertices of different
  blocks at a joint, where displacements can differ (up to 13.8 mm in Case C,
  whose total displacement range is 16.5 mm). With
  `sections.preserve_discontinuities: true` vertices are merged only within one
  connected mesh region, so each block keeps its own nodal values.
* **Degenerate triangles.** A cut through, or very close to, existing nodes can
  produce zero- or near-zero-area triangles. The build report counts them with
  the criterion `area ≤ 1e-12 × (bounding-box diagonal)²` and reports their
  share of the section area. They carry valid `Source_Cell_ID` values, so cell
  queries are unaffected; with zero area they contribute nothing to rendering
  or to area-weighted statistics.

Why pre-computed sections? The browser receives small, finished polygon sets
and does no geometry processing, which keeps memory use and latency low on
ordinary computers and lets every published section be validated before
delivery. The cost is flexibility: only the listed positions can be shown.
Interactive cutting in the browser is possible in principle (and could also
keep cell provenance), but is not implemented.
