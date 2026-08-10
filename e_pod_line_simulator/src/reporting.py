"""
报告导出模块 - 将仿真结果导出为 Excel / PDF

功能：
- export_excel(): 导出多 Sheet 的 Excel 报告（KPI、工序产出、报警、WIP 采样、切换事件）
- export_pdf(): 导出 PDF 摘要报告（中文字体优先，缺失时回退 Helvetica）
- export_report(): 按文件扩展名自动分派
"""

import os
from typing import List, Optional

from src.models import SimulationResult


# 中文字体候选路径（按优先级）
_CN_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]

_CN_FONT_NAME = None
_CN_FONT_REGISTERED = False


def _register_cn_font() -> str:
    """
    注册中文字体，返回字体名称

    Returns:
        str: 可用的字体名称（找不到中文字体时回退 "Helvetica"）
    """
    global _CN_FONT_NAME, _CN_FONT_REGISTERED
    if _CN_FONT_REGISTERED:
        return _CN_FONT_NAME

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        for path in _CN_FONT_CANDIDATES:
            if not os.path.exists(path):
                continue
            try:
                font_name = f"CN_{os.path.basename(path).replace('.', '_')}"
                pdfmetrics.registerFont(TTFont(font_name, path))
                _CN_FONT_NAME = font_name
                break
            except Exception:
                continue
    except Exception:
        pass

    if _CN_FONT_NAME is None:
        _CN_FONT_NAME = "Helvetica"
    _CN_FONT_REGISTERED = True
    return _CN_FONT_NAME


def _kpi_rows(result: SimulationResult) -> List[List[str]]:
    """构造 KPI 表格行（中文标签 + 值）"""
    k = result.kpis
    duration_minutes = result.duration_seconds / 60.0
    unit = result.unit
    return [
        ["产线名称", result.line_name],
        ["仿真时长(分钟)", f"{duration_minutes:.1f}"],
        [f"总产出({unit})", f"{result.total_output}"],
        [f"瓶颈产能({unit}/h)", f"{k.get('bottleneck_capacity', 0):.1f}"],
        [f"预计日产量({unit})", f"{k.get('daily_output', 0):.0f}"],
        ["日成本(元)", f"{k.get('total_cost', 0):.0f}"],
        [f"单位成本(元/{unit})", f"{k.get('unit_cost', 0):.3f}"],
        ["产线平衡率", f"{k.get('balance_rate', 0) * 100:.1f}%"],
        [f"UPPH({unit}/人·h)", f"{k.get('upph', 0):.1f}"],
    ]


def export_excel(result: SimulationResult, file_path: str) -> bool:
    """
    导出 Excel 报告

    Args:
        result: 仿真结果
        file_path: 保存路径（.xlsx）

    Returns:
        bool: 是否成功
    """
    try:
        import pandas as pd

        kpi_df = pd.DataFrame(_kpi_rows(result), columns=["指标", "值"])

        station_rows = []
        for station in result.station_outputs:
            station_rows.append({
                "工序ID": station,
                f"产出({result.unit})": result.station_outputs.get(station, 0),
                f"WIP({result.unit})": result.station_wips.get(station, 0),
            })
        station_df = pd.DataFrame(station_rows)

        alert_df = pd.DataFrame([
            {
                "时间(分钟)": round(a.timestamp_minutes, 1),
                "级别": a.severity,
                "类型": a.alert_type,
                "消息": a.message,
                "建议": a.suggestion,
            }
            for a in result.alerts
        ])

        wip_df = pd.DataFrame(result.wip_samples)
        changeover_df = pd.DataFrame(result.changeover_events)
        batch_df = pd.DataFrame(result.batch_results)
        quality_df = pd.DataFrame(result.quality_results)

        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            kpi_df.to_excel(writer, sheet_name="KPI", index=False)
            station_df.to_excel(writer, sheet_name="工序产出", index=False)
            alert_df.to_excel(writer, sheet_name="报警记录", index=False)
            wip_df.to_excel(writer, sheet_name="WIP采样", index=False)
            changeover_df.to_excel(writer, sheet_name="切换事件", index=False)
            if not batch_df.empty:
                batch_df.to_excel(writer, sheet_name="批次结果", index=False)
            if not quality_df.empty:
                quality_df.to_excel(writer, sheet_name="质量门", index=False)

        return True
    except Exception:
        return False


def export_pdf(result: SimulationResult, file_path: str) -> bool:
    """
    导出 PDF 摘要报告

    Args:
        result: 仿真结果
        file_path: 保存路径（.pdf）

    Returns:
        bool: 是否成功
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        font_name = _register_cn_font()

        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CNTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=18,
            leading=24,
        )
        body_style = ParagraphStyle(
            "CNBody",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=10,
            leading=14,
        )
        header_style = ParagraphStyle(
            "CNHeader",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=11,
            leading=14,
        )

        story = [
            Paragraph(f"电子烟产线仿真报告 - {result.line_name}", title_style),
            Spacer(1, 8 * mm),
            Paragraph(
                f"仿真时长：{result.duration_seconds / 60:.1f} 分钟　"
                f"总产出：{result.total_output} {result.unit}",
                body_style,
            ),
            Spacer(1, 6 * mm),
            Paragraph("一、核心 KPI", header_style),
            Spacer(1, 3 * mm),
        ]

        kpi_table = Table(_kpi_rows(result), colWidths=[80 * mm, 90 * mm])
        kpi_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)

        if result.alerts:
            story.append(Spacer(1, 6 * mm))
            story.append(Paragraph("二、报警记录", header_style))
            story.append(Spacer(1, 3 * mm))
            alert_rows = [["时间(分钟)", "级别", "消息"]]
            for alert in result.alerts[:50]:
                alert_rows.append([
                    f"{alert.timestamp_minutes:.1f}",
                    alert.severity,
                    alert.message,
                ])
            alert_table = Table(alert_rows, colWidths=[25 * mm, 25 * mm, 120 * mm])
            alert_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(alert_table)

        if result.batch_results:
            story.append(Spacer(1, 6 * mm))
            story.append(Paragraph("三、批次结果", header_style))
            story.append(Spacer(1, 3 * mm))
            batch_rows = [["批次ID", "配方", "周期(分钟)", "合格率", "产出(L)"]]
            for b in result.batch_results:
                batch_rows.append([
                    str(b.get("batch_id", "")),
                    str(b.get("recipe_name", "")),
                    f"{b.get('cycle_min', 0):.1f}",
                    f"{b.get('pass_rate', 0) * 100:.1f}%",
                    f"{b.get('yield_l', 0):.1f}",
                ])
            batch_table = Table(batch_rows, colWidths=[30 * mm, 35 * mm, 35 * mm, 30 * mm, 40 * mm])
            batch_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(batch_table)

        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(
            "注：本报告由仿真工具自动生成，结果作为产线设计参考，"
            "建议结合实际生产数据校准 OEE 等参数。",
            body_style,
        ))

        doc.build(story)
        return True
    except Exception:
        return False


def export_report(result: SimulationResult, file_path: str) -> bool:
    """
    按文件扩展名导出报告

    Args:
        result: 仿真结果
        file_path: 保存路径（.xlsx 或 .pdf）

    Returns:
        bool: 是否成功
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".xlsx":
        return export_excel(result, file_path)
    if ext == ".pdf":
        return export_pdf(result, file_path)
    return False
