"""
KPI 历史趋势（V3.2 P1）

跨运行记录 KPI 快照，保存到 configs/run_history.json，供趋势表/图使用。
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from src.models import ProductionLine, SimulationResult

DEFAULT_HISTORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "configs",
    "run_history.json",
)

KPI_NAMES = [
    "bottleneck_capacity",
    "daily_output",
    "total_cost",
    "unit_cost",
    "balance_rate",
    "upph",
    "batch_cycle_min",
    "batch_pass_rate",
    "yield_rate",
    "machine_oee",
    "shippable_quantity",
    "rejected_batches",
]

MAX_RECORDS = 200


def build_snapshot(
    line: ProductionLine,
    result: Optional[SimulationResult] = None,
) -> Dict[str, Any]:
    """从产线（或仿真结果）构建 KPI 快照"""
    if result is not None:
        kpis = {name: result.kpis.get(name, 0.0) for name in KPI_NAMES}
        kpis["total_output"] = result.total_output
        kpis["duration_minutes"] = round(result.duration_seconds / 60.0, 1)
    else:
        kpis = {
            "bottleneck_capacity": line.get_bottleneck_capacity(),
            "daily_output": line.calculate_daily_output(),
            "total_cost": line.calculate_total_cost(),
            "unit_cost": line.calculate_unit_cost(),
            "balance_rate": line.calculate_line_balance_rate(),
            "upph": line.calculate_upph(),
            "batch_cycle_min": line.calculate_batch_cycle_min(),
            "batch_pass_rate": line.calculate_batch_pass_rate(),
            "yield_rate": line.calculate_avg_yield_rate(),
            "machine_oee": line.calculate_avg_machine_oee(),
            "shippable_quantity": 0.0,
            "rejected_batches": 0.0,
        }
        kpis["total_output"] = 0
        kpis["duration_minutes"] = 0.0
    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "line_name": line.name,
        "production_type": line.production_type.value,
        "kpis": {k: round(float(v), 4) for k, v in kpis.items()},
    }


def load_history(path: str = DEFAULT_HISTORY_PATH) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def append_snapshot(
    record: Dict[str, Any],
    path: str = DEFAULT_HISTORY_PATH,
) -> bool:
    try:
        records = load_history(path)
        records.append(record)
        records = records[-MAX_RECORDS:]
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def kpi_series(
    history: List[Dict[str, Any]],
    kpi_name: str,
) -> List[Tuple[str, float]]:
    """返回 [(时间, 值)] 序列"""
    return [
        (record["timestamp"], record["kpis"].get(kpi_name, 0.0))
        for record in history
    ]
