"""Guard the English release without modifying scientific evidence."""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
CASES = ('flac3d_cavern_iv2', 'flac3d_slope_exac23', '3dec_slope')

@pytest.mark.parametrize('case', CASES)
def test_english_source_and_html_language(case):
    folder = ROOT / 'examples' / case
    for path in folder.rglob('*'):
        if path.suffix in {'.vue', '.js', '.py', '.html'}:
            assert not re.search(r'[\u3400-\u9fff]', path.read_text(encoding='utf-8-sig')), path
    assert 'lang="en"' in (folder / 'frontend/index.html').read_text(encoding='utf-8')

@pytest.mark.parametrize('case', CASES[1:])
def test_slope_labels_and_wrapping(case):
    text = (ROOT / 'examples' / case / 'frontend/src/App.vue').read_text(encoding='utf-8')
    for label in ('Reset view', 'Select field', 'Show section', 'Show mesh edges', 'cell data', 'Ready'):
        assert label in text
    assert ':title="formatFieldName(field)"' in text
    assert 'white-space: normal;' in text
    assert 'minmax(0, 1fr)' in text

def test_approved_licences():
    assert 'Copyright (c) 2026 HydroChina Itasca' in (ROOT / 'LICENSE').read_text()
    assert 'CC BY 4.0' in (ROOT / 'DATA_LICENSE.md').read_text()
    assert not (ROOT / 'LICENSE_PENDING.md').exists()
