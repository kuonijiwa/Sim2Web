# Validation

`sim2web validate case.yaml` checks a built package against its source
models and writes `validation/validation_summary.json` (per stage) and
`validation/validation_pairs.csv` (one row per compared array). It exits with
status 1 if any check fails. Expected values are recomputed from the raw source
arrays inside `sim2web.validate`, without calling the build code.

Three kinds of evidence are kept apart because they establish different things.

## 1. Exact copies

Arrays that are copies of source values must equal the source-derived Float32
reference bit for bit:

* every CellData array (stress components, principal stresses, category codes)
  of every product, matched through `Source_Cell_ID`;
* every PointData array of surface products (exterior, excavation), matched
  through `Source_Point_ID`, together with the vertex coordinates.

`max_exact_nrmse_vs_float64` reports the Float32 conversion error relative to
Float64 references (normalised by each reference array's range).

## 2. Interpolated section values

Section vertices are new points. Their displacement values are compared with an
independent evaluation of the source field at the vertex coordinates
(`vtkProbeFilter`: cell location and shape functions, not the cutter's edge
interpolation). Reported per stage:

| Key | Meaning |
|---|---|
| `interpolated_arrays`, `interpolated_tuples` | number of compared section arrays and values |
| `max_interp_abs_error`, `max_interp_nrmse` | agreement at vertices located normally |
| `closest_cell_fallback_points`, `fallback_max_abs_error` | vertices on warped exterior faces that lie a few Float32 rounding steps outside every cell; evaluated in the closest cell and reported separately |
| `probe_disagreements` | vertices where the probe value differs by more than 1e-5 of the field range; these are re-evaluated inside each source cell incident to the vertex |
| `cell_restricted_max_abs_error` | error of the stored value against the best-matching incident source cell; more than 10× the threshold fails the check |
| `vertices_on_discontinuities`, `max_jump_across_discontinuity` | vertices whose incident source cells disagree (e.g. a vertex shared by two blocks at a joint), and the size of that jump |
| `magnitude_vs_vector_norm` | difference between the stored magnitude and the norm of the stored components |

The remaining differences are dominated by the Float32 storage of vertex
coordinates: a vertex moved by half a Float32 step is evaluated at a slightly
different place.

`sim2web verify-interpolation case.yaml` complements this with an analytical
check: the displacement is replaced by a linear field `u = A(x − c) + b`,
sections are generated with the same settings, and the vertex values are
compared with the exact field. The error must stay within the bound implied by
the Float32 rounding of vertex coordinates (`within_rounding_bound`).

## 3. Package consistency

* every file listed in `index.json` exists, with the recorded size and SHA-256;
* the source model still has the SHA-256 recorded at build time;
* no cell field is published as PointData, no category is averaged;
* section vertices are on their planes and carry no `Source_Point_ID`;
* every published value lies inside the range recorded in the index.

## Browser-level verification

`node benchmark/browser_benchmark.mjs --site site` opens the package in
Chromium and, after every section switch, asks each visible actor which array
and association it is coloured by and what its data range is
(`window.__SIM2WEB__.describeActors()`). The run fails the verification if
the rendered array or association differs from the index, or if rendered data
fall outside the indexed range.

## Excavation-boundary robustness

`sim2web sensitivity case.yaml --thresholds 1e-10 1e-8 1e-6 --tolerances 1e-5 1e-3`
re-identifies void cells and re-extracts the boundary for each combination and
reports void-cell count, boundary faces, area, connected regions and the
Jaccard index of the boundary's `Source_Cell_ID` set relative to the configured
baseline (and to a label-based boundary when labels exist). A plateau over
several decades of threshold indicates that void and retained cells are
separated by a clear gap in stress magnitude.

## What is not validated

* Visual appearance (colours, lighting) is not compared pixel by pixel.
* `_DisplayOnly` averages are not claimed to be accurate values.
* Results from solvers are taken as given; Sim2Web does not check the
  simulation itself.
