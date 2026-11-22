# Case D: FLAC3D excavation pit

The model file `input/EXC12_dis.vtu` and the published products in `site/` use Git LFS. The site includes the independent validation summary at `site/validation/validation_summary.json`.

Fetch the data, rebuild or serve the published package.

```bash
git lfs pull
sim2web build examples/flac3d_pit_case4/sim2web.yaml
sim2web validate examples/flac3d_pit_case4/sim2web.yaml
sim2web serve examples/flac3d_pit_case4/site
```

* The export contains only retained zones (excavated zones were deleted), so the
  `removed_zones` rule identifies the pit walls and floor as the boundary faces of the
  solid that are not on the faces of the model box.
* The stress order is read from the file (`XX,YY,ZZ,XY,XZ,YZ`). The unit (MPa) was
  inferred from the magnitudes and should be confirmed against the export settings.
* The file contains volume zones only; structural elements (liners, anchors, struts)
  are not part of the VTU.
