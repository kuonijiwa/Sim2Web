# Configuration and input checklist

A case is described by one YAML (or JSON) file. Paths are relative to that
file. Unknown keys are rejected, so a misspelt option is reported instead of
being ignored. `sim2web inspect model.vtu --draft-config case.yaml` writes a
starting point; every line it marks `REVIEW` needs a decision by the analyst.

Any option can be overridden from the command line, for example
`sim2web build case.yaml --set sections.spacing=5 --set viewer.bands=12`.
Overrides are recorded in the configuration hash stored in `index.json`.

## Input checklist

Before configuring a new model, confirm the following. Sim2Web cannot infer
them from the file.

| Item | What to check | Configuration |
|---|---|---|
| File format | VTK XML unstructured grid (`.vtu`) with linear 3D cells (tetrahedra, hexahedra, wedges, pyramids) | `input.stages` |
| Displacement | a 3-component **PointData** array; its unit | `fields.displacement` |
| Stress | a 6-component array: **CellData** (zone/element stress, e.g. Itasca) or **PointData** (nodal stress, most FE codes); its **component order**; unit; sign convention | `fields.stress` |
| Categories | string or integer CellData (groups, materials, plastic state) to show as discrete classes | `fields.categories` |
| Voids | how excavated cells are represented: a label (e.g. `null`), zero stress, or a flag array | `geometry.excavation` |
| Discontinuities | whether neighbouring regions share nodes (continuum) or not (block/DEM models) | `geometry.exterior.internal_faces`, `sections.preserve_discontinuities` |
| Length unit | model coordinates in metres unless stated | `viewer.length_unit` (display only) |

**Stress-component order.** VTK files can name the components of an array
(`ComponentName0="XX" …`); Itasca's VTU export does. Use `order: from_file` to take
the order from these names (the default, and what `inspect --draft-config` writes
when they exist). An explicit order is checked against the file's names and the
build stops if they disagree; `sim2web validate` repeats this check
independently of the build. Accepted orders:

| `order` | Typical source |
|---|---|
| `from_file` | any file whose stress array carries `ComponentName` attributes |
| `XX,YY,ZZ,XY,XZ,YZ` | Itasca FLAC3D and 3DEC VTU exports (as declared in the example files) |
| `XX,YY,ZZ,XY,YZ,XZ` | Voigt order used by several FE codes |
| `XX,YY,ZZ,XY,YZ,ZX` | Voigt-type order (ZX is the same component as XZ) |

Declaring the wrong order changes the principal stresses, not the normal
components. Sim2Web v0.1 assumed `XY,YZ,XZ` for the FLAC3D cases although the
files declare `XY,XZ,YZ`; see `CHANGELOG.md` for the effect.

**Stress unit.** `inspect` and `build` compare the declared unit with the
vertical stress gradient: under gravity |σzz| grows by the unit weight
(5–30 kN/m³) per metre, so Pa, kPa and MPa differ by factors of 1,000 and the
order of magnitude decides. `build` warns when the declared unit is implausible
(`fields.stress.unit_check: false` disables the check, e.g. for models without
gravity).

Units and signs are never changed. Principal stresses are sorted
algebraically: with the compression-negative convention of FLAC3D and 3DEC,
the most compressive principal stress is `Stress_Min_Principal`.

## Minimal example

```yaml
schema: sim2web-config/1
title: "Tunnel portal, stage 4"
input:
  stages:
    - {file: results/stage4.vtu, name: stage4}
fields:
  displacement: {name: Displacement, unit: m}
  stress: {name: Stress, order: from_file, unit: Pa, sign_convention: "tension positive"}
  categories:
    - {name: "Group Slot : Default", label: "Material", labels: {"1": "Granite", "2": "Fault gouge"}}
geometry:
  primary: excavation
  excavation: {enabled: true, strategy: labels_then_stress, null_threshold: 1.0e-6, contact_tolerance: 1.0e-3}
sections: {axes: [x, y, z], spacing: 10}
```

Several stages are given either as a list or as a glob:

```yaml
input:
  glob: results/stage_*.vtu     # natural order: stage_2 before stage_10
```

## Option reference

### `input`

