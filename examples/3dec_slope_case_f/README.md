# Case F: 3DEC Kala slope

The model in `input/kala_final.vtu` and the published products in `site/` use Git LFS. The site includes the independent validation summary at `site/validation/validation_summary.json`.

The build drops geometrically matched internal contacts from the exterior. It keeps discontinuous values across block interfaces in the sections. The VTU names the stress components and stores stress in MPa.

```bash
git lfs pull
sim2web build examples/3dec_slope_case_f/sim2web.yaml
sim2web validate examples/3dec_slope_case_f/sim2web.yaml
sim2web serve examples/3dec_slope_case_f/site
```
