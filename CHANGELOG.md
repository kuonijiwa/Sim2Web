# Changelog

## 0.2.0.dev0 — unreleased

### Workbench

- `sim2web gui [PROJECT]`: local processing workbench (open model, fields and
  units, geometry and excavation, sections, build and validate, publish and
  export) that edits `case.yaml`, runs the library and shows the package in
  the published viewer. Standard-library server, Vue interface
  (`workbench/`), docs in `docs/WORKBENCH.md`.

### Fixes and additions after the Windows run of 2026-11-21 (r3)

- `removed_zones`: faces of mesh interfaces without shared gridpoints (rock on
  both sides) are removed from the excavation surface (Case D: 11,710 faces
  below the pit floor). New default `exterior.internal_faces: auto`.
- Sections exactly on a plane of element faces no longer produce empty pieces
  that stopped the build.
- `convert`: Exodus II through VTK (time step selection, element blocks,
  undeformed mesh), assembly of separate component arrays into vectors and
  tensors with component names. Renaming no longer corrupts array values
  (the renamed array pointed to released memory).
- Abaqus exporter: last step with frames, nodal-stress fallback, exit code 2
  on an empty export.
- Documentation: install solvers such as OpenGeoSys in their own environment.

### Renamed to Sim2Web

- Package, command, configuration schema (`sim2web-config/1`), index schema
  (`sim2web-index/2`) and viewer API (`window.__SIM2WEB__`) now use the name
  Sim2Web. The old names are still accepted: `simwebview` is a command alias,
  `simwebview-config/1` and `simwebview-index/2` files are read, and
  `window.__SIMWEBVIEW__` points to the same API.


### Reusable library instead of per-case scripts
- New installable package `simwebview` (`src/simwebview`, replaces the
  96-line `geosimvis` helper) with modules for configuration, field contract,
  void identification, geometry, writing, validation and diagnostics.
- One declarative YAML configuration per model replaces the three case
  processors. Every option that differed between the v0.1 scripts (stress
  component order, null threshold, contact tolerance, averaging scope, section
  placement and filtering) is an explicit, validated setting.
- Command-line interface: `build`, `validate`, `sensitivity`,
  `verify-interpolation`, `inspect --draft-config`, `serve`, `install-viewer`;
  `--set key=value` overrides.
- Multi-stage packages (list or glob of VTU files) with per-stage and global
  ranges.
- Deterministic `index.json` (schema `simwebview-index/2`) with field metadata,
  file sizes and SHA-256 hashes; timings and diagnostics go to a separate
  `build_report.json`.

### One data-driven viewer
- The three per-case `App.vue` files are replaced by one viewer (`viewer/`)
  that builds its controls from the index: stages, grouped fields with units and
  association, colour maps, band count, full/P5–P95/custom ranges, layers with
  opacity, sections with slider and keyboard stepping, click-to-probe with exact
  values and source IDs, PNG export, shareable view links, performance panel,
  and an automation API (`window.__SIMWEBVIEW__`).

### Correctness
- **Stress component order of the FLAC3D cases.** The VTU files of all three
  cases declare their stress components as `XX,YY,ZZ,XY,XZ,YZ`
  (`ComponentName` attributes). v0.1 read the FLAC3D cases A and B as
  `XX,YY,ZZ,XY,YZ,XZ`, swapping the XZ and YZ shear components. Normal stress
  components and displacements were unaffected; principal stresses were not.
  In Case A the most compressive principal stress reaches −45.15 MPa instead of
  the published −41.84 MPa, and in individual cells the intermediate and maximum
  principal stresses differ by up to 76 % and 57 % of their ranges; in Case B
  the largest differences are 5 %, 22 % and 12 % of the ranges. The order is now
  read from the file (`order: from_file`) or checked against it, and the
  validator checks it independently of the build configuration. Found by an
  independent Codex reproduction of a new model (Case D).
- v0.1 behaviour is reproduced byte for byte when requested
  (`tests/test_realdata.py`): all 441 v0.1 VTP products of the three cases.
- Displacement magnitude on section vertices is now the norm of the
  interpolated vector (`sections.magnitude: vector_norm`); v0.1 interpolated
  nodal magnitudes, which differed by up to 0.52 % of the range in Case B.
