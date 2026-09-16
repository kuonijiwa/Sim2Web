# Case A — FLAC3D cavern, IV-2

This representative final-stage case produces and displays the **INNER
EXCAVATION SURFACE** and axis-aligned **SECTION** meshes.

```bash
python examples/flac3d_cavern_iv2/processing/process.py
npm run build:cavern
```

Run both commands from the repository root. Alternatively, inside this case
directory, run `python processing/process.py`; the processor resolves its data
paths from the script location. Input is `input/IV-2.vtu` and
products are written under `output/model_cache/IV-2/`.  The editable frontend
entry component is `frontend/src/App.vue`.

Stress is rendered from exact CellData where available.  PointData stress is an
optional display interpolation only.  Displacement is continuous PointData.
