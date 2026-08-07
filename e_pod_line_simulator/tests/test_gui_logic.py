"""GUI 交互逻辑单元测试（不依赖显示环境）"""

from src.gui_canvas import compute_reorder_order
from src.gui_panels import build_template_line


def test_compute_reorder_order_move_to_middle():
    order = ["s01", "s02", "s03"]
    positions = {"s01": (0, 0), "s02": (100, 0), "s03": (200, 0)}
    new_order = compute_reorder_order(order, "s03", positions, 150, 0)
    assert new_order == ["s01", "s03", "s02"]


def test_compute_reorder_order_invalid():
    order = ["s01", "s02"]
    positions = {"s01": (0, 0), "s02": (100, 0)}
    assert compute_reorder_order(order, "missing", positions, 0, 0) is None
    assert compute_reorder_order(order, "s01", {"s01": (0, 0)}, 0, 0) is None


def test_build_template_line():
    assert len(build_template_line("simple").stations) == 3
    assert len(build_template_line("standard").stations) == 5
    assert len(build_template_line("complex").stations) == 8
    assert build_template_line("blank").stations == []
    assert build_template_line("complex").stations[0].name == "镭雕"


def test_dialog_handler_methods_exist():
    from src.gui_panels import (
        SaveScenarioDialog,
        ScenarioManageDialog,
        ShiftConfigDialog,
        StationDialog,
        WizardDialog,
    )

    assert hasattr(ShiftConfigDialog, "_btn_ok")
    assert hasattr(ShiftConfigDialog, "_btn_cancel")
    assert hasattr(StationDialog, "_btn_ok")
    assert hasattr(StationDialog, "_btn_cancel")
    assert hasattr(SaveScenarioDialog, "_on_confirm")
    assert hasattr(SaveScenarioDialog, "_on_cancel")
    assert hasattr(WizardDialog, "_next")
    assert hasattr(WizardDialog, "_cancel")
    assert hasattr(ScenarioManageDialog, "_delete_selected")
