"""AI 自动优化模块单元测试（V3.2 P2）"""

from src.models import ProductionLine, Station
from src.optimizer import optimize


def make_line():
    line = ProductionLine("优化测试", shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "瓶颈", 2.0, 1))
    line.add_station(Station("s02", "下游", 1.0, 2))
    return line


def test_optimize_returns_ranked_top_solutions():
    line = make_line()
    top = optimize(
        line, objective="unit_cost",
        generations=2, population=4, top_n=3,
        duration_hours=0.5,
    )

    assert 1 <= len(top) <= 3
    assert all("rank" in s and "params" in s and "unit_cost" in s for s in top)
    unit_costs = [s["unit_cost"] for s in top]
    assert unit_costs == sorted(unit_costs)


def test_optimize_deterministic_with_seed():
    line = make_line()
    a = optimize(line, generations=2, population=4, duration_hours=0.5, seed=7)
    b = optimize(line, generations=2, population=4, duration_hours=0.5, seed=7)
    assert [s["unit_cost"] for s in a] == [s["unit_cost"] for s in b]


def test_optimize_output_objective_scores_output():
    line = make_line()
    top = optimize(
        line, objective="output",
        generations=2, population=4, duration_hours=0.5,
    )
    assert top
    assert top[0]["score"] == top[0]["total_output"]


def test_optimize_actual_unit_cost_present():
    top = optimize(
        make_line(), objective="unit_cost",
        generations=2, population=4, duration_hours=0.5,
    )
    assert all("actual_unit_cost" in s and s["actual_unit_cost"] > 0 for s in top)


def test_optimize_locked_stations_keep_values():
    line = make_line()
    original = line.get_station("s01")
    top = optimize(
        line, objective="unit_cost",
        generations=2, population=4, duration_hours=0.5,
        locked_stations=["s01"],
    )
    for s in top:
        assert s["params"]["瓶颈"]["worker_count"] == original.worker_count
        assert s["params"]["瓶颈"]["buffer_capacity"] == original.buffer_capacity


def test_optimize_progress_callback_called():
    calls = []

    optimize(
        make_line(), objective="output",
        generations=3, population=4, duration_hours=0.5,
        progress_callback=lambda g, t, s: calls.append((g, t)),
    )

    assert len(calls) == 2
    assert calls[0][0] == 1 and calls[0][1] == 2
