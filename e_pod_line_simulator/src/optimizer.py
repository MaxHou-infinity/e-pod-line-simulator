"""
遗传算法辅助优化（V3.2 P2 / V3.3 增强）

遗传算法寻优：对工序人数 / 缓冲区容量 / 机台节拍搜索，输出 TOP 方案。
- V3.3：初始种群注入当前配置、工序锁定、实际单位成本口径、进度回调。
"""

import copy
import random
from typing import Callable, Dict, List, Optional

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


def _current_individual(line: ProductionLine) -> List[float]:
    individual: List[float] = []
    for station in line.stations:
        individual.append(float(station.worker_count))
        individual.append(float(station.buffer_capacity))
        if station.machine_takt:
            individual.append(float(station.machine_takt))
    return individual


def _gene_specs(line: ProductionLine) -> List[tuple]:
    """返回 [(station_id, gene_key, lo, hi)]，与个体编码顺序一致"""
    specs: List[tuple] = []
    for station in line.stations:
        for key, (lo, hi) in _gene_bounds(station).items():
            specs.append((station.id, key, lo, hi))
    return specs


def _locked_mask(line: ProductionLine, locked_stations: List[str]) -> List[bool]:
    locked = set(locked_stations or [])
    return [sid in locked for sid, _, _, _ in _gene_specs(line)]


def _random_individual(
    line: ProductionLine,
    rng: random.Random,
    locked: List[str],
) -> List[float]:
    mask = _locked_mask(line, locked)
    current = _current_individual(line)
    individual: List[float] = []
    for index, (_, key, lo, hi) in enumerate(_gene_specs(line)):
        if mask[index]:
            individual.append(current[index])
            continue
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


def _params_text(params: Dict) -> str:
    parts = []
    for name, entry in params.items():
        parts.append(
            f"{name}:{entry['worker_count']}人/{entry['buffer_capacity']}缓冲"
        )
    return "；".join(parts)


def _crossover(a: List[float], b: List[float], rng: random.Random) -> List[float]:
    point = rng.randint(1, len(a) - 1) if len(a) > 1 else 0
    return a[:point] + b[point:]


def _mutate(
    line: ProductionLine,
    individual: List[float],
    rng: random.Random,
    locked: List[str],
    rate: float = 0.2,
) -> List[float]:
    mask = _locked_mask(line, locked)
    result = list(individual)
    for index, (_, key, lo, hi) in enumerate(_gene_specs(line)):
        if mask[index] or rng.random() >= rate:
            continue
        if key == GENE_TAKT:
            result[index] = round(rng.uniform(lo, hi), 2)
        else:
            result[index] = float(rng.randint(int(lo), int(hi)))
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
        total_cost = result.kpis.get("total_cost", 0.0)
        actual_unit_cost = (
            total_cost / result.total_output if result.total_output > 0 else 0.0
        )
        score = result.total_output if objective == "output" else -unit_cost
        return {
            "score": score,
            "total_output": result.total_output,
            "unit_cost": unit_cost,
            "actual_unit_cost": actual_unit_cost,
            "total_cost": total_cost,
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
    locked_stations: Optional[List[str]] = None,
    include_baseline: bool = True,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
) -> List[Dict]:
    """
    运行遗传算法寻优，返回按目标排序的 TOP 方案（含参数与 KPI）。

    locked_stations: 锁定的工序 ID，其基因固定为当前值；
    include_baseline: 初始种群注入当前产线配置；
    progress_callback: (当前代, 总代数, 当前最优分数)。
    """
    rng = random.Random(seed)
    locked = locked_stations or []
    individuals = [_random_individual(line, rng, locked) for _ in range(population)]
    if include_baseline and individuals:
        individuals[0] = _current_individual(line)

    evaluated = [
        e for e in (
            _evaluate(line, ind, objective, duration_hours, warmup_minutes)
            for ind in individuals
        )
        if e is not None
    ]

    total_generations = max(0, generations - 1)
    for generation in range(1, total_generations + 1):
        if not evaluated:
            break
        parents = sorted(evaluated, key=lambda e: e["score"], reverse=True)
        next_gen: List[Dict] = []
        while len(next_gen) < population and len(parents) >= 2:
            pool = parents[: max(2, len(parents) // 2)]
            a = rng.choice(pool)
            b = rng.choice(pool)
            child = _crossover(a["individual"], b["individual"], rng)
            child = _mutate(line, child, rng, locked)
            evaluated_child = _evaluate(
                line, child, objective, duration_hours, warmup_minutes
            )
            if evaluated_child is not None:
                next_gen.append(evaluated_child)
        evaluated = (
            sorted(evaluated, key=lambda e: e["score"], reverse=True) + next_gen
        )[:population]
        if progress_callback:
            progress_callback(generation, total_generations, evaluated[0]["score"])

    evaluated.sort(key=lambda e: e["score"], reverse=True)
    top = evaluated[:top_n]
    for rank, entry in enumerate(top, 1):
        entry["rank"] = rank
        entry["objective"] = objective
    return top
