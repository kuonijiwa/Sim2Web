# Sim2Web

**One-click post-processing and verifiable web publishing of geotechnical simulation results.**

Sim2Web turns a three-dimensional simulation result (a VTK unstructured grid
exported from FLAC3D, 3DEC or any other solver) into a static web package that a
reviewer can open in a browser: the exterior surface, the excavation boundary,
pre-computed internal sections and the physical fields on them, with every
published value traceable to the source cell or node it came from.

```text
model.vtu ─┐
case.yaml ─┴─► sim2web build ─► site/index.html + site/model_cache/{index.json, *.vtp}
                sim2web validate ─► validation_summary.json, validation_pairs.csv
```

* **One library, no per-case code.** A YAML configuration declares the input
  arrays (displacement, stress and its component order, categories), how voids
  are identified, which surfaces and sections to produce and how the viewer
  starts. Each of the seven main examples has its own configuration.
* **One data-driven viewer.** The browser application reads `index.json` and
  builds its controls from it: stages, fields (with units and point/cell
  association), layers, sections, colour scales. It needs no editing for a new
  model; titles, colour maps and defaults come from the configuration.
* **Traceable fields.** Stress and categories stay cell data and are coloured
  per cell; averaged copies for smooth display are marked `_DisplayOnly`.
  `Source_Cell_ID` and `Source_Point_ID` link every product back to the source
  mesh; clicking in the viewer shows them with the exact values.
* **Independent validation.** `sim2web validate` recomputes every published
  value from the raw source arrays and compares: exact copies bit for bit,
  interpolated section values against an independent shape-function evaluation,
  and the package files against the hashes recorded at build time.
* **Static delivery.** Any static web server (IIS, nginx, GitHub Pages, `sim2web serve`) is enough.

## Installation

```bash
python -m pip install "sim2web @ git+https://github.com/kuonijiwa/Sim2Web"
```

Python 3.10 or later. The browser viewer is bundled in released wheels; when
installing from a source checkout, build it once with Node.js 20+:

```bash
git clone https://github.com/kuonijiwa/Sim2Web && cd Sim2Web
python -m pip install -e ".[test]"
npm ci && npm run build                  # writes src/sim2web/viewer_dist and workbench_dist
```

Run `git lfs pull` for six of the seven main examples. Case E has a
repository-supplied OpenGeoSys project for generating its input.

Keep solvers and their Python packages (OpenGeoSys, FEniCS, MOOSE tools, …)
in separate environments: Sim2Web needs only the result files they write, and
solver wheels may require library versions that conflict with the pinned
`requirements.txt`.

## Quick start with your own model

```bash
sim2web inspect mymodel.vtu --draft-config case.yaml   # lists arrays, drafts a configuration
# edit case.yaml: check every line marked REVIEW (stress order, units, sign, void rule)
sim2web build case.yaml                                # writes site/
sim2web validate case.yaml                             # independent checks; exit code 1 on failure
sim2web serve site                                     # http://127.0.0.1:8000/
```

