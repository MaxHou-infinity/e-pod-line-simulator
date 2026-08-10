"""仿真引擎单元测试（headless 模式与切换事件）"""

import time

import pytest

from src.models import (
    CollaborationType,
    ProductionType,
    ProductionLine,
    Recipe,
    Station,
    Tank,
    Batch,
    create_liquid_line,
)
from src.simulation import SimulationEngine, detect_waste


def make_line(name="测试产线"):
    line = ProductionLine(name, shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "注油", 1.0, 1))
    line.add_station(Station("s02", "包装", 1.0, 1))
    return line


def test_headless_run_returns_result():
    result = SimulationEngine(make_line()).run_sync(duration_hours=1.0)

    assert result.total_output > 0
    assert result.line_name == "测试产线"
    assert result.station_outputs["s01"] > 0
    assert result.kpis["bottleneck_capacity"] > 0
    assert result.duration_seconds == 3600


def test_changeover_reduces_output_and_records_event():
    engine = SimulationEngine(make_line())
    engine.trigger_changeover("s01", minutes=30)
    result_with = engine.run_sync(duration_hours=1.0)

    result_without = SimulationEngine(make_line()).run_sync(duration_hours=1.0)

    assert len(result_with.changeover_events) == 1
    assert result_with.changeover_events[0]["station_id"] == "s01"
    assert any(a.alert_type == "changeover" for a in result_with.alerts)
    assert result_with.total_output < result_without.total_output


def test_trigger_changeover_validates_station():
    engine = SimulationEngine(make_line())
    with pytest.raises(ValueError):
        engine.trigger_changeover("missing", minutes=45)
    with pytest.raises(ValueError):
        engine.trigger_changeover("s01", minutes=0)


def test_wip_samples_collected():
    result = SimulationEngine(make_line()).run_sync(duration_hours=0.5)
    assert len(result.wip_samples) > 0
    assert all("wip" in sample for sample in result.wip_samples)


def test_detect_waste():
    line = ProductionLine("浪费测试")
    line.add_station(Station("s01", "瓶颈", 30.0, 1))
    line.add_station(Station("s02", "过剩", 10.0, 5))
    bottleneck_capacity = line.get_bottleneck_capacity()
    alerts = detect_waste(line.stations, bottleneck_capacity)
    assert any(a.alert_type == "waste" for a in alerts)


def test_set_callback_and_state_updates():
    engine = SimulationEngine(make_line())
    collected = []
    engine.set_callback(lambda state: collected.append(state))
    result = engine.run_sync(duration_hours=0.05)
    assert len(collected) > 0
    assert result.total_output > 0


def test_callback_exception_does_not_crash_simulation():
    engine = SimulationEngine(make_line())
    engine.set_callback(lambda state: (_ for _ in ()).throw(RuntimeError("模拟异常")))
    result = engine.run_sync(duration_hours=0.02)
    assert result.total_output >= 0


def test_changeover_event_for_other_station_is_routed():
    engine = SimulationEngine(make_line())
    engine.trigger_changeover("s02", minutes=10)
    result = engine.run_sync(duration_hours=0.2)
    assert len(result.changeover_events) == 1
    assert result.changeover_events[0]["station_id"] == "s02"


def test_multiple_changeover_events_chain_in_order():
    engine = SimulationEngine(make_line())
    engine.trigger_changeover("s01", minutes=10)
    engine.trigger_changeover("s01", minutes=5)
    result_two = engine.run_sync(duration_hours=1.0)

    engine_single = SimulationEngine(make_line())
    engine_single.trigger_changeover("s01", minutes=10)
    result_single = engine_single.run_sync(duration_hours=1.0)

    assert len(result_two.changeover_events) == 2
    assert result_two.total_output < result_single.total_output


def test_collaborative_station_run():
    line = ProductionLine("协同产线", shift_hours=1, break_minutes=0)
    line.add_station(Station(
        "s01", "组装", 5.0, 3,
        collaboration_type=CollaborationType.COLLABORATIVE,
    ))
    result = SimulationEngine(line).run_sync(duration_hours=0.1)
    assert result.total_output > 0


def test_wip_blockage_alert():
    line = ProductionLine("堵塞测试", shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "快工序", 1.0, 10, buffer_capacity=5))
    line.add_station(Station("s02", "慢工序", 100.0, 1, buffer_capacity=5))
    result = SimulationEngine(line).run_sync(duration_hours=1.0)
    assert any(a.alert_type == "blockage" for a in result.alerts)


def test_wip_respects_buffer_capacity():
    line = ProductionLine("WIP边界测试", shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "快工序", 1.0, 10, buffer_capacity=100))
    line.add_station(Station("s02", "慢工序", 100.0, 1, buffer_capacity=5))
    result = SimulationEngine(line).run_sync(duration_hours=1.0)

    # WIP 采样恒为非负且不超过缓冲区容量
    assert all(0 <= sample["wip"] <= 5 for sample in result.wip_samples)
    # 结果汇总中的 WIP 同样受容量约束
    assert 0 <= result.station_wips["s02"] <= 5
    # 下游满缓冲时触发堵塞报警
    assert any(a.alert_type == "blockage" for a in result.alerts)


def test_empty_line_headless_run():
    line = ProductionLine("空产线")
    result = SimulationEngine(line).run_sync(duration_hours=0.02)
    assert result.total_output == 0


