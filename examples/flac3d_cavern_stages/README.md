# FLAC3D underground cavern construction stages

The five VTUs follow the construction order I-1, I-3, II-2, III-3 and IV-2. The viewer shares the same section-plane plan across the stages. The stress order is declared in each input file and the excavation surface uses the solid side of the stress-classified void boundary.

```bash
git lfs pull
sim2web build examples/flac3d_cavern_stages/sim2web.yaml
sim2web validate examples/flac3d_cavern_stages/sim2web.yaml
sim2web serve examples/flac3d_cavern_stages/site
```

The site includes the independent validation summary at `site/validation/validation_summary.json`.
