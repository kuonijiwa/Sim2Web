# Contributing

Code and documentation use MIT; example data use CC BY 4.0. See `LICENSE` and
`DATA_LICENSE.md`. These instructions describe development and verification.

## Development setup

Use Python 3.10+ and Node.js 20+. From the repository root, with your Python
environment activated:

```bash
python -m pip install -r requirements.txt
python -m pip install -e ".[test]"
python -m pytest -q
npm ci
npm run build
```

The browser applications use Vue, vtk.js and Vite. Exact installed versions are
recorded by `package-lock.json`; `npm ci` uses that lock. There are no
`test:web` or `validate:web` npm scripts. Browser interaction should be checked
using the deployment checklist in `docs/IIS_DEPLOYMENT.md`.

## Change rules

- Preserve the three real cases and their distinct surface roles. Do not replace
  them with synthetic data or silently add historical excavation stages.
- Keep quantitative stress in CellData and mark interpolated point copies as
  display-only. Preserve the documented Float32 conversion boundary.
- Keep categorical codes in CellData and use discrete rendering.
- Check tensor-component order, units and the physical meaning of null selectors
  before adapting a processor. Do not infer these from the VTU suffix alone.
- Keep paths in metadata and frontend asset references relative.
- Do not add credentials or confidential metadata. Include only data for which
  redistribution has been authorized and the applicable licence is recorded.
- The processors and publication validator replace their corresponding generated
  outputs. Back up independently modified products before explicitly running
  those commands; they have no general overwrite-confirmation switch.

## Tests and evidence

Add a focused test for behavior changes and run `python -m pytest -q` and
`npm run build`. The optional full source-pair validation command is
`python scripts/validate_publication.py`; see `docs/PUBLICATION_REVISION.md` for
its regeneration and evidence-writing behavior. Distinguish newly measured
results from the retained publication evidence.

Document schema or command changes alongside the code. Performance claims need
machine-readable measurements; successful compilation or page loading is not
evidence of interactive throughput. Do not commit dependencies, caches, virtual
environments, browser profiles or build output. Keep `requirements.txt`,
`package-lock.json`, and `.gitattributes` in version control.
