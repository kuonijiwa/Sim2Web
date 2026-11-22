# Contributing

Code and documentation use MIT; example data use CC BY 4.0 (`LICENSE`,
`DATA_LICENSE.md`).

## Development setup

```bash
python -m pip install -r requirements.txt     # validated versions
python -m pip install -e ".[test]"
python -m pytest -q                           # synthetic-model tests, ~5 s
npm install
npm run test:viewer
npm run build:viewer
```

Real-data checks need the Git LFS models (`git lfs pull`) and take a few
minutes:

```bash
SIM2WEB_REALDATA=1 python -m pytest -m realdata
```

## Rules for changes

- Numerical behaviour is configured, not hard-coded per case. A new option
  needs a default that keeps existing packages unchanged, a validation rule in
  `config.py`, documentation in `docs/CONFIGURATION.md` and a test.
- Keep quantitative stress in CellData; point copies are `_DisplayOnly`.
  Categories stay CellData and are never interpolated.
- Do not infer tensor order, units, signs or void rules from file names.
- `index.json` must stay deterministic (no timestamps or absolute paths).
- If a change alters products of the example cases, state it in `CHANGELOG.md`
  and say whether `tests/test_realdata.py` (byte-level v0.1 regression) still
  applies.
- Include only data whose redistribution is authorised, with its licence.
