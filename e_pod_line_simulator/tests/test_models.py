"""数据模型单元测试"""

import pytest

from src.models import (
    CollaborationType,
    ProductionLine,
    Scenario,
    Station,
)


def make_station(
    sid="s01",
    name="注油",
    process_time=25.0,
    workers=2,
    collab=CollaborationType.PARALLEL,
    oee=0.85,
):
    return Station(
        id=sid,
        name=name,
        process_time=process_time,
        worker_count=workers,
        collaboration_type=collab,
        oee=oee,
        efficiency=0.95,
    )


def test_station_capacity_parallel():
    station = make_station()
    expected = (3600 / 25) * 2 * 0.85 * 0.95 * (1 - 45 / 480)
    assert station.get_capacity() == pytest.approx(expected, rel=1e-6)


def test_station_capacity_collaborative_ignores_workers():
    station = make_station(workers=4, collab=CollaborationType.COLLABORATIVE)
    single = make_station(workers=1, collab=CollaborationType.COLLABORATIVE)
    assert station.get_capacity() == single.get_capacity()


def test_production_line_kpis():
    line = ProductionLine("测试产线")
    line.add_station(make_station("s01", "注油", 25, 2))
    line.add_station(make_station("s02", "焊接", 30, 3))
    bottleneck = line.find_bottleneck()
    assert bottleneck is not None
    assert bottleneck.id == "s01"
    assert line.get_bottleneck_capacity() > 0
    assert line.calculate_daily_output() > 0
    assert line.calculate_total_cost() > 0
    assert line.calculate_unit_cost() > 0
    assert 0 < line.calculate_line_balance_rate() <= 1
    assert line.calculate_upph() > 0


def test_production_line_empty_returns_zero():
    line = ProductionLine("空产线")
    assert line.find_bottleneck() is None
    assert line.get_bottleneck_capacity() == 0
    assert line.calculate_daily_output() == 0
    assert line.calculate_upph() == 0


def test_production_line_duplicate_id_raises():
    line = ProductionLine("测试")
    line.add_station(make_station("s01"))
    with pytest.raises(ValueError):
        line.add_station(make_station("s01"))


def test_production_line_serialization_roundtrip():
    line = ProductionLine("序列化测试", shift_hours=10, break_minutes=30, worker_hourly_wage=25.0)
    line.add_station(make_station())
    line.add_station(make_station("s02", "包装", 15, 2))

    restored = ProductionLine.from_dict(line.to_dict())
    assert restored.name == line.name
    assert restored.shift_hours == 10
    assert len(restored.stations) == 2
    assert restored.stations[0].id == "s01"


def test_scenario_snapshot_is_independent():
    line = ProductionLine("方案测试")
    line.add_station(make_station())
    scenario = Scenario.create("方案A", line, "描述")

    line.stations[0].worker_count = 9
    assert scenario.production_line.stations[0].worker_count == 2
    kpis = scenario.get_kpis()
    assert kpis["total_workers"] == 2


def test_alert_and_simulation_state_serialization():
    from src.models import Alert, SimulationState

    alert = Alert("bottleneck", "critical", "s01", "瓶颈", "建议", 12.5)
    data = alert.to_dict()
    assert data["timestamp_minutes"] == 12.5

    state = SimulationState(current_time=60, station_states={"s01": {}}, total_output=10)
    assert state.to_dict()["total_output"] == 10
