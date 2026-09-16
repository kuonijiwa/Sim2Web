# Case B — FLAC3D slope, exac_23

`exac_23` is the spelling used by the authoritative files.  This candidate
retains that single final stage.  The primary object is the **OUTER EXPOSED
SURFACE**; the processor also writes global **SECTION** meshes.

```bash
python processing/process.py
npm run build:flac3d-slope
```

Input is `input/exac_23.vtu`; products are written beneath
`output/model_cache/exac_23/`.  The editable frontend entry component is
`frontend/src/App.vue`.

Stress uses exact CellData, material/group identifiers are categorical
CellData, and displacement fields are continuous PointData.
