"""报告导出单元测试"""

import os

from src.models import ProductionLine, Station
from src.reporting import export_excel, export_pdf, export_report
from src.simulation import SimulationEngine


def make_result():
    line = ProductionLine("报告测试", shift_hours=1, break_minutes=0)
    line.add_station(Station("s01", "注油", 1.0, 1))
    line.add_station(Station("s02", "包装", 1.0, 1))
    return SimulationEngine(line).run_sync(duration_hours=0.1)


def test_export_excel(tmp_path):
    path = str(tmp_path / "report.xlsx")
    assert export_excel(make_result(), path) is True
    assert os.path.exists(path)

    from openpyxl import load_workbook

    wb = load_workbook(path)
    assert "KPI" in wb.sheetnames
    assert "工序产出" in wb.sheetnames
    assert "报警记录" in wb.sheetnames
    assert "WIP采样" in wb.sheetnames
    assert "切换事件" in wb.sheetnames


def test_export_pdf(tmp_path):
    path = str(tmp_path / "report.pdf")
    assert export_pdf(make_result(), path) is True
    assert os.path.exists(path)
    with open(path, "rb") as f:
        assert f.read(4) == b"%PDF"


def test_export_report_dispatch(tmp_path):
    xlsx_path = str(tmp_path / "a.xlsx")
    pdf_path = str(tmp_path / "b.pdf")
    bad_path = str(tmp_path / "c.txt")
    result = make_result()
    assert export_report(result, xlsx_path) is True
    assert export_report(result, pdf_path) is True
    assert export_report(result, bad_path) is False
