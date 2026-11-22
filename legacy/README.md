# Frozen v0.1 processors

These are the three case scripts of SimWebView v0.1.0-alpha.0 (commit
`9ad8901`), moved here unchanged except for how they locate their case folder.
They are **not** part of the library. They are kept so that the regression
test can show that the configuration-driven library reproduces the published
v0.1 products byte for byte:

```bash
python legacy/v0_1/flac3d_slope_exac23.py /tmp/legacy_B    # needs /tmp/legacy_B/input/*.vtu
simwebview build examples/flac3d_slope_exac23/simwebview.yaml --set sections.magnitude=interpolated \
    --set fields.stress.order=XX,YY,ZZ,XY,YZ,XZ --set fields.stress.check_file_order=false
python scripts/compare_with_legacy.py examples/flac3d_slope_exac23/simwebview.yaml /tmp/legacy_B/output/model_cache \
       --hash-record paper_evidence/revision_v2/hashes_B.json
```

The v0.1 settings are listed in `tests/test_realdata.py` (`V01`):
`sections.magnitude=interpolated`, `geometry.exterior.internal_faces=keep`,
`sections.preserve_discontinuities=false` and, for Cases A and B,
`fields.stress.order=XX,YY,ZZ,XY,YZ,XZ` with `fields.stress.check_file_order=false`
(v0.1 swapped the XZ and YZ shear components of the FLAC3D exports).
