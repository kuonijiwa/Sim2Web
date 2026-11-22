# Workbench

`sim2web gui` opens a processing workbench in the browser. It walks through
the same steps as the configuration file, shows what the library finds in the
model while you choose, and displays the result in the viewer that is
published.

```bash
sim2web gui my_project          # opens http://127.0.0.1:8765/workbench/
```

The project directory holds `case.yaml` and the packages built from it. The
workbench listens on the local machine only and adds no dependency to
Sim2Web.

## Steps

| Step | What you do | What the library checks |
|------|-------------|-------------------------|
| 1 Open model | choose one or more result files (one per stage); Exodus, MED, XDMF and Gmsh files are converted to VTU first | lists every array with its components and range; drafts the settings |
| 2 Fields and units | confirm displacement, stress and category arrays, stress unit and sign convention | reads the stress component order from the file; when the file does not name the components, the build is held until an order is chosen. The vertical stress gradient is compared with the declared unit (unit weight 5–30 kN/m³) |
| 3 Geometry and excavation | main surface, internal faces, groups, excavation rule; **Preview surfaces** | counts connected mesh regions and removes faces with rock on both sides |
| 4 Sections | directions, spacing or explicit positions, discontinuities | estimates the number of sections |
| 5 Build and validate | **Build package**, **Validate** | independent recomputation of every published value; a rebuild clears the previous validation |
| 6 Publish and export | titles, colour map, length unit; **Download package (ZIP)** | — |

![Step 2: the file does not name its stress components](images/workbench_fields.png)

![Step 5: package built and validated](images/workbench_build.png)

## Reproducibility

Every change is written to `case.yaml` immediately. The workbench is an
editor of that file plus buttons that run the library on it; the commands
shown in step 6 reproduce the package without the workbench:

```bash
sim2web build case.yaml
sim2web validate case.yaml
```

Validation results are written where `sim2web validate` writes them
(`site/validation/`), so the exported ZIP carries them.

## Development

```bash
sim2web gui my_project --no-browser      # API on port 8765
npm run dev:workbench                    # interface with hot reload, forwards /api to 8765
npm run test:workbench                   # unit tests of the interface logic
node benchmark/workbench_walkthrough.mjs --url http://127.0.0.1:8765/workbench/ \
     --model path/to/model.vtu --out shots/   # scripted walk through all steps
```

The server is `src/sim2web/workbench.py` (standard library only); the
interface is `workbench/` (Vue). Its API is listed at the top of
`workbench.py`.
