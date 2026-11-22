# Figures of the revised manuscript

* `fig1_architecture.png`: `dot -Tpng fig1.dot -o fig1_architecture.png`
* `fig2_workbench.png`: `benchmark/workbench_walkthrough.mjs` on Case E
  (`--order XX,YY,ZZ,XY,YZ,XZ --unit Pa --spacing 20`), steps 2 and 5, composed by `make_figs.py`
* `fig3_principal_caseA.png`: `make_figs.py` (Case A input, `vtkTensorPrincipalInvariants`
  versus the order declared in the file)
* `fig4_cases.png`: `benchmark/screenshots.mjs` on the rebuilt Cases A, B, C, E
  (A: `#field=Stress_Min_Principal&axis=x&pos=38&range=p5_p95&section=1 --probe 0.47,0.5`;
  B: `#field=Stress_Max_Principal&axis=y&pos=-185&range=p5_p95&section=1`;
  C: `--field TotalDisplacement --axis x --index 26 --probe 0.5,0.45`; E: default view)
* `fig5_internal_faces.png`: `make_figs.py`; face counts from the [archived Case C measurements](https://github.com/kuonijiwa/Sim2Web/blob/26966d011ed26f9d67791f03d49f93721e37bd19/paper_evidence/revision_v3/README.md#2-package-size-and-primary-products-current-configurations)
  and the Windows r3 Case F run

Run `make_figs.py` from the repository root in the Sim2Web environment; it expects
the screenshots in `/tmp/figs` and `/tmp/wb_shots` (adjust the paths).
