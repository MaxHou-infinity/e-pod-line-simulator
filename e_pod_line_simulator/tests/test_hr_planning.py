"""人力规划模块单元测试（V3.2 P0，headless）"""

import pytest

from src.models import CollaborationType, ProductionLine, Station
from src.hr_planning import (
    LaborCostConfig,
    LearningCurveConfig,
    ShiftPlan,
    build_hr_summary,
    calculate_labor_costs,
    current_headcount_by_role,
    ramp_days_to_full,
    required_headcount_by_role,
    required_headcount_by_station,
    weekly_hiring_gap,
)


def make_assembly_line(worker_count=1, process_time=60.0):
    line = ProductionLine("装配线", shift_hours=8, break_minutes=60)
    line.add_station(Station(
        "s01", "组装", process_time, worker_count,
        oee=1.0, efficiency=1.0, changeover_time=0,
    ))
    return line


def test_required_headcount_parallel_scales_with_target():
    line = make_assembly_line()
    shift = ShiftPlan(shifts_per_day=1, shift_hours=8, break_minutes=60)
    # 有效 7h；单人工位产能 60/h
    assert required_headcount_by_station(line, 420, shift)["s01"] == 1
    assert required_headcount_by_station(line, 840, shift)["s01"] == 2


def test_collaborative_headcount_keeps_team():
    line = ProductionLine("协同线")
    line.add_station(Station(
        "s01", "组装", 30.0, 3,
        collaboration_type=CollaborationType.COLLABORATIVE,
        oee=1.0, efficiency=1.0, changeover_time=0,
    ))
    shift = ShiftPlan(shifts_per_day=1, shift_hours=8, break_minutes=60)
    assert required_headcount_by_station(line, 100000, shift)["s01"] == 3


def test_labor_costs_formula():
    line = make_assembly_line()
    shift = ShiftPlan(shifts_per_day=1, shift_hours=8, break_minutes=60)
    cost = LaborCostConfig(
        base_hourly_wage=20.0,
        social_insurance_rate=0.30,
        absence_rate=0.0,
    )
    result = calculate_labor_costs(line, 10, shift, cost)
    # 208 元/人·天 × 10 = 2080；月 = 54080
    assert result["daily_labor_cost"] == pytest.approx(2080.0)
    assert result["monthly_labor_cost"] == pytest.approx(54080.0)

    cost_absent = LaborCostConfig(
        base_hourly_wage=20.0,
        social_insurance_rate=0.30,
        absence_rate=0.1,
    )
    result_absent = calculate_labor_costs(line, 10, shift, cost_absent)
    assert result_absent["covered_headcount"] == 12


def test_weekly_hiring_gap_timeline():
    required = {"filling_operator": 5, "qc_technician": 1}
    current = {"filling_operator": 2, "qc_technician": 1}
    plan = [(1, "filling_operator", 2), (3, "filling_operator", 1)]
    rows = weekly_hiring_gap(required, current, plan, weeks=4)
    assert rows[0]["gap"]["filling_operator"] == 1
    assert rows[1]["gap"]["filling_operator"] == 1
    assert rows[2]["gap"]["filling_operator"] == 0
    assert rows[3]["total_gap"] == 0


def test_ramp_days_to_full():
    line = make_assembly_line(worker_count=8)
    shift = ShiftPlan(shifts_per_day=1, shift_hours=8, break_minutes=60)
    required = {"general": 10}
    current = {"general": 8}
    learning = LearningCurveConfig(
        ramp_days=10, start_efficiency=0.5, target_efficiency=1.0
    )
    days = ramp_days_to_full(line, 0, shift, required, current, learning)
    assert days == 10


def test_build_hr_summary_shape():
    line = make_assembly_line(worker_count=2)
    shift = ShiftPlan(shifts_per_day=2, shift_hours=8, break_minutes=60)
    cost = LaborCostConfig()
    learning = LearningCurveConfig(ramp_days=30)
    summary = build_hr_summary(
        line, 2000, shift, cost, learning,
        current={"general": 2}, hiring_plan=[],
    )
    assert summary["total_headcount"] >= 2
    assert "headcount_by_station" in summary
    assert "headcount_by_role" in summary
    assert summary["costs"]["daily_labor_cost"] > 0
    assert len(summary["weekly_gap"]) == 12
    assert summary["days_to_full"] >= 0
    assert "current_headcount" in summary
    assert "current_total" in summary
    assert "initial_gap" in summary


def test_current_headcount_by_role_sums_stations():
    line = ProductionLine("在岗测试")
    line.add_station(Station("s01", "镭雕", 2.0, 5))
    line.add_station(Station("s02", "注油", 2.0, 1))
    line.add_station(Station("s03", "包装", 2.0, 2))

    current = current_headcount_by_role(line)
    assert current == {"general": 8}


def test_gap_uses_station_headcount_when_current_empty():
    """回归：当前在岗为空时按产线工序人数汇总，缺口不再虚高"""
    line = ProductionLine("方案-1", shift_hours=8, break_minutes=60)
    for i, workers in enumerate([5, 1, 1, 1, 1, 1, 2, 2]):
        line.add_station(Station(f"s{i:02d}", f"工序{i}", 60.0, workers))
    shift = ShiftPlan(shifts_per_day=1, shift_hours=8, break_minutes=60)
    summary = build_hr_summary(
        line, 100, shift, LaborCostConfig(), LearningCurveConfig(),
        current={}, hiring_plan=[],
    )
    assert summary["current_total"] == 14
    assert summary["initial_gap"] == max(0, summary["total_headcount"] - 14)