- Block models: `exterior.internal_faces` removes block-to-block contact faces
  from the exterior surface (Case C: 884,262 of 917,062 faces; primary product
  56.7 MB → 4.3 MB), and `sections.preserve_discontinuities` keeps vertices of
  different blocks apart at joints (v0.1 merged 62 % of Case C section vertices
  across blocks, mixing displacements that differ by up to 13.8 mm).
- The fallback group array of Case C is written with a fixed Int32 type; v0.1
  produced Int32 on Windows and Int64 on Linux.

- **Stress unit of Case C.** The 3DEC stresses were labelled Pa in v0.1, but
  their vertical gradient (0.0099 per m) corresponds to 9.9 kN/m³ only if the
  values are MPa (1 × 10⁻⁵ kN/m³ if Pa). The values are unchanged; the unit is
  now MPa, and `inspect`/`build` check units against the gravity gradient.
- **Block contacts.** Internal faces are now recognised geometrically (points
  just off both sides inside the solid), which also removes non-conforming
  contacts: Case C exterior 32,800 → 21,293 faces, 4.30 → 2.62 MB (v0.1: 56.7 MB).

### Other solvers
- Nodal (PointData) stress supported end to end; principal stresses on sections
  from the interpolated tensor.
- `simwebview convert` (meshio: Exodus, MED, XDMF, Gmsh, ...), quadratic cells
  reduced to corner nodes, component names stamped on arrays.
- `tools/abaqus_odb_to_vtu.py` for Abaqus results (tested against a mock of the
  odbAccess API only).
- Case E: OpenGeoSys 6.5.9 slope, generated and solved from the repository; the
  OGS stress order (Voigt, XX,YY,ZZ,XY,YZ,XZ) was determined with a simple-shear test.
- Configuration errors are reported without a traceback; empty `--set key=` allowed.

### New in response to the Case D reproduction
- `excavation.strategy: removed_zones` for exports from which the excavated zones
  were deleted.
- `inspect` reports component names and writes `order: from_file` when the file
  names them; with `--draft-config`, stdout stays valid JSON (message on stderr).
- The v0.1 regression test reports every mismatching product and accepts a
  product whose only difference is a 1-Float32-ULP change of a principal stress
  (observed on a second Windows machine; see `paper_evidence/revision_v3`).

### Validation and diagnostics
- Independent validator: exact checks of all CellData and surface PointData,
  independent interpolation check of section vertices (probe plus
  incident-cell evaluation), package hashes, associations and ranges.
- Excavation diagnostics in every build (stress histogram of void and retained
  cells, near-threshold retained cells, label agreement) and a sensitivity
  sweep command.
- Analytical linear-field check of section interpolation.
- Browser benchmark and browser-level verification
  (`benchmark/browser_benchmark.mjs`).
- Tests on synthetic models with known answers; CI on Linux, Windows and macOS.

### Migration from v0.1
- `python examples/<case>/processing/process.py` → `simwebview build examples/<case>/simwebview.yaml`.
- `npm run build:<case>` → the viewer is copied into each package by `simwebview build`.
- The frozen v0.1 processors are kept in `legacy/v0_1/` for regression only;
  the published v0.1 products remain in `examples/*/output/model_cache`.

## SimWebView display-name alignment — 2026-09-16 (prepared for upload)

- Adopted SimWebView as the software display name and aligned the README,
  citation metadata and data-credit example with the submission manuscript.
- Added the confirmed repository URL and Git LFS upload instructions.
- Retained the internal Python/npm package names; updated repository links to
  SimWebView after the owner confirmed the GitHub repository rename.
- Numerical software version remains 0.1.0-alpha.0, publication revision 2;
  this documentation-only update does not regenerate models or change code.
- Historical evidence is preserved, including its original names and images.

## 0.1.0-alpha.0 — 2026-09-04

- Frozen exactly three user-supplied 3D examples: FLAC3D cavern IV-2,
  FLAC3D slope `exac_23`, and one 3DEC slope model.
- Removed the staged 2D package and all non-final 3D stages from this candidate.
- Replaced workstation paths with case-relative input/output paths.
- Preserved exact CellData stress and discrete categorical rendering.
- Set the 3DEC outer shell default opacity to 100%.
- Added editable Vue/Vite source, static-server/IIS guidance, and closure tests.