The input checklist and every configuration option are described in
[docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Example cases

| Case | Solver | Configuration | Primary product | Notes |
|---|---|---|---|---|
| A | FLAC3D | [`examples/flac3d_cavern_iv2/sim2web.yaml`](examples/flac3d_cavern_iv2/sim2web.yaml) | excavation surface | underground cavern, stress-based void identification |
| B | FLAC3D | [`examples/flac3d_slope_exac23/sim2web.yaml`](examples/flac3d_slope_exac23/sim2web.yaml) | exterior surface | slope with excavated zones; supplementary excavation contact |
| C | 3DEC | [`examples/3dec_slope/sim2web.yaml`](examples/3dec_slope/sim2web.yaml) | exterior surface | 70 021 blocks; internal block contacts removed, joint discontinuities preserved in sections |
| D | FLAC3D | [`examples/flac3d_pit_case4/sim2web.yaml`](examples/flac3d_pit_case4/sim2web.yaml) | exterior surface | deep pit with the walls and floor in a separate excavation layer |
| E | OpenGeoSys | [`examples/ogs_slope/sim2web.yaml`](examples/ogs_slope/sim2web.yaml) | exterior surface | open-source FE solver, nodal stress in Voigt order; model generated and solved from the repository |
| F | 3DEC | [`examples/3dec_slope_case_f/sim2web.yaml`](examples/3dec_slope_case_f/sim2web.yaml) | exterior surface | Kala slope with geometric contact removal and preserved discontinuities |
| Five-stage cavern | FLAC3D | [`examples/flac3d_cavern_stages/sim2web.yaml`](examples/flac3d_cavern_stages/sim2web.yaml) | excavation surface | five construction stages with common-scale fields and aligned section locations |

Two further manuscript cases use solver sample files. Follow the recipes for
[G · Abaqus crankshaft](examples/abaqus_samples/README.md) and
[H · MOOSE elastic patch](examples/moose_elastic_patch/README.md).

```bash
sim2web build examples/flac3d_cavern_iv2/sim2web.yaml
sim2web validate examples/flac3d_cavern_iv2/sim2web.yaml
sim2web serve examples/flac3d_cavern_iv2/site
```

## Workbench

```bash
sim2web gui my_project
```

opens a local processing workbench in the browser: open a model, confirm
fields and units (with the component-order and unit checks shown as you
choose), set geometry and sections, preview, build, validate and export. It
writes the same `case.yaml` the command line uses and shows the result in the
published viewer. See [docs/WORKBENCH.md](docs/WORKBENCH.md).

## Further commands

| Command | Purpose |
|---|---|
| `sim2web sensitivity case.yaml` | sweep the void threshold and contact tolerance; report boundary stability |
| `sim2web verify-interpolation case.yaml` | replace displacement by a linear field and check section values analytically |
| `sim2web convert result.e result.vtu` | convert Exodus (any time step), MED, XDMF, Gmsh, …; assemble `stress_xx …` into tensors with component names |
| `abaqus python tools/abaqus_odb_to_vtu.py job.odb job.vtu` | export an Abaqus result with named stress components |
| `sim2web build case.yaml --set sections.spacing=5` | override any option from the command line |
| `node benchmark/browser_benchmark.mjs --site site` | measure load time, section switching, frame rate and memory in Chromium, and verify the rendered field association |

## Python API

```python
from sim2web import load_config, build, validate_package

cfg = load_config("case.yaml", overrides=["sections.spacing=5"])
result = build(cfg)
report = validate_package(cfg)
assert not report["failures"]
```

Lower-level building blocks (`sim2web.fields`, `sim2web.regions`,
`sim2web.geometry`) can be used directly in custom workflows.

## Documentation

* [Manuscript evidence and reproduction scripts](paper_evidence/README.md)
* [Workbench: processing in the browser](docs/WORKBENCH.md)
* [Configuration and input checklist](docs/CONFIGURATION.md)
* [Field semantics: associations, display-only arrays, sections](docs/FIELD_SEMANTICS.md)
* [Validation: what is checked and how to read the reports](docs/VALIDATION.md)
* [Viewer: features, links, customisation, embedding](docs/VIEWER.md)
* [Deployment on IIS and other static servers](docs/IIS_DEPLOYMENT.md)

## Scope

Sim2Web reads VTK unstructured grids with linear 3D cells; other formats
are converted with `sim2web convert` or, for Abaqus, the export script in
`tools/`. Zone (cell) and nodal (point) stress are both supported. Sections are pre-computed and axis-aligned, so the
browser does no geometry processing; arbitrary interactive cutting is not
provided. Packages can contain several stages (for example construction
stages); the viewer switches between them with a common or per-stage colour
scale.

## Compatibility

Formerly SimWebView. Existing configurations and packages remain supported,
and `simwebview` is an alias for `sim2web`. See the [changes since v0.1](CHANGELOG.md).

## Licence and citation

Code and documentation: MIT. Example data: CC BY 4.0 with attribution to
HydroChina Itasca (see `DATA_LICENSE.md`). Please cite the software using
`CITATION.cff`.
