# Reproducing the r6 web-slicing study

Only the public Case A and Case C configurations and grids are used. Keep generated sites, full-volume binaries and cutter reference arrays in a scratch directory outside Git.

The Windows run reused the base Sim2Web virtual environment for Python 3.12, VTK 9.5.0, PyVista and SciPy. The supplemental trame packages were installed into a separate target and appended to Python's search path, preserving the base NumPy/SciPy versions.

```powershell
$R6_WORK = 'C:/swv_r6_20261121'
$R6_PY = 'C:/swv_r4_20261121/venv/Scripts/python.exe'
$R6_SIM = 'C:/swv_r4_20261121/venv/Scripts/sim2web.exe'
$env:SIM2WEB_R6_TRAME_LIB = "$R6_WORK/trame_lib"
$env:SIM2WEB_R6_BROWSER_BUILD = "$R6_WORK/browser_dist"
& $R6_PY -m pip install --target "$R6_WORK/trame_lib" trame==4.0.0 trame-vtk==2.11.17 trame-vuetify==3.3.0 psutil==7.2.2 matplotlib==3.11.2
npm ci
npm run build
node node_modules/vite/bin/vite.js build --config benchmark/web_slicing/vite.config.mjs
$cases = @{ A='examples/flac3d_cavern_iv2/sim2web.yaml'; C='examples/3dec_slope/sim2web.yaml' }
foreach ($case in 'A','C') {
    & $R6_SIM build $cases[$case] --set "output.dir=$R6_WORK/site_$case"
    & $R6_SIM validate $cases[$case] --set "output.dir=$R6_WORK/site_$case"
    & $R6_PY benchmark/web_slicing/prepare.py $case "$R6_WORK/site_$case" "$R6_WORK/data_$case"
    node benchmark/web_slicing/check_browser.mjs "$R6_WORK/browser_dist" "$R6_WORK/data_$case" "$R6_WORK/check_$case"
    & $R6_PY benchmark/web_slicing/check_vtk.py "$R6_WORK/data_$case" "$R6_WORK/check_$case" "$R6_WORK/check_$case/correctness.json"
}
```

Verify WebSocket throttling by running the first command in one shell and the second in another. The measured workstation showed that CDP throttled WebSocket frames, so the main matrix uses CDP alone. The probe also records an optional additional frame shaper trial as a diagnostic.

```powershell
& $R6_PY benchmark/web_slicing/ws_echo.py
node benchmark/web_slicing/ws_probe.mjs http://127.0.0.1:18773 "$R6_WORK/websocket_probe.json"
```

Run the timing matrix serially in the same environment after the correctness gates pass.

```powershell
foreach ($case in 'A','C') {
    foreach ($method in 'B','W','S-local','S-remote') {
        foreach ($network in 'LAN','4G') {
            node benchmark/web_slicing/measure.mjs $R6_WORK $case $method $network $R6_PY 5 5
        }
    }
}
```

B fetches the full compressed volume payload on the page target instrumented by CDP. Transferable buffers move volume parsing, indexing and cutting to a worker. S uses the same `vtkCutter` backend for both trame display modes, with the process bound to localhost. W opens the built viewer with its public browser API, section-only visibility and prefetch disabled. The stock W viewer still transfers its primary surface during startup and retains its in-memory LRU during the five repeated sweeps. The first warm-up sweep is recorded separately.

The W HTTP harness adds an opacity-zero triangle to the served index to keep all ten depths inside the starting camera's clipping range. The built site files and viewer code stay intact. The triangle's transfer contributes to the W measurement. The S-local benchmark supplies the orthographic projection properties in the trame camera serializer. S-remote uses a 20 px corner marker to identify the section within each streamed JPEG. The browser verifies the decoded marker before accepting a remote frame.

The trial directory records the raw startup runs, switch events, sampled memory peaks, and a section screenshot. The remote completion hook reads the decoded server image. The local trame hook observes a WebGL geometry draw. All view completion markers wait for two browser animation frames.

Collect the verified matrix and render the evidence after a complete run.

```powershell
& $R6_PY benchmark/web_slicing/check_frames.py $R6_WORK
& $R6_PY benchmark/web_slicing/collect.py $R6_WORK --complete
$env:PYTHONPATH = "$R6_WORK/trame_lib"
$env:MPLBACKEND = 'Agg'
& $R6_PY paper_evidence/revision_v5/figures/draw_figure1.py
```
