"""
AI 自动优化（V3.2 P2）

遗传算法寻优：对工序人数 / 缓冲区容量 / 机台节拍搜索，输出 TOP 方案。
默认以单位成本为目标（越小越好），也可切换为总产出（越大越好）。
"""

import copy
import random
from typing import Dict, List, Optional

from src.models import ProductionLine
from src.simulation import SimulationEngine

GENE_WORKER = "worker_count"
GENE_BUFFER = "buffer_capacity"
GENE_TAKT = "machine_takt"


def _gene_bounds(station) -> Dict[str, tuple]:
    bounds = {
        GENE_WORKER: (1, 10),
        GENE_BUFFER: (10, 500),
    }
    if station.machine_takt:
        bounds[GENE_TAKT] = (0.5, round(station.machine_takt * 1.5, 2))
    return bounds


def _random_individual(line: ProductionLine, rng: random.Random) -> List[float]:
    individual: List[float] = []
    for station in line.stations:
        for key, (lo, hi) in _gene_bounds(station).items():
            if key == GENE_TAKT:
                individual.append(round(rng.uniform(lo, hi), 2))
            else:
                individual.append(float(rng.randint(int(lo), int(hi))))
    return individual


def _apply_genes(line: ProductionLine, individual: List[float]) -> None:
    index = 0
    for station in line.stations:
        for key in _gene_bounds(station):
            value = individual[index]
            index += 1
            if key == GENE_WORKER:
                station.worker_count = max(1, int(round(value)))
            elif key == GENE_BUFFER:
                station.buffer_capacity = max(10, int(round(value)))
            elif key == GENE_TAKT:
                station.machine_takt = max(0.1, round(value, 2))


def _params_summary(line: ProductionLine, individual: List[float]) -> Dict:
    clone = copy.deepcopy(line)
    _apply_genes(clone, individual)
    summary: Dict[str, Dict] = {}
    for station in clone.stations:
        entry = {
            GENE_WORKER: station.worker_count,
            GENE_BUFFER: station.buffer_capacity,
        }
        if station.machine_takt:
            entry[GENE_TAKT] = station.machine_takt
        summary[station.name] = entry
    return summary


def _crossover(
    line: ProductionLine,
    a: List[float],
    b: List[float],
    rng: random.Random,
) -> List[float]:
    point = rng.randint(1, len(a) - 1) if len(a) > 1 else 0
    return a[:point] + b[point:]


def _mutate(
    line: ProductionLine,
    individual: List[float],
    rng: random.Random,
    rate: float = 0.2,
) -> List[float]:
    result = list(individual)
    index = 0
    for station in line.stations:
        for key, (lo, hi) in _gene_bounds(station).items():
            if rng.random() < rate:
                if key == GENE_TAKT:
                    result[index] = round(rng.uniform(lo, hi), 2)
                else:
                    result[index] = float(rng.randint(int(lo), int(hi)))
            index += 1
    return result


def _evaluate(
    line: ProductionLine,
    individual: List[float],
    objective: str,
    duration_hours: float,
    warmup_minutes: float,
) -> Optional[Dict]:
    try:
        clone = copy.deepcopy(line)
        _apply_genes(clone, individual)
        result = SimulationEngine(clone).run_sync(duration_hours, warmup_minutes)
        unit_cost = result.kpis.get("unit_cost", 0.0)
        score = result.total_output if objective == "output" else -unit_cost
        return {
            "score": score,
            "total_output": result.total_output,
            "unit_cost": unit_cost,
            "params": _params_summary(clone, individual),
            "individual": individual,
        }
    except Exception:
        return None


def optimize(
    line: ProductionLine,
    objective: str = "unit_cost",
    generations: int = 8,
    population: int = 6,
    top_n: int = 3,
    duration_hours: float = 8.0,
    warmup_minutes: float = 0.0,
    seed: int = 42,
) -> List[Dict]:
    """
    运行遗传算法寻优，返回按目标排序的 TOP 方案（含参数与 KPI）。
    """
    rng = random.Random(seed)
    individuals = [_random_individual(line, rng) for _ in range(population)]
    evaluated = [
        e for e in (
            _evaluate(line, ind, objective, duration_hours, warmup_minutes)
            for ind in individuals
        )
        if e is not None
    ]

    for _ in range(max(0, generations - 1)):
        if not evaluated:
            break
        parents = sorted(
            evaluated,
            key=lambda e: e["score"],
            reverse=True,
        )
        next_gen: List[Dict] = []
        while len(next_gen) < population and len(parents) >= 2:
            a = rng.choice(parents[: max(2, len(parents) // 2)])
            b = rng.choice(parents[: max(2, len(parents) // 2)])
            child = _crossover(line, a["individual"], b["individual"], rng)
            child = _mutate(line, child, rng)
            evaluated_child = _evaluate(
                line, child, objective, duration_hours, warmup_minutes
            )
            if evaluated_child is not None:
                next_gen.append(evaluated_child)
        evaluated = (
            sorted(evaluated, key=lambda e: e["score"], reverse=True)
            + next_gen
        )[:population]

    evaluated.sort(key=lambda e: e["score"], reverse=True)
    top = evaluated[:top_n]
    for rank, entry in enumerate(top, 1):
        entry["rank"] = rank
        entry["objective"] = objective
    return top
