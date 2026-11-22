# Case A: FLAC3D underground cavern, stage IV-2

Configuration: [`sim2web.yaml`](sim2web.yaml). Input: `input/*.vtu` (Git LFS).

```bash
sim2web build examples/flac3d_cavern_iv2/sim2web.yaml       # writes examples/flac3d_cavern_iv2/site
sim2web validate examples/flac3d_cavern_iv2/sim2web.yaml
sim2web serve examples/flac3d_cavern_iv2/site
```

* Primary product: the solid-side **excavation surface** (the cavern walls are hidden by the outer model boundary).
* Void identification: stress-based: null zones carry exactly zero stress; the smallest non-zero |σ| of a retained cell is 0.030 MPa, more than six decades above the 1e-8 threshold. Run `sim2web sensitivity examples/flac3d_cavern_iv2/sim2web.yaml` for the threshold/tolerance sweep.
* `output/model_cache/` holds the fixtures for the byte-level regression test. The current viewer reads `site/`.
