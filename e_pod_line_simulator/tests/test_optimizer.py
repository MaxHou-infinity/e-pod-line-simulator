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
