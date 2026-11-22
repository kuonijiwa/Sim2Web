# Case C: 3DEC discontinuous slope (70,021 blocks)

Configuration: [`sim2web.yaml`](sim2web.yaml). Input: `input/*.vtu` (Git LFS).

```bash
sim2web build examples/3dec_slope/sim2web.yaml       # writes examples/3dec_slope/site
sim2web validate examples/3dec_slope/sim2web.yaml
sim2web serve examples/3dec_slope/site
```

* Primary product: the **exterior surface** with block-to-block contact faces removed (32,800 of 917,062 extracted faces remain).
* Void identification: labels first, stress fallback; this model contains no void cells. Run `sim2web sensitivity examples/3dec_slope/sim2web.yaml` for the threshold/tolerance sweep.
* `output/model_cache/` holds the fixtures for the byte-level regression test. The current viewer reads `site/`.
