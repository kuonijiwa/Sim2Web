# Windows run r4 (Codex, 2026-11-21)

Windows 11, i7-10750H, ParaView 5.13.3, Chrome 160, VTK 9.5.0, commit 722176f.
Measured while the workstation ran other tasks; durations are single wall-clock runs.

* `REPORT.md`: commands, exit codes and results of the task sections 0-7.
* `MANUSCRIPT_NUMBERS.md`: every number used in the manuscript with its source file.
* `comparison_results.{json,md}`: ParaView/Glance versus Sim2Web, M1-M11, Cases A, C, D.
* `REFERENCES.md`, `references_crossref.json`: reference check.
* `repro_scripts/`: scripts used for the measurements.

The full evidence archive (logs, traces, per-case JSON, screenshots, including
derived results of the non-public Cases D and F) is kept outside the
repository (`codex_run_2026-11-21_r4_evidence.zip`, 7.4 MB).

Code changes proposed in this run were merged with their original authorship:
Exodus files under non-ASCII paths on Windows, identical configuration hashes
for workbench and command-line builds, and the ParaView baseline for 5.13.3.
