# Publication revision 2

This local revision preserves the three real source VTUs and geometric selection rules. It adds source identifiers, explicit display-array names, exclusion of averaged categorical point arrays, and output-derived scalar ranges. The original candidate remains separate and unchanged.

## Regenerate and validate

From the repository root with the pinned Python environment:

```sh
python -m pip install -r requirements.txt
python scripts/validate_publication.py
python -m pytest -q
npm ci
npm run build
```

The validation script regenerates the three example output trees twice, so copy any independently modified products elsewhere before running it. It writes `paper_evidence/revision_v2/summary.json`, a source-pair CSV, logs with repository-relative context, and SHA-256 output inventories.

To additionally compare geometry with a retained earlier candidate, pass `--geometry-reference PATH_TO_EARLIER_CANDIDATE`. This optional regression is not needed for source-array validation. A missing reference is recorded as untested, not as a pass.

Source_Cell_ID indexes the input VTU cells before selection. Source_Point_ID indexes input nodes and is exported on non-section surfaces only. Six stress fields are compared on every VTP output; four displacement fields are compared on primary surfaces. Group code checks use the source encoding. Section-point interpolation is not independently verified by this script.

All observed source-paired fields matched their expected Float32 representation. This does not imply zero error relative to Float64, a physically validated source solution, or generally correct excavation identification. Range-normalized errors use each reference array pair's range; constant references retain absolute errors and have no defined normalized error.

The included logs and summary document the recorded run. Timing includes processor startup, reading and writing but excludes the later validation pass. Background activity and filesystem cache were not controlled. The figure scripts and article are maintained in the accompanying manuscript package.

## Display policy

Quantitative stress stays in CellData. Point stress copies have `_DisplayOnly` suffixes and are excluded from the main selector. Averaged categories are removed from PointData before writing. Groups use discrete cell rendering. Case B's group is a single source class; Case C's Material_ID is a one-class fallback without a source category field.

Case B obtains its range from actual written products and rejects missing range metadata. Case A has black numeric scalar-bar text, a displayed numeric range and discrete category bands. None of these revisions changes the surface geometry or introduces a new reconstruction algorithm.

This is a local candidate, not a published release. Code licensing (MIT) and data licensing (CC BY 4.0) have been approved; see the root licence files. Confirm immutable version metadata and the public URL before uploading. Do not upload node_modules, Python caches or local build directories; follow the repository ignore rules. See `ENGLISH_INTERFACE.md` for the later text-only interface update; historical evidence below this package's `paper_evidence/` remains unchanged.
