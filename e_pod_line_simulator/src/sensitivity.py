"""
敏感性试算（V3.1 P2）

围绕瓶颈工序生成单一变量变更方案，headless 对比产出与单位成本。
"""

import copy
from typing import Dict, List, Optional

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
    base_material_cost = base_result.kpis.get('material_cost', 0.0)
    base_total_cost = base_result.kpis.get('total_cost', 0.0)
    scenarios = [{
        'label': '基线',
        'total_output': base_result.total_output,
        'unit_cost': base_unit_cost,
        'material_cost': base_material_cost,
        'total_cost': base_total_cost,
        'actual_unit_cost': (
            base_total_cost / base_result.total_output
            if base_result.total_output > 0 else 0.0
        ),
        'delta_output': 0,
        'delta_unit_cost': 0.0,
        'delta_material_cost': 0.0,
        'apply': None,
    }]

    bottleneck = line.find_bottleneck()
    if bottleneck is None:
        return scenarios

    variants = []

    def _station_apply(attr: str, value) -> Dict:
        return {'station_id': bottleneck.id, 'attr': attr, 'value': value}

    if bottleneck.machine_takt and bottleneck.machine_takt > 1:
        variants.append((
            '机台节拍-1秒',
            lambda c: setattr(
                c.get_station(bottleneck.id), 'machine_takt',
                c.get_station(bottleneck.id).machine_takt - 1.0,
            ),
            _station_apply(
                'machine_takt',
                round(bottleneck.machine_takt - 1.0, 2),
            ),
        ))
        variants.append((
            '增加1台机台',
            lambda c: setattr(
                c.get_station(bottleneck.id), 'worker_count',
                c.get_station(bottleneck.id).worker_count + 1,
            ),
            _station_apply('worker_count', bottleneck.worker_count + 1),
        ))
    elif bottleneck.collaboration_type == CollaborationType.PARALLEL:
        variants.append((
            '瓶颈+1人',
            lambda c: setattr(
                c.get_station(bottleneck.id), 'worker_count',
                c.get_station(bottleneck.id).worker_count + 1,
            ),
            _station_apply('worker_count', bottleneck.worker_count + 1),
        ))
        variants.append((
            '瓶颈+2人',
            lambda c: setattr(
                c.get_station(bottleneck.id), 'worker_count',
                c.get_station(bottleneck.id).worker_count + 2,
            ),
            _station_apply('worker_count', bottleneck.worker_count + 2),
        ))
        variants.append((
            '自动化替代10%',
            lambda c: setattr(
                c.get_station(bottleneck.id), 'process_time',
                c.get_station(bottleneck.id).process_time * 0.9,
            ),
            _station_apply(
                'process_time',
                round(bottleneck.process_time * 0.9, 3),
            ),
        ))
    if bottleneck.worker_count > 1:
        variants.append((
            '瓶颈-1人',
            lambda c: setattr(
                c.get_station(bottleneck.id), 'worker_count',
                max(1, c.get_station(bottleneck.id).worker_count - 1),
            ),
            _station_apply('worker_count', max(1, bottleneck.worker_count - 1)),
        ))
    variants.append((
        '瓶颈OEE+5%',
        lambda c: setattr(
            c.get_station(bottleneck.id), 'oee',
            min(1.0, c.get_station(bottleneck.id).oee + 0.05),
        ),
        _station_apply('oee', min(1.0, round(bottleneck.oee + 0.05, 4))),
    ))
    if line.materials:
        variants.append((
            '原料价格+10%',
            lambda c: [
                setattr(m, 'unit_cost', round(m.unit_cost * 1.1, 4))
                for m in c.materials
            ],
            {'material_prices': {
                m.name: round(m.unit_cost * 1.1, 4) for m in line.materials
            }},
        ))
        variants.append((
            '原料价格-10%',
            lambda c: [
                setattr(m, 'unit_cost', round(m.unit_cost * 0.9, 4))
                for m in c.materials
            ],
            {'material_prices': {
                m.name: round(m.unit_cost * 0.9, 4) for m in line.materials
            }},
        ))

    for label, apply, apply_info in variants:
        clone = copy.deepcopy(line)
        apply(clone)
        result = SimulationEngine(clone).run_sync(duration_hours, warmup_minutes)
        unit_cost = result.kpis.get('unit_cost', 0.0)
        material_cost = result.kpis.get('material_cost', 0.0)
        total_cost = result.kpis.get('total_cost', 0.0)
        scenarios.append({
            'label': label,
            'total_output': result.total_output,
            'unit_cost': unit_cost,
            'material_cost': material_cost,
            'total_cost': total_cost,
            'actual_unit_cost': (
                total_cost / result.total_output
                if result.total_output > 0 else 0.0
            ),
            'delta_output': result.total_output - base_result.total_output,
            'delta_unit_cost': round(unit_cost - base_unit_cost, 4),
            'delta_material_cost': round(material_cost - base_material_cost, 4),
            'apply': apply_info,
        })

    return scenarios


def run_sweep(
    line: ProductionLine,
    param: str,
    values: List[float],
    station_id: Optional[str] = None,
    duration_hours: float = 8.0,
    warmup_minutes: float = 0.0,
) -> List[Dict]:
    """
    批量试算（V3.2 P1）

    对同一参数的一组取值逐一仿真，对比产出/日产量/单位成本/UPPH。
    参数支持：worker_count / machine_takt / oee（作用于指定工序，
    缺省为瓶颈工序）与 shift_hours（作用于产线）。
    """
    target = line.get_station(station_id) if station_id else line.find_bottleneck()
    rows: List[Dict] = []
    for value in values:
        clone = copy.deepcopy(line)
        if param == "shift_hours":
            clone.shift_hours = max(1, int(value))
        elif param in ("worker_count", "machine_takt", "oee"):
            if target is None:
                continue
            station = clone.get_station(target.id)
            if station is None:
                continue
            if param == "worker_count":
                station.worker_count = max(1, int(value))
            elif param == "machine_takt":
                station.machine_takt = max(0.1, float(value))
            else:
                station.oee = min(1.0, max(0.01, float(value)))
        else:
            continue
        result = SimulationEngine(clone).run_sync(duration_hours, warmup_minutes)
        rows.append({
            'label': f"{param}={value}",
            'total_output': result.total_output,
            'daily_output': round(result.kpis.get('daily_output', 0.0), 1),
            'unit_cost': result.kpis.get('unit_cost', 0.0),
            'upph': result.kpis.get('upph', 0.0),
        })
    return rows
