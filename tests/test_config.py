from pathlib import Path

import pytest

from sim2web.config import ConfigError, apply_overrides, config_from_dict, load_config

from conftest import base_config

ROOT = Path(__file__).resolve().parents[1]


def test_unknown_option_is_rejected(tmp_path):
    data = base_config("x.vtu")
    data["sections"]["spcing"] = 5
    with pytest.raises(ConfigError, match="spcing"):
        config_from_dict(data, tmp_path)


def test_stress_order_must_be_declared_and_known(tmp_path):
    data = base_config("x.vtu")
    data["fields"]["stress"]["order"] = "XX,YY,ZZ,YZ,XY,XZ"
    with pytest.raises(ConfigError, match="order"):
        config_from_dict(data, tmp_path)


def test_primary_excavation_requires_excavation(tmp_path):
    data = base_config("x.vtu", **{"geometry.primary": "excavation", "geometry.excavation.enabled": False})
    with pytest.raises(ConfigError, match="primary"):
        config_from_dict(data, tmp_path)


def test_group_field_must_be_a_declared_category(tmp_path):
    data = base_config("x.vtu", **{"geometry.groups.field": "Material"})
    with pytest.raises(ConfigError, match="declared category"):
        config_from_dict(data, tmp_path)


def test_overrides_are_applied_before_validation():
    data = apply_overrides(base_config("x.vtu"), ["sections.spacing=2.5", "viewer.bands=12"])
    assert data["sections"]["spacing"] == 2.5 and data["viewer"]["bands"] == 12


def test_glob_stages_are_naturally_sorted(tmp_path):
    for name in ("stage_10.vtu", "stage_2.vtu", "stage_1.vtu"):
        (tmp_path / name).write_text("")
    data = base_config("unused")
    data["input"] = {"glob": "stage_*.vtu"}
    cfg = config_from_dict(data, tmp_path)
    assert [s.name for s in cfg.resolved_stages()] == ["stage_1", "stage_2", "stage_10"]


@pytest.mark.parametrize("case", ["flac3d_cavern_iv2", "flac3d_slope_exac23", "3dec_slope"])
def test_shipped_case_configurations_are_valid(case):
    cfg = load_config(ROOT / "examples" / case / "sim2web.yaml")
    assert cfg.resolved_stages()


def test_configuration_written_for_the_former_name_is_read(tmp_path):
    data = base_config("x.vtu")
    data["schema"] = "simwebview-config/1"
    assert config_from_dict(data, tmp_path).schema == "sim2web-config/1"


def test_overrides_address_list_entries():
    from sim2web.config import ConfigError, apply_overrides

    data = {"input": {"stages": [{"file": "a.vtu", "name": "s"}]}}
    apply_overrides(data, ["input.stages[0].file=G:/成果/papers/02/case4/EXC12_dis.vtu", "sections.spacing=5"])
    assert data["input"]["stages"][0]["file"].endswith("EXC12_dis.vtu")
    assert data["sections"]["spacing"] == 5
    with pytest.raises(ConfigError, match="out of range"):
        apply_overrides(data, ["input.stages[2].file=x.vtu"])
