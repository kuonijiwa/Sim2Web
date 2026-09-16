# Publication revision evidence

This directory contains the current evidence for publication revision 2.
`summary.json` and `source_output_pairs.csv` record two-run processing and
source-to-final-output validation. `environment.json` records the observed
workstation and dependency versions. Per-case hashes support determinism checks.

The `screenshots` directory contains native browser captures from the revised
frontends and a record of the exercised controls. Earlier screenshots elsewhere
in `paper_evidence` are historical and do not document the corrected field policy
or Case B scalar range. They must not be substituted into the revised manuscript.

Numerical validation covers cell stress on every final VTP, available source group
codes, and primary-surface displacement. It does not independently validate
section-point interpolation, solver physics, or semantic surface-role selection.
Timing consists of two observed runs per case, not a controlled comparative
performance benchmark. See `docs/PUBLICATION_REVISION.md` for reproduction.
