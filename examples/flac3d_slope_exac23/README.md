# Case B: FLAC3D slope, state `exac_23` (identifier as spelled in the source file)

Configuration: [`sim2web.yaml`](sim2web.yaml). Input: `input/*.vtu` (Git LFS).

```bash
sim2web build examples/flac3d_slope_exac23/sim2web.yaml       # writes examples/flac3d_slope_exac23/site
sim2web validate examples/flac3d_slope_exac23/sim2web.yaml
sim2web serve examples/flac3d_slope_exac23/site
```

* Primary product: the **exterior surface**; the contact with the excavated zones is a supplementary layer.
* Void identification: stress-based; the smallest non-zero |σ| of a retained cell is 2,847 Pa, about eleven decades above the 1e-8 Pa threshold. Run `sim2web sensitivity examples/flac3d_slope_exac23/sim2web.yaml` for the threshold/tolerance sweep.
* `output/model_cache/` holds the fixtures for the byte-level regression test. The current viewer reads `site/`.
