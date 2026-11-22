# Case E: OpenGeoSys slope (open-source solver)

A two-layer slope (160 m × 60 m, crest 60 m, toe 20 m, weak layer dipping out
of the slope) under gravity, solved with the open-source finite-element code
OpenGeoSys 6.5.9 (`SMALL_DEFORMATION`, linear elasticity, 15,360 hexahedra).
Unlike the Itasca cases, stress is **nodal** (PointData) and written in Voigt
order without component names.

Install OpenGeoSys in its **own** virtual environment. The `ogs` wheel
requires numpy 2, which breaks the scipy pinned in `requirements.txt` when
both are installed together (seen in the Windows run of 2026-11-21). Sim2Web
only reads the VTU files the solver writes, so the two environments never
need to share packages:

```bash
python -m venv .venv-ogs && .venv-ogs/bin/pip install ogs==6.5.9 pyvista   # Windows: .venv-ogs\Scripts\pip
.venv-ogs/bin/python examples/ogs_slope/make_mesh.py
(cd examples/ogs_slope && ../../.venv-ogs/bin/ogs slope.prj -o input)
# in the Sim2Web environment:
sim2web build examples/ogs_slope/sim2web.yaml
sim2web validate examples/ogs_slope/sim2web.yaml
```

The solve takes about 3 minutes with the direct solver.
