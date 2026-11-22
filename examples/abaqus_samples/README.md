# Case G · Abaqus crankshaft

The source is `crankshaft_TCD_nodal_averaged_R2020.odb`, the nodal-averaged
crankshaft result supplied with the Abaqus/fe-safe 2020 tutorial data. On a
Windows SIMULIA 2020 installation, find it under
`win_b64/Durability_resources/data/Abaqus/`. The exporter reads the last
populated frame by default. This ODB stores stress `S` on nodes, so the
configuration retains the point association and uses the file's component
names. Units are left unspecified because the ODB supplies no unit system.

Run from the repository root in PowerShell with Sim2Web installed and the
viewer built. Set `$simulia2020` to the installation root. Use a writable
scratch path that the Abaqus 2020 Python launcher can read.

```powershell
$repo = (Get-Location).Path
$simulia2020 = 'C:/SIMULIA/EstProducts/2020'
$bin = "$simulia2020/win_b64"
$run = Join-Path ([IO.Path]::GetTempPath()) 'sim2web-abaqus-crankshaft'
New-Item -ItemType Directory -Force -Path $run | Out-Null
Copy-Item "$repo/examples/abaqus_samples/sim2web.yaml" $run
Copy-Item "$repo/tools/abaqus_odb_to_vtu.py" $run
Push-Location $run
& "$bin/code/bin/ABQLauncher.exe" python abaqus_odb_to_vtu.py "$bin/Durability_resources/data/Abaqus/crankshaft_TCD_nodal_averaged_R2020.odb" crankshaft.vtu
sim2web build sim2web.yaml
sim2web validate sim2web.yaml
Pop-Location
```

Use the ODB from your licensed installation. The sample ODB and its exports
are supplied locally by the reader.
