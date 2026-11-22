# Figure 2 and Figure 4 capture

Use the r7 checkout with the browser and workbench assets built. The figure capture uses Playwright against Chrome and the Sim2Web viewer. It sets the viewer state through the public share-link hash and injects the figure-specific CSS at capture time.

In the workstation's existing Sim2Web Python environment, install `reportlab` and `pypdf` in a separate target and set `SIM2WEB_R7_PDF_LIB` to that directory. `prepare_views.py` also uses the existing NumPy, SciPy and PyVista. The print script uses the Arial Bold font installed with Windows.

```powershell
$r7 = 'C:/swv_r7_20261121'
$py = 'C:/swv_r4_20261121/venv/Scripts/python.exe'
$sim = 'C:/swv_r4_20261121/venv/Scripts/sim2web.exe'
$env:SIM2WEB_R7_PDF_LIB = "$r7/python_lib"
New-Item -ItemType Directory -Force -Path "$r7/out", "$r7/caseE/input"
& $py -m pip install --target "$r7/python_lib" reportlab pypdf
npm run build
Copy-Item examples/ogs_slope/input/slope_result_ts_1_t_1.000000.vtu "$r7/caseE/input/ogs_slope.vtu"
& $sim gui "$r7/caseE" --port 18795 --no-browser
```

Run these from a second shell with the same `$r7`, `$py` and `SIM2WEB_R7_PDF_LIB`. The Figure 2 script follows the real UI walkthrough, including reading the VTU, clearing the ordering error, building and independently validating. Use a fresh project for a replay of panel (a).

```powershell
node benchmark/figures_r7/capture_workbench.mjs http://127.0.0.1:18795/workbench/ "$r7/caseE/input/ogs_slope.vtu" "$r7/out"
& $py benchmark/figures_r7/prepare_views.py C:/swv_r4_20261121/model_runs $r7
node benchmark/figures_r7/capture_viewers.mjs "$r7/view_states_local.json" "$r7/out"
& $py benchmark/figures_r7/compose_print.py "$r7/out" paper_evidence/revision_v5/figures_r7
```

`prepare_views.py` expects each existing A–F package at `<model_runs>/<case>/site`. Camera and browser scratch files, the input data and the built sites belong in the local working directory. The publication figures and layout checks are in `paper_evidence/revision_v5/figures_r7/`.
