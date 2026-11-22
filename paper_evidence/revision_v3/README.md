# Evidence for SimWebView 0.2.0.dev0 (revision 3)

Generated on Linux (Python 3.11.x, NumPy 1.26.4, SciPy 1.11.4, PyVista 0.46.3,
VTK 9.5.0, vtk.js 32.14.0, Vue 3.5) from the Git LFS models of the three
cases. Every number below can be regenerated with the commands given. The v0.1
evidence (Windows) is kept unchanged in `../revision_v2/`.

## 0. Correction: stress component order in Cases A and B

All three source files declare their stress components as `XX,YY,ZZ,XY,XZ,YZ`
(`ComponentName` attributes of the VTU). v0.1 read the FLAC3D Cases A and B as
`XX,YY,ZZ,XY,YZ,XZ`, swapping the two shear components XZ and YZ. Normal
components and displacements are unaffected; principal stresses are not
(`stress_order_correction.json`, all retained cells):

| Case | Array | Largest difference (% of range) | Cells differing by > 1 % of range |
|---|---|---|---|
| A | `Stress_Min_Principal` | 3.84 MPa (8.5 %) | 2.9 % |
| A | `Stress_Mid_Principal` | 10.58 MPa (76.1 %) | 25.8 % |
| A | `Stress_Max_Principal` | 7.22 MPa (56.5 %) | 22.9 % |
| B | `Stress_Min_Principal` | 0.41 MPa (5.2 %) | 2.2 % |
| B | `Stress_Mid_Principal` | 0.90 MPa (22.5 %) | 27.5 % |
| B | `Stress_Max_Principal` | 0.49 MPa (12.3 %) | 17.5 % |

In Case A the most compressive principal stress of the model is −45.15 MPa,
not −41.84 MPa as computed by v0.1.

The build now reads the order from the file or stops when an explicit order
disagrees with it, and the validator checks the order independently of the
configuration. The numbers in the following sections are for the corrected
configurations. The error was found while an independent session configured a
fourth model (`windows_codex_run.md`).

### Stress unit of Case C

The 3DEC stresses were labelled Pa in v0.1. Their vertical gradient
(0.0099 per metre, fitted to depth-binned medians of σzz) corresponds to a unit
weight of 9.9 kN/m³ if the values are MPa and 1 × 10⁻⁵ kN/m³ if they are Pa;
only MPa is physical. Cases A (21.7 kN/m³ in MPa) and B (11.6 kN/m³ in Pa) are
consistent with their labels. The values are unchanged; the label is now MPa
and every build performs this check.

## 1. Refactoring preserves the published products

With the v0.1 settings (`V01` in `tests/test_realdata.py`: interpolated section
magnitudes, internal block faces kept, no discontinuity preservation and, for A
and B, the v0.1 shear-component order), the configuration-driven
library reproduces **all 441 VTP products** of v0.1 **byte for byte**, compared
with the SHA-256 records of the published Windows run
(`legacy_regression.json`; `SIMWEBVIEW_REALDATA=1 pytest -m realdata`).

| Case | VTP products | byte-identical to v0.1 record |
|---|---|---|
| A | 133 | 133 |
| B | 156 | 156 |
| C | 152 | 152 |

On a second machine (Windows, Intel i7-10750H) 439 of 441 products were
byte-identical; the other two differ by one Float32 ULP in the maximum principal
stress of one cell whose exact eigenvalue lies 1.2 × 10⁻¹⁷ from a Float32
rounding midpoint (`windows_codex_run.md`). The regression test accepts exactly
this case and nothing else.