| Key | Default | Meaning |
|---|---|---|
| `stages` | – | list of `{file, name, label}`; `name` defaults to the file stem |
| `glob` | – | alternative to `stages`; pattern relative to the configuration |
| `sort` | `natural` | ordering of globbed files: `natural` or `name` |

### `output`

| Key | Default | Meaning |
|---|---|---|
| `dir` | `site` | static package directory |
| `cache` | `model_cache` | sub-directory with `index.json` and the VTP products |
| `viewer` | `true` | copy the bundled viewer (`index.html`, `assets/`) into `dir` |

### `fields`

| Key | Meaning |
|---|---|
| `displacement.name`, `.unit` | source vector array; yields `TotalDisplacement`, `X_Disp`, `Y_Disp`, `Z_Disp` (PointData) |
| `stress.name`, `.order`, `.unit`, `.sign_convention` | source tensor array; yields `Stress_XX/YY/ZZ` and `Stress_Min/Mid/Max_Principal` (CellData); `order` defaults to `from_file` |
| `stress.check_file_order` | `true`: stop when an explicit `order` disagrees with the file's component names |
| `categories[]` | `{name, label, labels}`; yields integer codes `<name>_ID` (CellData) from the sorted unique values; `labels` maps raw values to legend text |
| `extra[]` | `{name, association: cell or point, label, unit}`; further scalar arrays published unchanged |

### `geometry`

| Key | Default | Meaning |
|---|---|---|
| `primary` | `exterior` | main browser object: `exterior` or `excavation` |
| `exterior.enabled` | `true` | extract the boundary of the retained solid |
| `exterior.split_by_group` | `true` | one surface per group, so internal group boundaries are kept |
| `exterior.internal_faces` | `auto` | faces with solid on both sides (block contacts, zones generated without merged gridpoints): `auto` drops them when the solid has more than one connected mesh region and otherwise leaves the surface unchanged; `keep`, `drop`, or write them as a separate `layer`. With `excavation.strategy: removed_zones` such faces are always removed from the excavation surface |
| `exterior.internal_faces_method` | `geometric` | `geometric`: a face is a contact when points just off both of its sides lie inside the solid (finds conforming and non-conforming contacts); `coincident`: only faces that match another face vertex for vertex |
| `excavation.enabled` | `false` | extract the solid-side boundary of void cells |
| `excavation.strategy` | `labels_then_stress` | `labels`, `stress`, `labels_then_stress`, `field` or `removed_zones` |
| `excavation.null_threshold` | `1e-8` | `stress`: a cell is void when all six components are below this magnitude (native units) |
| `excavation.label_fields` | declared categories | `labels`: arrays searched for the tokens |
| `excavation.label_tokens` | `[null, excavated]` | case-insensitive substrings that mark void cells |
| `excavation.void_field` | – | `field`: CellData array, non-zero for void cells |
| `excavation.contact_tolerance` | `1e-3` | distance (model units) within which a solid-surface vertex counts as touching the void |
| `excavation.near_null_factor` | `100` | diagnostic: retained cells below `factor × threshold` are reported as at risk |
| `excavation.required` | `false` | fail if no void cell is found |
| `groups.field` | – | declared category that partitions the solid (exterior split, per-group averaging) |
| `groups.constant_fallback` | – | v0.1 compatibility only |
| `display_averaging` | `per_group` | cell-to-point averaging for `_DisplayOnly` copies: `per_group` or `whole_solid` |

### `sections`

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | generate sections |
| `axes` | `[x, y, z]` | section normals |
| `spacing` | `10` | distance between sections |
| `placement` | `integer_grid` | `integer_grid`: `int(min)`, `+spacing`, … `< max`; `interior`: `min+spacing`, … `< max`; `explicit`: only `positions` |
| `positions` | – | per-axis extra (or, with `explicit`, the only) positions |
| `min_points` | `10` | skip sections with this many points or fewer |
| `magnitude` | `vector_norm` | displacement magnitude on section vertices: norm of the interpolated vector, or `interpolated` nodal magnitudes (v0.1) |
| `preserve_discontinuities` | `false` | do not merge coincident vertices of different connected mesh regions (blocks) |