def test_threaded_run_pause_resume_stop():
    engine = SimulationEngine(make_line())
    engine.set_callback(lambda state: None)
    engine.run(duration_hours=0.01, speed=10)
    assert engine.is_running is True
    time.sleep(0.3)
    engine.pause()
    assert engine.is_paused is True
    time.sleep(0.2)
    engine.resume()
    assert engine.is_paused is False
    time.sleep(0.3)
    engine.stop()
    time.sleep(0.1)
    assert engine.is_running is False
    results = engine.get_results()
    assert "total_output" in results


def test_threaded_run_real_time_mode():
    engine = SimulationEngine(make_line())
    engine.run(duration_hours=2 / 3600, speed=1)
    time.sleep(0.3)
    engine.stop()
    time.sleep(0.2)
    assert engine.is_running is False


def test_liquid_batch_simulation_matches_manual():
    line = create_liquid_line()
    recipe = line.recipes[0]
    result = SimulationEngine(line).run_sync(duration_hours=24.0)

    assert len(result.batch_results) == 1
    batch = result.batch_results[0]
    assert batch["status"] == "released"
    assert batch["recipe_name"] == "经典烟草"

    # 手工计算：调配 + 陈化 + 灌装 + QC（分钟）
    fill_min = recipe.batch_volume_l / recipe.filling_rate_l_per_h * 60
    expected_cycle = (
        recipe.mixing_time_min + recipe.aging_time_min + fill_min + recipe.qc_time_min
    )
    assert abs(batch["cycle_min"] - expected_cycle) / expected_cycle < 0.03

    # 罐液位 = 批次量 × 收率
    assert line.tanks[0].current_level_l == pytest.approx(500 * 0.95, rel=1e-6)
    # 人力汇总
    assert result.labor_summary["qc_technician"] == 1


def test_cleaning_between_recipes():
    line = ProductionLine("换配方测试", production_type=ProductionType.LIQUID_FILLING)
    line.recipes.append(Recipe(
        name="配方A", batch_volume_l=100, yield_rate=0.95,
        mixing_time_min=10, aging_time_min=0,
        filling_rate_l_per_h=600, qc_time_min=5, clean_time_min=0,
    ))
    line.recipes.append(Recipe(
        name="配方B", batch_volume_l=100, yield_rate=0.95,
        mixing_time_min=10, aging_time_min=0,
        filling_rate_l_per_h=600, qc_time_min=5, clean_time_min=30,
    ))
    line.tanks.append(Tank("T01", "调配罐", 1000, 0))
    line.batches.append(Batch("B001", "配方A", 100))
    line.batches.append(Batch("B002", "配方B", 100))

    result = SimulationEngine(line).run_sync(duration_hours=24.0)

    assert len(result.cleaning_events) == 1
    assert result.cleaning_events[0]["recipe_from"] == "配方A"
    assert result.cleaning_events[0]["recipe_to"] == "配方B"
    assert result.cleaning_events[0]["clean_min"] == 30

    batch_b = result.batch_results[1]
    fill_min = 100 / 600 * 60
    expected_b = 10 + fill_min + 5  # 调配+灌装+QC（清洗在批次间单独计时）
    assert abs(batch_b["cycle_min"] - expected_b) < 0.03 * expected_b
    # 清洗发生在 B 开始前
    assert result.cleaning_events[0]["time"] < batch_b["start_time"]


def test_pouch_machine_takt_throughput():
    line = ProductionLine("袋装节拍测试", production_type=ProductionType.POUCH_PACKAGING)
    line.add_station(Station(
        "p01", "填充机", 1.0, 2,
        machine_takt=1.0, oee=1.0, efficiency=1.0,
        changeover_time=0, clean_time_minutes=0,
    ))
    result = SimulationEngine(line).run_sync(duration_hours=1.0)
    # 理论：3600 秒 / 1.0 秒 × 2 机台 = 7200 袋
    assert 7100 <= result.total_output <= 7300


def test_liquid_quality_gate_rework():
    line = create_liquid_line()
    qc = line.get_station("s03")
    qc.sampling_rate = 1.0
    qc.defect_rate = 1.0
    qc.rework_minutes = 15.0

    engine = SimulationEngine(line)
    engine.random_seed = 42
    result = engine.run_sync(duration_hours=24.0)

    assert len(result.quality_results) == 1
    assert result.quality_results[0]["rework_count"] >= 1
    assert result.quality_results[0]["pass_rate"] < 1.0
    assert result.batch_results[0]["pass_rate"] < 1.0


def test_pouch_quality_gate_reduces_output():
    line = ProductionLine("袋装质检测试", production_type=ProductionType.POUCH_PACKAGING)
    line.add_station(Station(
        "p01", "在线检测", 1.0, 1,
        machine_takt=1.0, oee=1.0, efficiency=1.0,
        changeover_time=0, clean_time_minutes=0,
        sampling_rate=1.0, defect_rate=1.0, rework_minutes=5.0,
    ))
    engine = SimulationEngine(line)
    engine.random_seed = 42
    result = engine.run_sync(duration_hours=0.5)

    assert len(result.quality_results) > 0
    assert all(q["defect"] for q in result.quality_results)
    # 缺陷率 100% 时合格产出为 0（缺陷件返工隔离，不计产出）
    assert result.total_output == 0
    assert len(result.quality_results) >= 3