Running the original v0.1 scripts on Linux also reproduced the Windows hashes
for Cases A and B. For Case C they differed only in the declared type of the
constant fallback array `Material_ID` (Int64 on Linux, Int32 on Windows, from
NumPy's platform-dependent default integer); values and geometry were
identical. The library now fixes this type explicitly.

## 2. Package size and primary products (current configurations)

| Case | Source VTU (MB) | Primary product | Primary (MB) | Reduction | Sections | Complete package (MB) |
|---|---|---|---|---|---|---|
| A | 225.500 | excavation surface, 49,677 faces | 5.099 | 97.7 % | 132 | 82.913 (−63.2 %) |
| B | 107.877 | exterior surface, 38,789 faces | 3.841 | 96.4 % | 154 | 86.257 (−20.0 %) |
| C | 97.225 | exterior surface, 21,293 faces | 2.620 | 97.3 % | 151 | 132.241 (+36.0 %) |
| E | 2.738 | exterior surface, 7,920 faces | 0.338 | 87.6 % | 30 | 1.424 (−48.0 %) |

MB = 10⁶ bytes. Case C changed: v0.1 published 917,062 surface faces
(56.683 MB, 41.7 % reduction), of which 895,769 are block-to-block contact faces
inside the slope (884,262 conforming, 11,507 non-conforming;
`geometry.exterior.internal_faces: drop`). Rays cast from 3,000 random outside
directions hit the same first surface with and without these faces (2,328 hits,
largest distance difference 0.5 mm). Its sections grew
from about 85.6 to 129.6 MB because vertices of different blocks are no longer
merged at joints (section 4). The complete package is not what a browser
downloads; see section 6.

## 3. Field fidelity (`simwebview validate`, `validation_*.json`)

| Case | Exact arrays (tuples) | Mismatches | Max nRMSE vs Float64 | Interpolated section arrays (values) | Max abs. error at section vertices (m) |
|---|---|---|---|---|---|
| A | 935 (6,396,076) | 0 | 1.69 × 10⁻⁷ | 528 (2,940,016) | 2.6 × 10⁻⁷ |
| B | 1,100 (6,394,383) | 0 | 2.33 × 10⁻⁸ | 616 (3,006,676) | 2.2 × 10⁻⁷ |
| C | 916 (8,281,562) | 0 | 4.55 × 10⁻⁸ | 604 (6,228,208) | 2.4 × 10⁻⁷ |
| E (nodal stress) | 41 | 0 | – | 300 | 7.2 × 10⁻⁹ m; 0.8 Pa on MPa-level stress |

* "Exact" arrays are all CellData of all products (via `Source_Cell_ID`) and all
  PointData of surface products (via `Source_Point_ID`); all equal the
  source-derived Float32 reference bit for bit.
* Section vertex values were compared with an independent evaluation of the
  source displacement (`vtkProbeFilter`). Vertices where the probe disagreed by
  more than 10⁻⁵ of the range (A 16, B 58, C 127,122, the last almost all on
  block joints where the probe picks the neighbouring block) were re-evaluated
  inside their incident source cells. Every stored value matches an incident
  cell within 1.3 × 10⁻⁶ m (A), 1.6 × 10⁻⁸ m (B) and 6.6 × 10⁻⁷ m (C). The
  residuals are consistent with Float32 storage of vertex coordinates.
* Vertices on warped exterior faces that lie just outside every cell (A 39,
  B 4,424, C 5,034) were evaluated in the closest cell; maximum deviation
  2.4 × 10⁻⁷ m.

**Analytical check** (`simwebview verify-interpolation`,
`interpolation_analytical_*.json`): with a linear displacement field on the
real meshes, all 43 sampled sections reproduce the field within the bound set by
Float32 rounding of the vertex coordinates (max. relative error 6.8 × 10⁻¹⁶
before Float32 storage of values). Interpolating nodal *magnitudes* instead of
taking the norm of the interpolated vector misstates the magnitude by up to
0.56 % (A), 0.49 % (B) and 0.96 % (C) of its maximum; hence the new default
`sections.magnitude: vector_norm`.

## 4. Discontinuities in the 3DEC model (Case C)

The 3DEC model consists of 70,021 blocks that share no nodes; 85,664 node
locations are occupied by nodes of more than one block, and displacements of
coincident nodes differ by up to 13.8 mm (total displacement range 16.5 mm).

| Setting | Section vertices on a joint whose incident cells disagree | Largest jump at such a vertex | Magnitude vs. norm of components |
|---|---|---|---|
| v0.1 (merge coincident vertices) | 19,589 | 5.05 mm | up to 4.9 % of range |
| `preserve_discontinuities: true` | 23 (all < 0.5 µm, rounding) | 4.5 × 10⁻⁷ m | 5.8 × 10⁻⁸ of range |

(`validation_C_v01_settings.json`, `validation_C.json`.)

## 5. Robustness of the excavation boundary (`excavation_sensitivity_*.json`)

| Case | Void cells | Smallest non-zero max\|σ\| of a retained cell | Threshold range tested | Tolerance range tested | Boundary faces | Jaccard vs. baseline |
|---|---|---|---|---|---|---|
| A | 227,947 (all exactly zero stress) | 0.030 MPa | 10⁻¹⁰ … 10⁻² MPa | 10⁻⁶ … 10⁻³ m | 49,677 in all 28 runs | 1.0000 |
| B | 147,468 (all exactly zero stress) | 2,847 Pa | 10⁻¹⁰ … 10⁻² Pa | 10⁻⁵ … 10⁻² m | 11,131 in all 28 runs | 1.0000 |

In both models void cells carry exactly zero stress and the smallest retained
stress lies 6 (A) and 11 (B) decades above the configured threshold, so the
classification does not depend on the threshold within that gap. Void and
solid cells share nodes, so the contact tolerance only needs to exceed
coordinate rounding. Case C contains no void cells. No explicit excavation
labels exist in these exports; the label strategy and the label-versus-stress
agreement diagnostic are exercised by the synthetic tests
(`tests/test_pipeline.py`).

## 6. Browser performance

On the authors' Windows workstation with a GPU (Intel UHD via Direct3D 11,
Chrome 160 and Firefox 132): first image after 1.3–1.7 s, startup transfer
5.3–6.1 MB (12.6 MB for Case D), median section switch 36–117 ms, 48–60 fps
(display limited), JS heap ≤ 19.4 MiB; all 1,620 rendered-field checks passed.
Full table in `windows_codex_run.md`. The container measurements below
(`benchmark/browser_benchmark.mjs`, `browser_*.json`) used software rendering.

