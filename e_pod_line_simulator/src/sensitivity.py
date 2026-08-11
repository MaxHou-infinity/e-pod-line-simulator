"""
敏感性试算（V3.1 P2）

围绕瓶颈工序生成单一变量变更方案，headless 对比产出与单位成本。
"""

import copy
from typing import Dict, List

from src.models import CollaborationType, ProductionLine
from src.simulation import SimulationEngine


def run_sensitivity(
    line: ProductionLine,
    duration_hours: float = 8.0,
    warmup_minutes: float = 0.0,
) -> List[Dict]:
    """
    运行敏感性试算

    Returns:
        List[Dict]: 每个方案含 label/total_output/unit_cost/delta_output/delta_unit_cost
    """
    base_result = SimulationEngine(copy.deepcopy(line)).run_sync(
        duration_hours, warmup_minutes
    )
    base_unit_cost = base_result.kpis.get('unit_cost', 0.0)
    scenarios = [{
        'label': '基线',
        'total_output': base_result.total_output,
        'unit_cost': base_unit_cost,
        'delta_output': 0,
        'delta_unit_cost': 0.0,
    }]

    bottleneck = line.find_bottleneck()
    if bottleneck is None:
        return scenarios

    variants = []
    if bottleneck.machine_takt and bottleneck.machine_takt > 1:
        variants.append((
            '机台节拍-1秒',
            lambda st: setattr(st, 'machine_takt', st.machine_takt - 1.0),
        ))
    elif bottleneck.collaboration_type == CollaborationType.PARALLEL:
        variants.append((
            '瓶颈+1人',
            lambda st: setattr(st, 'worker_count', st.worker_count + 1),
        ))
    variants.append((
        '瓶颈OEE+5%',
        lambda st: setattr(st, 'oee', min(1.0, st.oee + 0.05)),
    ))

    for label, apply in variants:
        clone = copy.deepcopy(line)
        target = clone.get_station(bottleneck.id)
        apply(target)
        result = SimulationEngine(clone).run_sync(duration_hours, warmup_minutes)
        unit_cost = result.kpis.get('unit_cost', 0.0)
        scenarios.append({
            'label': label,
            'total_output': result.total_output,
            'unit_cost': unit_cost,
            'delta_output': result.total_output - base_result.total_output,
            'delta_unit_cost': round(unit_cost - base_unit_cost, 4),
        })

    return scenarios
