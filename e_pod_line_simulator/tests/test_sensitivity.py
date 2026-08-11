"""敏感性试算测试（V3.1 P2）"""

from src.models import ProductionLine, Station
from src.sensitivity import run_sensitivity


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
