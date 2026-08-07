"""仿真引擎单元测试（headless 模式与切换事件）"""

import pytest

from src.models import CollaborationType, ProductionLine, Station
from src.simulation import SimulationEngine, detect_waste


def make_line(name="测试产线"):
    line = ProductionLine(name, shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "注油", 1.0, 1))
    line.add_station(Station("s02", "包装", 1.0, 1))
    return line


def test_headless_run_returns_result():
    result = SimulationEngine(make_line()).run_sync(duration_hours=1.0)

    assert result.total_output > 0
    assert result.line_name == "测试产线"
    assert result.station_outputs["s01"] > 0
    assert result.kpis["bottleneck_capacity"] > 0
    assert result.duration_seconds == 3600


def test_changeover_reduces_output_and_records_event():
    engine = SimulationEngine(make_line())
    engine.trigger_changeover("s01", minutes=30)
    result_with = engine.run_sync(duration_hours=1.0)

    result_without = SimulationEngine(make_line()).run_sync(duration_hours=1.0)

    assert len(result_with.changeover_events) == 1
    assert result_with.changeover_events[0]["station_id"] == "s01"
    assert any(a.alert_type == "changeover" for a in result_with.alerts)
    assert result_with.total_output < result_without.total_output


def test_trigger_changeover_validates_station():
    engine = SimulationEngine(make_line())
    with pytest.raises(ValueError):
        engine.trigger_changeover("missing", minutes=45)
    with pytest.raises(ValueError):
        engine.trigger_changeover("s01", minutes=0)


def test_wip_samples_collected():
    result = SimulationEngine(make_line()).run_sync(duration_hours=0.5)
    assert len(result.wip_samples) > 0
    assert all("wip" in sample for sample in result.wip_samples)


def test_detect_waste():
    line = ProductionLine("浪费测试")
    line.add_station(Station("s01", "瓶颈", 30.0, 1))
    line.add_station(Station("s02", "过剩", 10.0, 5))
    bottleneck_capacity = line.get_bottleneck_capacity()
    alerts = detect_waste(line.stations, bottleneck_capacity)
    assert any(a.alert_type == "waste" for a in alerts)
