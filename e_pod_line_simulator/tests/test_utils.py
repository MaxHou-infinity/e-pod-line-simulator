"""工具函数单元测试"""

import logging

import pandas as pd

from src.models import (
    CollaborationType,
    ProductionLine,
    ProductionType,
    Station,
    create_liquid_line,
)
from src.utils import (
    calculate_roi,
    create_excel_template,
    format_number,
    format_time,
    get_alert_color,
    get_status_color,
    import_from_excel,
    load_config,
    load_ui_config,
    save_config,
    save_ui_config,
    setup_logger,
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

    liquid = create_liquid_line()
    assert validate_production_line(liquid) == (True, "")
    liquid.cleanroom_limits = {"C": 1}
    ok, msg = validate_production_line(liquid)
    assert ok is False and "超过上限" in msg


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
    assert get_status_color("running") == "#34C759"
    assert get_status_color("unknown") == "#E5E5EA"
    assert get_alert_color("warning") == "#FF9F0A"


def test_calculate_roi():
    assert calculate_roi(10000, 200) == 50.0
    assert calculate_roi(10000, 0) == 0.0
    assert calculate_roi(10000, -1) == 0.0


def test_format_number():
    assert format_number(123.456) == "123.46"
    assert format_number(1.2, 3) == "1.200"


def test_create_and_import_excel_template(tmp_path):
    path = str(tmp_path / "template.xlsx")
    assert create_excel_template(path) is True
    line, error = import_from_excel(path)
    assert line is not None and error is None
    assert len(line.stations) == 4
    assert line.stations[0].name == "注油"


def test_create_and_import_liquid_template(tmp_path):
    path = str(tmp_path / "liquid.xlsx")
    assert create_excel_template(path, production_type="liquid_filling") is True
    line, error = import_from_excel(path)
    assert line is not None and error is None
    assert line.production_type == ProductionType.LIQUID_FILLING
    assert len(line.recipes) == 1
    assert line.recipes[0].name == "经典烟草"
    assert len(line.tanks) == 2
    assert len(line.batches) == 1


def test_import_excel_missing_file(tmp_path):
    line, error = import_from_excel(str(tmp_path / "none.xlsx"))
    assert line is None
    assert "不存在" in error


def test_import_excel_missing_required_column(tmp_path):
    df = pd.DataFrame({"工序名": ["注油"]})
    path = str(tmp_path / "bad.xlsx")
    df.to_excel(path, index=False, engine="openpyxl")
    line, error = import_from_excel(path)
    assert line is None
    assert "缺少必填列" in error


def test_setup_logger_writes_file(tmp_path):
    log_path = str(tmp_path / "app.log")
    logger = setup_logger(log_path)
    logger.info("测试日志")
    for handler in logger.handlers:
        handler.flush()
    content = open(log_path, encoding="utf-8").read()
    assert "测试日志" in content


def test_ui_config_roundtrip(tmp_path, monkeypatch):
    import src.utils as utils_mod

    path = str(tmp_path / "ui.json")
    monkeypatch.setattr(utils_mod, "UI_CONFIG_FILE", path)
    assert save_ui_config({"theme": "dark"}) is True
    assert load_ui_config() == {"theme": "dark"}
    assert load_ui_config()["theme"] == "dark"
