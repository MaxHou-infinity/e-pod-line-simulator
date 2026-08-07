"""方案管理单元测试"""

from src.models import ProductionLine, Station
from src.scenario_manager import ScenarioManager


def make_line(name="方案产线"):
    line = ProductionLine(name)
    line.add_station(Station("s01", "注油", 25, 2))
    return line


def test_max_scenarios_is_five():
    manager = ScenarioManager()
    assert manager.MAX_SCENARIOS == 5


def test_save_up_to_five_scenarios():
    manager = ScenarioManager()
    for i in range(5):
        ok, err = manager.save_scenario(f"方案{i+1}", make_line(), "测试")
        assert ok, err
    ok, err = manager.save_scenario("方案6", make_line())
    assert ok is False
    assert "上限" in err


def test_persistence_roundtrip(tmp_path):
    path = str(tmp_path / "scenarios.json")
    manager = ScenarioManager()
    manager.set_storage_path(path)
    manager.save_scenario("方案A", make_line(), "描述A")
    manager.save_scenario("方案B", make_line(), "描述B")

    loaded = ScenarioManager()
    assert loaded.load_from_file(path) is True
    assert loaded.get_scenario_count() == 2
    assert loaded.get_scenario("方案A").description == "描述A"
    assert loaded.get_scenario("方案B").production_line.stations[0].name == "注油"


def test_delete_persists(tmp_path):
    path = str(tmp_path / "scenarios.json")
    manager = ScenarioManager()
    manager.set_storage_path(path)
    manager.save_scenario("方案A", make_line())
    manager.delete_scenario("方案A")

    loaded = ScenarioManager()
    loaded.load_from_file(path)
    assert loaded.get_scenario_count() == 0
