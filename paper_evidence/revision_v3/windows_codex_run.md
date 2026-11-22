# Independent Windows reproduction (Codex session, 2026-11-21)

An independent agent session (Codex) reproduced commit `2cb2e6b` on the
authors' Windows workstation, configured a new model (Case D) from the
documentation alone, and reported every command with exit code and output. The
full report, logs and screenshots are kept with the project files
(`codex_run_2026-11-21/REPORT.md`); this page summarises the results used in
the paper and the changes they led to.

## Environment

Windows 11 Home (Chinese), 10.0.26300; Intel Core i7-10750H (6 cores), 15.8 GiB;
GPUs NVIDIA Quadro P620 and Intel UHD (browsers used the Intel UHD through
ANGLE/Direct3D 11). Python 3.12.14, NumPy 1.26.4, SciPy 1.11.4, PyVista 0.46.3,
VTK 9.5.0; Node 24.19, Chrome 160, Firefox 132 (Playwright build). Repository and
models on a path with Chinese characters (`G:\成果\…`): reading, building and
validation worked.

## Existing cases on Windows

* Unit tests 25 passed; viewer tests 8 passed.
* Build sizes, face counts, section counts and every validation count were
  identical to the Linux results (A, B, C).
* v0.1 byte-level regression: **439 of 441** products identical. The two
  exceptions (Case C `full_model.vtp`, `slice_y_430.00.vtp`) differ only in
  `Stress_Max_Principal` of one source cell (`Source_Cell_ID` 282075) by one
  Float32 ULP (9.31870332e-08 vs 9.31870261e-08). Evaluated with 80-digit
  arithmetic, the exact eigenvalue lies 1.24 × 10⁻¹⁷ above the midpoint between
  the two Float32 neighbours; LAPACK on this CPU returned a value just below the
  midpoint. The regression test now accepts exactly this kind of difference
  (≤ 1 ULP, principal stresses only, everything else identical) and reports all
  others.

## Browser performance on a real GPU

Three cold runs per case, HTTP cache disabled, no prefetching, headed browsers,
ten sections per axis, 120 rotation frames. Medians over runs (maximum for the
worst switch).

| Case | Browser | Startup transfer | First image | Section switch, median (max) | Frame rate | JS heap after sweep |
|---|---|---|---|---|---|---|
| A | Chrome 160 | 6.08 MB | 1.49 s | 39 ms (279 ms) | 60 fps | 19.4 MiB |
| A | Firefox 132 | 6.08 MB | 1.53 s | 70 ms (336 ms) | 60 fps | – |
| B | Chrome 160 | 5.52 MB | 1.34 s | 41 ms (99 ms) | 60 fps | 16.6 MiB |
| B | Firefox 132 | 5.52 MB | 1.40 s | 74 ms (219 ms) | 60 fps | – |
| C | Chrome 160 | 5.29 MB | 1.41 s | 68 ms (129 ms) | 60 fps | 14.3 MiB |
| C | Firefox 132 | 5.29 MB | 1.59 s | 117 ms (283 ms) | 48 fps | – |
| D | Chrome 160 | 12.57 MB | 1.74 s | 36 ms (102 ms) | 60 fps | 17.0 MiB |
| D | Firefox 132 | 12.57 MB | 2.36 s | 64 ms (199 ms) | 48 fps | – |

60 fps is the display refresh limit. All 1,620 rendered-field checks passed
(array, association and range of every visible actor after every section
switch). Edge could not be started by the automation driver; no second machine
was tested.

## Case D: FLAC3D excavation pit (new model)

`EXC12_dis.vtu`: 102.9 MB, 332,510 nodes, 548,417 zones (tetrahedra, hexahedra,
wedges, pyramids), domain 150 × 150 × 111 m, one exported state. Configured
from `simwebview inspect` and the documentation without code changes.

* Primary surface 11.27 MB (110,194 faces; 89 % smaller than the VTU); 112
  sections; package 70.0 MB.
* Validation passed: 795 exact arrays (5,429,436 values), 0 mismatches; 448
  interpolated section arrays (2,083,816 values), nRMSE 3.7 × 10⁻⁷; analytical
  linear-field check within the Float32 rounding bound on 12 sections.
* The export contains **no void cells** (excavated zones were deleted). The
  sensitivity sweep shows no void cells up to a threshold of 10⁻⁴ MPa; at 10⁻²
  MPa it would misclassify 3,598 retained low-stress cells. This illustrates the
  documented failure mode of a stress criterion and led to the new
  `removed_zones` strategy (pit walls and floor from the boundary of the solid
  off the box faces).
* The file declares its stress components as `XX,YY,ZZ,XY,XZ,YZ`. Checking the
  three published files showed the same declaration, which exposed the
  shear-component swap of v0.1 in Cases A and B (`stress_order_correction.json`).
* Five connected mesh regions; with `preserve_discontinuities` the largest
  cell-restricted `Z_Disp` residual falls from 2.2 × 10⁻⁷ m to 6.0 × 10⁻¹⁰ m.

## Changes made after the run

1. Stress order read from / checked against `ComponentName` attributes; Cases A
   and B corrected; the validator checks the order independently.
2. `excavation.strategy: removed_zones`.
3. `inspect --draft-config` keeps stdout valid JSON.
4. The v0.1 regression test reports every mismatch and accepts 1-ULP
   eigenvalue rounding differences.