### `viewer`

| Key | Default | Meaning |
|---|---|---|
| `title`, `subtitle` | case title | page and panel heading |
| `default_field`, `default_axis` | first field / first axis | initial selection |
| `colormap` | `jet` | `jet`, `viridis`, `turbo`, `coolwarm`, `grayscale` |
| `bands` | `8` | number of colour bands for continuous fields |
| `range_mode` | `full` | `full` or `p5_p95` (values outside are clamped to the end colours, not changed) |
| `background` | white | RGB in 0–1 |

## Other solvers and formats

Sim2Web reads VTU. For other formats:

```bash
sim2web convert result.e result.vtu                       # Exodus: last time step
sim2web convert result.e result.vtu --time '#3'           # step index 3 (or --time first, --time 2.5)
pip install "sim2web[convert]"                            # meshio, for the formats below
sim2web convert result.med result.vtu --component-names S=XX,YY,ZZ,XY,YZ,XZ --rename U=Displacement
```

* **Exodus II** (MOOSE, Cubit, Sierra) is read with VTK's own reader and needs
  no extra package. Every time step is available (`--time`, default the last
  one), element blocks are combined into one mesh and kept as the category
  `ElementBlock`, and the mesh is **not** moved by the displacement field.
* **Other formats** go through meshio (MED from Code_Aster/Salome, XDMF from
  FEniCS, Gmsh, Nastran, legacy VTK); these files hold one state.
* Separate component arrays are assembled into one array whose component names
  come from the suffixes: `disp_x, disp_y, disp_z` become `disp` (X, Y, Z) and
  `stress_xx ... stress_xz` become `stress` (XX, YY, ZZ, XY, YZ, XZ in that
  order, whatever the order in the file). `--no-assemble` keeps them apart.
* 3D cells are kept, quadratic cells are reduced to their corner nodes, and
  `--component-names` stamps names on arrays that carry none (use the name
  before or after `--rename`).

Abaqus: `abaqus python tools/abaqus_odb_to_vtu.py job.odb job.vtu` writes nodal
`U` and stress `S` with component names from Abaqus' labels: at the element
centroid when the ODB can provide it, otherwise as nodal values (`NODAL`
output, or the average of `ELEMENT_NODAL` values). Without `--step` the last
step that has frames is used; an export that would contain no 3D continuum
element stops with exit code 2. Tested with mocks of the odbAccess API and the
R2019 crankshaft example ODB shipped with Abaqus 2020.

Nodal stress (PointData) is supported throughout: surfaces carry exact nodal
values, sections interpolate the six tensor components and compute principal
stresses from the interpolated tensor. Stress-based void criteria need cell
stress; use `labels`, `field` or `removed_zones` with nodal stress.

## Choosing the void (excavation) rule

0. **Deleted zones.** Some exports omit the excavated zones altogether (no
   void cells; the build report shows `void_cells: 0`). Use
   `strategy: removed_zones`: boundary faces of the solid that do not lie on a
   face of the model's bounding box are taken as the excavation surface. This
   assumes flat outer model boundaries; an irregular ground surface would be
   included as well.
1. **Labels first.** If the model carries an excavation label, use
   `strategy: labels`. It is exact and independent of the stress state.
2. **Zero stress.** FLAC3D null zones and 3DEC deleted zones export zero
   stress. Use `strategy: stress` with a threshold far below the smallest
   physical stress, then run `sim2web sensitivity case.yaml`: the boundary
   should not change over several decades of threshold. The build report lists
   a histogram of `log10(max|σ|)` for void and retained cells and the number of
   retained cells close to the threshold.
3. **Failure modes** of a stress rule: retained cells that genuinely carry
   near-zero stress (for example zones that failed in tension and were
   unloaded, or unloaded free blocks) are classified as void, which creates
   spurious cavities. Check `near_null_retained_cells` and the
   `label_agreement` block of `build_report.json`, and inspect the excavation
   layer in the viewer against the design geometry.
4. **Daylighting excavations.** Faces that share only a vertex with the void
   surface are included, so where an excavation reaches the model boundary a
   one-face rim of exterior faces belongs to the excavation layer.
