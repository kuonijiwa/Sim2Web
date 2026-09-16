# English interface update — 2026-09-16

This update translates the FLAC3D and 3DEC slope viewers' controls, field labels,
status messages and comments. The cavern viewer was already in English. All
three HTML entry points now declare English. Processor comments, docstrings and
console messages are English. Slope field buttons wrap long labels and expose
their full label as a tooltip. Stress labels explicitly identify cell data.

Array identifiers, relative data paths, stage names (`IV-2`, `exac_23`,
`slopemodel`), units, extraction rules and numerical operations are unchanged.
The 3DEC default surface opacity remains 100%. No model was regenerated for
this update. Python syntax-tree comparisons exclude only docstrings and print
message text, preserving expressions inside formatted messages.

The numerical logs, hashes and screenshots in `paper_evidence/revision_v2/`
are historical evidence from the earlier candidate and are retained byte for
byte. They may contain Chinese messages or UI labels. They are not screenshots
of this English-interface update and have not been relabelled or retouched.

MIT and CC BY 4.0 were approved for code and example data respectively, with the
copyright name HydroChina Itasca. No repository or archival record has been
published by this packaging step.

## Verification

- All 32 Python tests passed, including six English-release checks.
- All three Vite production builds passed using the existing installed locked
  dependency set (Node 22.12.0, Vite 6.4.3). This was not a fresh online npm
  installation. Vite reported its existing large-bundle advisory.
- Local browser inspection at 1280 x 720 loaded all three real models and
  reached Ready. FLAC3D slope principal-stress selection updated the English
  legend. 3DEC principal-stress and X-section selection updated the displayed
  field and section position. The 3DEC initial opacity was 100%.
- Long slope field labels wrap without truncation; the control panel scrolls
  vertically at this viewport size. This is a desktop smoke check, not an
  exhaustive browser, mobile, or numerical validation campaign.
- New upload packaging checks compare retained inputs, outputs and historical
  evidence byte-for-byte with the previous upload copy.
