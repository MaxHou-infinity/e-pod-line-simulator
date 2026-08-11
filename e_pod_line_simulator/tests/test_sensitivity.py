"""敏感性试算测试（V3.1 P2 / V3.2 P1 批量试算）"""

from src.models import ProductionLine, Station
from src.sensitivity import run_sensitivity, run_sweep


def test_sensitivity_scenarios():
    line = ProductionLine("敏感性测试", shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "慢瓶颈", 2.0, 1))
    line.add_station(Station("s02", "快下游", 1.0, 2))

    scenarios = run_sensitivity(line, duration_hours=1.0)

    assert len(scenarios) >= 3
    base = scenarios[0]
    assert base["label"] == "基线"
    worker = next(s for s in scenarios if s["label"] == "瓶颈+1人")
    assert worker["delta_output"] > 0
    assert worker["delta_unit_cost"] < 0


def test_run_sweep_worker_count_monotonic():
    line = ProductionLine("批量试算", shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "瓶颈", 2.0, 1))
    line.add_station(Station("s02", "下游", 1.0, 2))

    rows = run_sweep(line, "worker_count", [1, 2, 3], duration_hours=1.0)

    assert len(rows) == 3
    outputs = [row["total_output"] for row in rows]
    assert outputs == sorted(outputs)
    assert outputs[0] < outputs[-1]
    assert all("total_output" in row and "unit_cost" in row for row in rows)


def test_run_sweep_shift_hours_increases_output():
    line = ProductionLine("批量试算班次", shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "注油", 1.0, 1))

    rows = run_sweep(line, "shift_hours", [1, 2], duration_hours=1.0)

    assert len(rows) == 2
    assert rows[1]["total_output"] >= rows[0]["total_output"]
    assert rows[0]["label"] == "shift_hours=1"
