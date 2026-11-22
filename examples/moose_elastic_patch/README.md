# Case H · MOOSE elastic patch

The source is the upstream MOOSE Solid Mechanics 3D elastic-patch reference
result [`elastic_patch_out.e`](https://github.com/idaholab/moose/blob/db004415602203a8d05b7a82a114b3fccfed69fe/modules/solid_mechanics/test/tests/elastic_patch/gold/elastic_patch_out.e).
The pinned MOOSE source revision is `db004415602203a8d05b7a82a114b3fccfed69fe`
(2024-02-28). The Exodus result contains three time steps. Sim2Web converts the
final step by default (`t=2`) and assembles the split displacements and stress
components. The commands use the reference output directly.

Run from the repository root in PowerShell with the viewer built.

```powershell
python -m pip install -e '.[convert]'
$repo = (Get-Location).Path
$run = Join-Path ([IO.Path]::GetTempPath()) 'sim2web-moose-patch'
New-Item -ItemType Directory -Force -Path $run | Out-Null
Copy-Item "$repo/examples/moose_elastic_patch/sim2web.yaml" $run
Push-Location $run
$upstream = 'https://raw.githubusercontent.com/idaholab/moose/db004415602203a8d05b7a82a114b3fccfed69fe/modules/solid_mechanics/test/tests/elastic_patch/gold/elastic_patch_out.e'
Invoke-WebRequest -Uri $upstream -OutFile elastic_patch_out.e
if ((git hash-object elastic_patch_out.e) -ne '255db70cac82f384b25d0c4df8df488e3fba57ef') { throw 'Unexpected Exodus input' }
sim2web convert elastic_patch_out.e moose.vtu
sim2web build sim2web.yaml
sim2web validate sim2web.yaml
Pop-Location
```

For a small synthetic conversion test, the repository also supplies
[`tests/data/moose_like_patch.e`](../../tests/data/moose_like_patch.e).
The upstream Exodus file is fetched when following the recipe.