Three cold runs per case (fresh profile, HTTP cache disabled, prefetching off),
Chromium 153 headless, **software rendering** (llvmpipe) on a 2-core Intel Xeon
@ 2.30 GHz with 7.8 GiB RAM, viewport 1600 × 900, local HTTP server without
compression. Medians over runs; ten evenly spaced sections per axis.

| Case | Transferred before first image | Navigation → first image | Section switch, median (max) | Frame rate while rotating | JS heap after sweep | Rendered-field checks |
|---|---|---|---|---|---|---|
| A | 6.08 MB (surface + one section) | 1.29 s | 131 ms (423 ms) | 10.4 fps | ≤ 14.1 MiB | 180/180 passed |
| B | 5.52 MB | 1.24 s | 164 ms (310 ms) | 9.4 fps | ≤ 15.2 MiB | 270/270 passed |
| C | 5.29 MB | 1.22 s | 154 ms (238 ms) | 12.8 fps | ≤ 14.8 MiB | 180/180 passed |

The viewer bundle itself adds 1.38 MB (0.38 MB gzip). Frame rates here are a
lower bound set by CPU rendering; GPU measurements belong on representative
user hardware:

```bash
node benchmark/browser_benchmark.mjs --site examples/3dec_slope/site --runs 3 --out browser_C.json
```

"Rendered-field checks" query, after every section switch, the array and
association each visible actor is coloured by and its data range, and compare
them with the index.

## 6b. Case E: an open-source finite-element solver

A two-layer slope (15,360 hexahedra) generated by `examples/ogs_slope/make_mesh.py`
and solved with OpenGeoSys 6.5.9 (`SMALL_DEFORMATION`). OGS writes nodal stress
without component names; a simple-shear test (u = 0.001 z eₓ on a cube)
placed the XZ stress (= G·γ, no √2 factor) in column 6, i.e. Voigt order
`XX,YY,ZZ,XY,YZ,XZ`, which differs from the Itasca exports. The unit check
gives 16.5 kN/m³ in Pa. Validation passed: 41 exact arrays, 300 interpolated
section arrays; principal stresses on sections from the interpolated tensor
agree with the independent evaluation within 0.8 Pa.

## 7. Mesh quality of sections (`build_report_*.json`)

Criterion: triangle area ≤ 10⁻¹² × (bounding-box diagonal)² after
triangulation. Degenerate triangles: A 204 of 1,440,853; B 110 of 1,462,082;
C 705 of 1,335,296. Their share of section area is at most 1.7 × 10⁻¹⁰. No
duplicate triangles or invalid indices were found in any product. Degenerate
triangles keep valid `Source_Cell_ID` values.
