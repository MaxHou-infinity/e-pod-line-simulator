"""工具函数单元测试"""

from src.models import CollaborationType, ProductionLine, Station
from src.utils import (
    format_time,
    get_alert_color,
    get_status_color,
    load_config,
    save_config,
    validate_production_line,
    validate_station,
)


def test_validate_station():
    assert validate_station("注油", 25, 2) == (True, "")
    assert validate_station("", 25, 2)[0] is False
    assert validate_station("注油", 0, 2)[0] is False
    assert validate_station("注油", 25, 0)[0] is False


def test_validate_production_line():
    line = ProductionLine("测试")
    assert validate_production_line(line)[0] is False
    line.add_station(Station("s01", "注油", 25, 2))
    assert validate_production_line(line) == (True, "")


def test_save_and_load_config(tmp_path):
    line = ProductionLine("往返测试")
    line.add_station(Station("s01", "注油", 25, 2, collaboration_type=CollaborationType.PARALLEL))
    path = str(tmp_path / "line.json")
    assert save_config(line, path) is True

    restored = load_config(path)
    assert restored is not None
    assert restored.name == "往返测试"
    assert restored.stations[0].name == "注油"


def test_load_config_missing_file(tmp_path):
    assert load_config(str(tmp_path / "none.json")) is None


def test_format_time():
    assert format_time(3661) == "01:01:01"


def test_color_helpers():
    assert get_status_color("running") == "#00FF00"
    assert get_status_color("unknown") == "#CCCCCC"
    assert get_alert_color("warning") == "#FFA500"
