# Comparison with a generic ParaView → Glance workflow

Reviewer 2 asked for a comparison with ParaView, ParaView Glance and
ParaViewWeb. This protocol makes it measurable. The question is not which
renderer is faster. It is what a careful user gets when they share the same
staged excavation result with general-purpose tools, and what it costs them.

## Cases

* **Case A** (FLAC3D cavern, `examples/flac3d_cavern_iv2`): excavation surface,
  stress-based void rule, Itasca component order.
* **Case C** (3DEC slope, `examples/3dec_slope`): block model with internal
  contact faces.
* **Case D** (FLAC3D pit, `examples/flac3d_pit_case4/input/EXC12_dis.vtu`):
  zones removed before export.

## Task given to both workflows

Produce a package that a colleague without either tool can open in a browser
and that shows:
1. the primary surface (excavation surface for A, exterior surface for C and D);
2. displacement magnitude and minimum, intermediate and maximum principal stress;
3. sections normal to x, y and z at the positions Sim2Web uses (the `value`
   entries in `site/model_cache/index.json`).

## Generic workflow (ParaView GUI, Python trace on)

ParaView 5.13 with default filter settings. Start **Tools → Start Trace**
before loading and stop it after exporting. Steps:

* load the VTU;
* remove null zones (Threshold on the largest absolute stress component, or
  on the null label);
* Extract Surface;
* Tensor Principal Invariants;
* one Slice per section position;
* File → Export Scene (vtkjs or Glance HTML).

Then open the export in ParaView Glance in Chromium.
`benchmark/paraview_baseline.py` performs the same pipeline in pvpython and
can be used to check the GUI result. It is not a substitute for the trace.

## Sim2Web workflow

`sim2web gui` with the shipped configuration's choices made in the workbench,
or `sim2web build` and `sim2web validate` with the shipped `sim2web.yaml`.

## Measurements

| # | Quantity | Generic workflow | Sim2Web |
|---|----------|------------------|---------|
| M1 | user operations | lines of the ParaView Python trace (filters, property changes, export) | lines changed in `case.yaml` relative to the draft, or workbench actions |
| M2 | elapsed time to package (wall clock, same machine) | from loading to the exported file | build (+ validate, reported separately) |
| M3 | package size: primary surface, whole package | bytes on disk | `build_report.json` |
| M4 | first image in Chromium, field switch, section switch | Glance, manual stopwatch or Performance panel | `benchmark/browser_benchmark.mjs` |
| M5 | principal stresses: largest error and cells with false tension | `benchmark/paraview_principal_check.py` (same VTK filter) | 0 (validated) |
| M6 | declared stress unit consistent with gravity | not checked | `stress_unit_check` |
| M7 | excavation surface separated from outer boundary | yes/no, and how (manual clip?) | layer `excavation` |
| M8 | internal faces in the exterior (Case C, D) | faces and bytes of Extract Surface | after `internal_faces` |
| M9 | values traceable to source cell/node | yes/no | `Source_Cell_ID`, `Source_Point_ID`, probe |
| M10 | sections available to the recipient | number exported, can the recipient step through them | all, slider |
| M11 | independent check of published values | none | `validation_summary.json` |

## Results available already (computed here, 2026-11-21)

M5 uses the VTK class behind ParaView's filter, so it was run without ParaView.
`vtkTensorPrincipalInvariants` reads six-component arrays in VTK order
(XX, YY, ZZ, XY, YZ, XZ) and ignores the `ComponentName` attributes. Itasca
writes XX, YY, ZZ, XY, XZ, YZ and names the components accordingly.

| Case | Min principal: max error | Mid: max error | Max: max error | Cells with false tension (σ₁ > 0 only in the generic result) |
|------|---------------------------|----------------|----------------|-------------------------------------------------------------|
| A | 3.84 MPa (8.5 % of range) | 10.58 MPa (76.1 %) | 7.22 MPa (56.5 %) | 14,711 of 983,438 retained cells |
| B | 0.41 MPa (5.2 %) | 0.90 MPa (22.5 %) | 0.49 MPa (12.3 %) | 16,668 |
| C | 14.6 MPa (6.9 %) | 36.3 MPa (30.4 %) | 21.7 MPa (28.3 %) | 19,608 |

Case B is exported in Pa; the errors above are converted to MPa
(406,572 Pa, 899,114 Pa, 492,542 Pa).

The generic minimum principal stress of Case A (−41.84 MPa) is the value of
the v0.1 package. The v0.1 scripts made the same assumption as the generic
filter, and Sim2Web 0.2 detects the mismatch from the file. Files:
`paraview_principal_case{A,B,C}.json`.

M8 for Case C: extracting the surface without removing internal faces gives
917,062 faces (56.7 MB, 58 % of the VTU). Sim2Web publishes 21,293 faces
(2.6 MB) with the same visible surface (rays from 3,000 random outside
directions hit the same first surface). For the 75 MB 3DEC model of case5 the
corresponding numbers are 693,022 faces (42.9 MB) and 19,394 faces (2.35 MB),
with 778 of 778 first hits identical. (An earlier version of this file gave
the case5 numbers under Case C; corrected after the r4 run.)

## Results of the Windows run (r4)

Same workstation for both workflows; see `windows_r4/`.

| | A | C | D |
|---|---|---|---|
| M1 ParaView trace lines (non-blank, non-comment) / Sim2Web changed config lines, workbench clicks | 5,411 / 36, 14 | 6,192 / 17, 14 | 4,579 / 35, 14 |
| M2 pvpython pipeline / Sim2Web build / Sim2Web validate (s) | 194.5 / 99.6 / 122.1 | 364.3 / 101.6 / 344.3 | 165.2 / 144.5 / 81.5 |
| M3 Glance HTML / Sim2Web site (MB) | 256.3 / 84.5 | 440.6 / 133.9 | 200.2 / 62.8 |
| M4 first frame, median of 3 (ms), Glance / Sim2Web | 31,214 / 2,869 | 49,043 / 2,662 | 23,636 / 3,686 |
| M5 cells tensile only in the generic result | 14,711 | 19,608 | 3,808 |
| M7 extra operations to separate the excavation surface | 4 | 0 | 3 |
| M8 exterior faces, ParaView / Sim2Web | 51,973 / (primary: excavation, 49,677) | 917,062 / 21,293 | 105,508 / 20,293 |
| M10 sections | 132 / 132 | 151 / 151 | 112 / 112 |
| M11 validation | — / passed | — / passed | — / passed |

With one extra operation that moves the file's XZ and YZ components into
VTK's positions, the generic principal stresses agree with Sim2Web to
double-precision rounding. The error is purely the component order.

## Reporting rules

* Report every number together with the ParaView version, the machine and
  the trace file.
* When the generic workflow can achieve something only by a manual extra
  step (reordering components with a Calculator, clipping the outer boundary),
  count that step in M1. Report the result both with and without the step.
* Do not tune either workflow beyond the defaults and the shipped configuration.
