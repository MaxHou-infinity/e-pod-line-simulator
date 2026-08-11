"""
人力规划模块（V3.2 P0）

面向 HRBP/HR 的纯计算层：目标产量 → 岗位/人数 → 排班 → 成本 →
招聘缺口 → 爬坡达产。不依赖仿真引擎，便于独立测试与报告。

说明：人力需求为规划估算，不构成用工承诺；协同工序加人不提升产能。
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from src.models import CollaborationType, ProductionLine


@dataclass
class ShiftPlan:
    """班次计划（V3.2）"""
    shifts_per_day: int = 1
    shift_hours: float = 8.0
    break_minutes: int = 60
    overtime_hours_per_shift: float = 0.0

    def effective_hours_per_day(self) -> float:
        """每日有效工时（小时）= 班次数 ×（班次时长 − 休息 + 加班）"""
        per_shift = (
            self.shift_hours
            - self.break_minutes / 60.0
            + self.overtime_hours_per_shift
        )
        return max(0.0, self.shifts_per_day * per_shift)


@dataclass
class LaborCostConfig:
    """人力成本参数（V3.2）"""
    base_hourly_wage: float = 20.0
    overtime_multiplier: float = 1.5
    social_insurance_rate: float = 0.30
    recruitment_cost_per_head: float = 0.0
    training_cost_per_head: float = 0.0
    absence_rate: float = 0.0
    monthly_turnover_rate: float = 0.0


@dataclass
class LearningCurveConfig:
    """新员工爬坡曲线（V3.2）"""
    ramp_days: int = 90
    start_efficiency: float = 0.6
    target_efficiency: float = 1.0

    def efficiency_at(self, day: int) -> float:
        """第 day 天（1 起）的综合效率，线性爬坡至目标值"""
        if self.ramp_days <= 0:
            return self.target_efficiency
        progress = min(max(day, 0), self.ramp_days) / self.ramp_days
        return (
            self.start_efficiency
            + (self.target_efficiency - self.start_efficiency) * progress
        )


def _per_head_capacity(station) -> float:
    """单人的可支撑产能（单位/h）"""
    capacity = station.get_capacity()
    if station.worker_count <= 0:
        return capacity
    if station.collaboration_type == CollaborationType.COLLABORATIVE:
        # 协同：加人不提升产能，按整线实际配人估算
        return capacity
    return capacity / station.worker_count


def required_headcount_by_station(
    line: ProductionLine,
    daily_target: float,
    shift_plan: ShiftPlan,
) -> Dict[str, int]:
    """按目标日产量反推各工序所需人数"""
    daily_hours = shift_plan.effective_hours_per_day()
    required_hourly = daily_target / daily_hours if daily_hours > 0 else 0.0
    result: Dict[str, int] = {}
    for station in line.stations:
        per_head = _per_head_capacity(station)
        if per_head <= 0:
            result[station.id] = station.worker_count
            continue
        needed = math.ceil(required_hourly / per_head)
        if station.collaboration_type == CollaborationType.COLLABORATIVE:
            needed = max(station.worker_count, 1)
        result[station.id] = max(1, needed)
    return result


def required_headcount_by_role(
    line: ProductionLine,
    daily_target: float,
    shift_plan: ShiftPlan,
) -> Dict[str, int]:
    """按工种汇总所需人数；未出现在工序中的支持工种沿用 labor_config"""
    by_station = required_headcount_by_station(line, daily_target, shift_plan)
    by_role: Dict[str, int] = {}
    for station in line.stations:
        role = station.job_role.value if station.job_role else "general"
        by_role[role] = by_role.get(role, 0) + by_station[station.id]
    for role, count in line.labor_config.items():
        if role not in by_role:
            by_role[role] = count
    return by_role


def total_headcount(
    line: ProductionLine,
    daily_target: float,
    shift_plan: ShiftPlan,
) -> int:
    """目标产量下的总人数"""
    return sum(
        required_headcount_by_station(line, daily_target, shift_plan).values()
    )


def calculate_labor_costs(
    line: ProductionLine,
    headcount: int,
    shift_plan: ShiftPlan,
    cost: LaborCostConfig,
    days_per_month: int = 26,
) -> Dict[str, float]:
    """人力成本测算（日/月/单位）"""
    base_pay_per_head_day = cost.base_hourly_wage * (
        shift_plan.shift_hours
        + shift_plan.overtime_hours_per_shift * cost.overtime_multiplier
    )
    gross_per_head_day = base_pay_per_head_day * (1 + cost.social_insurance_rate)

    coverage = 1.0
    if 0 <= cost.absence_rate < 1:
        coverage = 1.0 / (1.0 - cost.absence_rate)
    covered_headcount = math.ceil(headcount * coverage)

    daily_labor_cost = gross_per_head_day * covered_headcount
    monthly_labor_cost = daily_labor_cost * days_per_month

    replacements_per_month = math.ceil(headcount * cost.monthly_turnover_rate)
    monthly_recruit_training = replacements_per_month * (
        cost.recruitment_cost_per_head + cost.training_cost_per_head
    )
    monthly_total = monthly_labor_cost + monthly_recruit_training

    daily_output = max(line.calculate_daily_output(), 1.0)
    return {
        'headcount': headcount,
        'covered_headcount': covered_headcount,
        'daily_labor_cost': round(daily_labor_cost, 2),
        'monthly_labor_cost': round(monthly_labor_cost, 2),
        'monthly_recruit_training': round(monthly_recruit_training, 2),
        'monthly_total': round(monthly_total, 2),
        'per_unit_labor_cost': round(daily_labor_cost / daily_output, 4),
    }


def weekly_hiring_gap(
    required: Dict[str, int],
    current: Dict[str, int],
    hiring_plan: List[Tuple[int, str, int]],
    weeks: int = 12,
) -> List[Dict]:
    """按周招聘缺口时间线（到岗人数按周累计）"""
    rows = []
    for week in range(1, weeks + 1):
        gap: Dict[str, int] = {}
        for role, req in required.items():
            cur = current.get(role, 0)
            arrivals = sum(
                qty for (w, r, qty) in hiring_plan if r == role and w <= week
            )
            gap[role] = max(0, req - cur - arrivals)
        rows.append({
            'week': week,
            'gap': gap,
            'total_gap': sum(gap.values()),
        })
    return rows


def ramp_days_to_full(
    line: ProductionLine,
    daily_target: float,
    shift_plan: ShiftPlan,
    required: Dict[str, int],
    current: Dict[str, int],
    learning: LearningCurveConfig,
) -> int:
    """
    按爬坡曲线估算达产天数

    近似模型：以总人数为代理，新增人力按效率曲线爬坡；
    当前人力已满足目标时返回 0。
    """
    total_required = sum(required.values())
    total_current = sum(current.values())
    new_hires = max(0, total_required - total_current)
    if new_hires == 0 or total_required == 0:
        return 0
    for day in range(1, learning.ramp_days + 2):
        efficiency = learning.efficiency_at(day)
        effective = total_current + new_hires * efficiency
        if effective >= total_required - 1e-6:
            return day
    return learning.ramp_days


def build_hr_summary(
    line: ProductionLine,
    daily_target: float,
    shift_plan: ShiftPlan,
    cost: LaborCostConfig,
    learning: LearningCurveConfig,
    current: Dict[str, int],
    hiring_plan: List[Tuple[int, str, int]],
    weeks: int = 12,
) -> Dict:
    """汇总 HR 人力规划结果（供报告与 GUI 使用）"""
    by_station = required_headcount_by_station(line, daily_target, shift_plan)
    by_role = required_headcount_by_role(line, daily_target, shift_plan)
    total = sum(by_station.values())
    costs = calculate_labor_costs(line, total, shift_plan, cost)
    gap_rows = weekly_hiring_gap(by_role, current, hiring_plan, weeks)
    days_to_full = ramp_days_to_full(
        line, daily_target, shift_plan, by_role, current, learning
    )
    return {
        'daily_target': daily_target,
        'effective_hours_per_day': shift_plan.effective_hours_per_day(),
        'headcount_by_station': by_station,
        'headcount_by_role': by_role,
        'total_headcount': total,
        'costs': costs,
        'weekly_gap': gap_rows,
        'days_to_full': days_to_full,
    }
