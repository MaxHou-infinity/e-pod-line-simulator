"""
GUI面板组件 - 各种功能面板

这个文件包含所有面板组件：
- ConfigPanel: 配置面板（工序列表、编辑功能）
- KPIDashboard: KPI仪表盘（显示关键指标）
- AlertPanel: 报警面板（显示瓶颈、浪费等警报）
- StationDialog: 工序编辑对话框

面板设计原则：
1. 独立性：每个面板是独立的组件，可以单独测试
2. 回调机制：通过回调函数与主窗口通信
3. 数据绑定：面板显示数据，但不直接修改数据
"""

import tkinter as tk
import os
import webbrowser
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional, Callable, Dict, Any

from src.models import Station, Alert, CollaborationType, ProductionLine
from src.utils import validate_station, get_alert_color
from src.scenario_manager import ScenarioManager
from src.theme import ALERT_ICONS, COLORS, ToolTip, resolve_font_family
from src.glossary import GLOSSARY
from src.version import (
    BUG_REPORT_URL,
    WECHAT_QR_PATH,
    WECHAT_QR_SMALL_PATH,
    __version__,
)
from src.models import (
    ProductionType,
    create_liquid_line,
    create_pouch_line,
)


def build_template_line(key: str) -> ProductionLine:
    """
    按模板 key 创建产线（纯函数，供向导与测试复用）

    Args:
        key: simple / standard / complex / blank

    Returns:
        ProductionLine: 新产线
    """
    from src.models import CollaborationType

    line = ProductionLine("新产线")
    if key == "blank":
        return line

    for idx, (name, time, workers, mode) in enumerate(WizardDialog.TEMPLATES[key], 1):
        line.add_station(Station(
            id=f"s{idx:02d}",
            name=name,
            process_time=time,
            worker_count=workers,
            collaboration_type=(
                CollaborationType.PARALLEL if mode == "parallel" else CollaborationType.COLLABORATIVE
            ),
        ))
    return line


def station_edit_fields(production_type: ProductionType) -> set:
    """
    工序编辑字段与生产类型的映射（V1.3）

    - assembly：不显示任何 V1.3 字段
    - liquid_filling：清洗时间（CIP/SIP）+ 质量门（抽检/缺陷/返工）
    - pouch_packaging：机台节拍 + 质量门（抽检/缺陷/返工），
      清洗时间对高速包装无排程意义，不显示
    """
    quality = {'sampling_rate', 'defect_rate', 'rework_minutes'}
    if production_type == ProductionType.LIQUID_FILLING:
        return {'clean_time_minutes'} | quality
    if production_type == ProductionType.POUCH_PACKAGING:
        return {'machine_takt'} | quality
    return set()


class ConfigPanel(ttk.Frame):
    """
    配置面板 - 显示和管理工序列表
    
    功能：
    - 显示所有工序
    - 提供添加、编辑、删除按钮
    - 支持工序选择
    
    使用方式：
        panel = ConfigPanel(parent, on_add=add_callback, ...)
        panel.update_stations(stations)
    """
    
    def __init__(
        self,
        parent,
        on_add: Optional[Callable] = None,
        on_edit: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
        on_select: Optional[Callable] = None
    ):
        """
        初始化配置面板
        
        Args:
            parent: 父组件
            on_add: 添加工序回调函数
            on_edit: 编辑工序回调函数
            on_delete: 删除工序回调函数
            on_select: 选择工序回调函数
        """
        super().__init__(parent)
        
        # 回调函数
        self.on_add = on_add
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_select = on_select
        
        # 当前选中的工序和产线引用（用于查找Station对象）
        self.selected_station: Optional[Station] = None
        self.production_line: Optional[Any] = None  # 保存产线引用，用于查找Station对象
        
        # 创建界面
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """创建界面组件"""
        # 标题 + 术语速查
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, pady=5)
        ttk.Label(title_frame, text="工序配置", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=5)
        self.production_type_label = ttk.Label(
            title_frame,
            text="类型：烟弹组装",
            foreground=COLORS['text_secondary'],
            font=('Arial', 9),
        )
        self.production_type_label.pack(side=tk.LEFT, padx=8)
        self.btn_glossary = ttk.Button(
            title_frame,
            text="术语?",
            width=6,
            command=self._open_glossary,
        )
        self.btn_glossary.pack(side=tk.RIGHT, padx=5)
        ToolTip(self.btn_glossary, "查看供应链关键术语说明")
        
        # 按钮框架
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加按钮
        self.btn_add = ttk.Button(button_frame, text="添加", command=self._btn_add)
        self.btn_add.pack(side=tk.LEFT, padx=2)
        ToolTip(self.btn_add, "添加新工序")

        # 编辑按钮
        self.btn_edit = ttk.Button(button_frame, text="编辑", command=self._btn_edit)
        self.btn_edit.pack(side=tk.LEFT, padx=2)
        ToolTip(self.btn_edit, "编辑选中工序")

        # 删除按钮
        self.btn_delete = ttk.Button(button_frame, text="删除", command=self._btn_delete)
        self.btn_delete.pack(side=tk.LEFT, padx=2)
        ToolTip(self.btn_delete, "删除选中工序")
        
        # 工序列表（使用Treeview显示）
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Treeview（表格视图）
        columns = ('name', 'time', 'workers', 'capacity')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # 设置列标题
        self.tree.heading('name', text='工序名称')
        self.tree.heading('time', text='耗时(秒)')
        self.tree.heading('workers', text='人数')
        self.tree.heading('capacity', text='产能(颗/h)')
        
        # 设置列宽
        self.tree.column('name', width=100)
        self.tree.column('time', width=80)
        self.tree.column('workers', width=60)
        self.tree.column('capacity', width=100)
        
        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def update_stations(self, stations: List[Station], production_line: Optional[Any] = None) -> None:
        """
        更新工序列表显示
        
        Args:
            stations: 工序列表
            production_line: 产线对象（可选，用于查找Station对象）
        """
        # 保存产线引用
        if production_line is not None:
            self.production_line = production_line
            self.set_production_type(production_line.production_type)
        
        # 清空现有数据
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 重置选中状态
        self.selected_station = None
        
        # 添加新数据
        for station in stations:
            capacity = station.get_capacity()
            self.tree.insert(
                '',
                tk.END,
                values=(
                    station.name,
                    f"{station.process_time:.1f}",
                    station.worker_count,
                    f"{capacity:.0f}"
                ),
                tags=(station.id,)  # 使用ID作为tag，便于查找
            )
    
    def get_selected_station(self) -> Optional[Station]:
        """
        获取选中的工序
        
        Returns:
            Optional[Station]: 选中的工序对象，如果没有选中返回None
        """
        return self.selected_station

    def select_station(self, station_id: str) -> None:
        """按 ID 选中工序列表中的一行（供画布单击联动）"""
        for item in self.tree.get_children():
            tags = self.tree.item(item, 'tags')
            if tags and tags[0] == station_id:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)
                break
    
    def _btn_add(self) -> None:
        """添加按钮点击"""
        if self.on_add:
            self.on_add()
    
    def _btn_edit(self) -> None:
        """编辑按钮点击"""
        if self.on_edit:
            self.on_edit()
    
    def _btn_delete(self) -> None:
        """删除按钮点击"""
        if self.on_delete:
            self.on_delete()

    def set_editable(self, enabled: bool) -> None:
        """切换工序编辑能力（仿真运行中禁用）"""
        state = tk.NORMAL if enabled else tk.DISABLED
        for btn in (self.btn_add, self.btn_edit, self.btn_delete):
            btn.config(state=state)

    def _open_glossary(self) -> None:
        """打开术语说明对话框"""
        GlossaryDialog(self.winfo_toplevel())

    def set_production_type(self, production_type: ProductionType) -> None:
        """更新生产类型标签"""
        label_map = {
            ProductionType.ASSEMBLY: "类型：烟弹组装",
            ProductionType.LIQUID_FILLING: "类型：烟油灌装",
            ProductionType.POUCH_PACKAGING: "类型：尼古丁袋包装",
        }
        if hasattr(self, 'production_type_label'):
            self.production_type_label.config(
                text=label_map.get(production_type, "类型：烟弹组装")
            )

    def set_unit(self, unit: str) -> None:
        """按生产类型更新工序列表产能单位"""
        if hasattr(self, 'tree'):
            self.tree.heading('capacity', text=f'产能({unit}/h)')
    
    def _on_select(self, event: tk.Event) -> None:
        """工序选择事件"""
        selection = self.tree.selection()
        if not selection:
            self.selected_station = None
            return
        
        # 获取选中的行
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if tags and len(tags) > 0:
            station_id = tags[0]
            
            # 从产线对象中查找Station对象
            if self.production_line:
                station = self.production_line.get_station(station_id)
                if station:
                    self.selected_station = station
                    
                    # 触发选择回调
                    if self.on_select:
                        self.on_select(station)
                else:
                    self.selected_station = None
            else:
                self.selected_station = None


class KPIDashboard(ttk.LabelFrame):
    """
    KPI仪表盘 - 显示关键绩效指标
    
    显示的KPI：
    - 瓶颈产能：产线最大产能
    - 日产量：预计日产量
    - 总成本：日人力成本
    - 单颗成本：单颗物料成本
    - 产线平衡率：产线平衡程度
    
    使用方式：
        dashboard = KPIDashboard(parent)
        dashboard.update_kpis({'bottleneck_capacity': 850, ...})
    """
    
    def __init__(self, parent):
        """初始化KPI仪表盘"""
        super().__init__(parent, text="KPI仪表盘", padding=10)
        
        # KPI标签
        self.kpi_labels: Dict[str, ttk.Label] = {}
        self.kpi_name_labels: Dict[str, tk.Label] = {}
        self.kpi_unit_labels: Dict[str, tk.Label] = {}
        self.kpi_cells: Dict[str, tk.Frame] = {}
        
        # 创建界面
        self._create_widgets()
    
    def _create_widgets(self) -> None:
        """创建界面组件"""
        # 时间戳显示（第一行，单独显示）
        timestamp_frame = ttk.Frame(self)
        timestamp_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(timestamp_frame, text="仿真时间:", font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        self.timestamp_label = ttk.Label(
            timestamp_frame,
            text="0.0 分钟",
            font=('Arial', 12, 'bold'),
            foreground='green'
        )
        self.timestamp_label.pack(side=tk.LEFT, padx=5)

        # 运行状态徽标
        self.run_state_label = ttk.Label(
            timestamp_frame,
            text="● 已停止",
            font=('Arial', 10, 'bold'),
            foreground='gray',
        )
        self.run_state_label.pack(side=tk.RIGHT, padx=5)
        
        # 分隔线
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=10)
        
        # 使用Grid布局，6列显示6个KPI（卡片化）
        kpis = [
            ('bottleneck_capacity', '瓶颈产能', '颗/h'),
            ('daily_output', '预计日产量', '颗'),
            ('total_cost', '日成本', '元'),
            ('unit_cost', '单颗成本', '元/颗'),
            ('balance_rate', '产线平衡率', '%'),
            ('upph', 'UPPH', '颗/人·h')
        ]

        kpi_frame = ttk.Frame(self)
        kpi_frame.pack(fill=tk.BOTH, expand=True)

        family = resolve_font_family()
        for i, (key, label, unit) in enumerate(kpis):
            # 卡片容器
            cell = tk.Frame(
                kpi_frame,
                bg=COLORS['surface'],
                highlightbackground=COLORS['border'],
                highlightthickness=1,
                padx=10,
                pady=8,
            )
            cell.grid(row=0, column=i, sticky='nsew', padx=6, pady=4)
            kpi_frame.grid_columnconfigure(i, weight=1)
            self.kpi_cells[key] = cell

            # KPI 名称
            name_label = tk.Label(
                cell,
                text=label,
                bg=COLORS['surface'],
                fg=COLORS['text_secondary'],
                font=(family, 9),
            )
            name_label.pack()
            self.kpi_name_labels[key] = name_label

            # KPI 数值
            value_label = tk.Label(
                cell,
                text="--",
                bg=COLORS['surface'],
                fg=COLORS['text'],
                font=(family, 15, 'bold'),
            )
            value_label.pack()
            if key == 'total_cost':
                ToolTip(value_label, "日成本 = 总人数 × 时薪 × 班次时长（元/天）")

            # 单位
            unit_label = tk.Label(
                cell,
                text=unit,
                bg=COLORS['surface'],
                fg=COLORS['text_secondary'],
                font=(family, 8),
            )
            unit_label.pack()
            self.kpi_unit_labels[key] = unit_label

            self.kpi_labels[key] = value_label

        # V1.3 扩展 KPI 摘要行
        self.v13_label = ttk.Label(
            self,
            text="",
            font=(family, 9),
            foreground=COLORS['text_secondary'],
        )
        self.v13_label.pack(fill=tk.X, pady=(4, 0))
    
    def update_timestamp(self, minutes: float) -> None:
        """
        更新时间戳显示
        
        Args:
            minutes: 仿真时间（分钟）
        """
        if hasattr(self, 'timestamp_label'):
            self.timestamp_label.config(text=f"{minutes:.1f} 分钟")
    
    def reset_timestamp(self) -> None:
        """重置时间戳为0"""
        if hasattr(self, 'timestamp_label'):
            self.timestamp_label.config(text="0.0 分钟")

    def set_run_state(self, state: str) -> None:
        """
        更新运行状态徽标

        Args:
            state: running / paused / stopped
        """
        if not hasattr(self, 'run_state_label'):
            return
        state_map = {
            'running': ('● 运行中', '#34C759'),
            'paused': ('⏸ 已暂停', '#FF9F0A'),
            'stopped': ('■ 已停止', '#6B7280'),
        }
        text, color = state_map.get(state, state_map['stopped'])
        self.run_state_label.config(text=text, foreground=color)
    
    def update_kpis(self, kpis: Dict[str, float]) -> None:
        """
        更新KPI显示
        
        Args:
            kpis: KPI字典，包含所有KPI值
        """
        # 更新瓶颈产能
        if 'bottleneck_capacity' in kpis:
            value = kpis['bottleneck_capacity']
            self.kpi_labels['bottleneck_capacity'].config(text=f"{value:.0f}")
        
        # 更新日产量
        if 'daily_output' in kpis:
            value = kpis['daily_output']
            self.kpi_labels['daily_output'].config(text=f"{value:.0f}")
        
        # 更新总成本
        if 'total_cost' in kpis:
            value = kpis['total_cost']
            self.kpi_labels['total_cost'].config(text=f"{value:.0f}")
        
        # 更新单颗成本
        if 'unit_cost' in kpis:
            value = kpis['unit_cost']
            self.kpi_labels['unit_cost'].config(text=f"{value:.2f}")
        
        # 更新平衡率
        if 'balance_rate' in kpis:
            value = kpis['balance_rate']
            self.kpi_labels['balance_rate'].config(text=f"{value*100:.1f}")
        
        # 更新UPPH
        if 'upph' in kpis:
            value = kpis['upph']
            self.kpi_labels['upph'].config(text=f"{value:.1f}")

    def update_v13_kpis(self, kpis: Dict[str, float]) -> None:
        """更新 V1.3 扩展 KPI 摘要（批次/收率/机台 OEE/单位成本）"""
        if not hasattr(self, 'v13_label'):
            return
        parts = []
        for key, label, fmt in [
            ('batch_cycle_min', '批次周期', '{:.1f} min'),
            ('batch_pass_rate', '批次合格率', '{:.1%}'),
            ('yield_rate', '收率', '{:.1%}'),
            ('machine_oee', '机台OEE', '{:.1%}'),
            ('cost_per_liter', '元/升', '{:.2f}'),
            ('cost_per_pouch', '元/袋', '{:.2f}'),
        ]:
            if key in kpis and kpis[key]:
                parts.append(f"{label}: {fmt.format(kpis[key])}")
        self.v13_label.config(text="  |  ".join(parts))

    def set_unit(self, unit: str) -> None:
        """按生产类型更新 KPI 计量单位（颗/升/袋）"""
        if not hasattr(self, 'kpi_name_labels'):
            return
        label_map = {
            'bottleneck_capacity': ('瓶颈产能', f'{unit}/h'),
            'daily_output': ('预计日产量', unit),
            'total_cost': ('日成本', '元'),
            'unit_cost': ('单位成本', f'元/{unit}'),
            'balance_rate': ('产线平衡率', '%'),
            'upph': ('UPPH', f'{unit}/人·h'),
        }
        for key, (name, unit_text) in label_map.items():
            if key in self.kpi_name_labels:
                self.kpi_name_labels[key].config(text=name)
            if key in self.kpi_unit_labels:
                self.kpi_unit_labels[key].config(text=unit_text)

    def recolor(self, palette: dict) -> None:
        """按主题色板重绘 KPI 卡片（V3.0）"""
        for key, cell in self.kpi_cells.items():
            cell.config(bg=palette['surface'], highlightbackground=palette['border'])
            if key in self.kpi_name_labels:
                self.kpi_name_labels[key].config(bg=palette['surface'], fg=palette['text_secondary'])
            if key in self.kpi_labels:
                self.kpi_labels[key].config(bg=palette['surface'], fg=palette['text'])
            if key in self.kpi_unit_labels:
                self.kpi_unit_labels[key].config(bg=palette['surface'], fg=palette['text_secondary'])
        if hasattr(self, 'v13_label'):
            self.v13_label.config(foreground=palette['text_secondary'])


class AlertPanel(ttk.LabelFrame):
    """
    报警面板 - 显示各种报警信息
    
    报警类型：
    - 瓶颈警报：产线瓶颈工序
    - 浪费警报：产能过剩的工序
    - 堵塞警报：WIP堆积过多
    
    使用方式：
        panel = AlertPanel(parent)
        panel.add_alert(alert)
    """
    
    def __init__(self, parent):
        """初始化报警面板"""
        super().__init__(parent, text="报警信息", padding=10)
        self._alerts: List[Alert] = []
        self._collapsed = False

        # 头部：筛选 / 清空 / 折叠 / 复制
        header = ttk.Frame(self)
        header.pack(fill=tk.X)
        self.filter_var = tk.StringVar(value="全部")
        self.filter_combo = ttk.Combobox(
            header,
            textvariable=self.filter_var,
            values=["全部", "严重", "警告", "信息"],
            width=6,
            state="readonly",
        )
        self.filter_combo.pack(side=tk.LEFT, padx=2)
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_filter())
        self.btn_clear = ttk.Button(header, text="清空", width=6, command=self._clear)
        self.btn_clear.pack(side=tk.LEFT, padx=2)
        self.btn_collapse = ttk.Button(
            header, text="折叠", width=6, command=self._toggle_collapse
        )
        self.btn_collapse.pack(side=tk.LEFT, padx=2)
        self.btn_copy_alerts = ttk.Button(
            header,
            text="📋 复制",
            width=8,
            command=self._copy_alerts,
        )
        self.btn_copy_alerts.pack(side=tk.RIGHT)

        # 报警列表（使用Text组件显示）
        self.text_widget = tk.Text(self, height=10, width=28, wrap=tk.WORD)
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        # 配置文本样式
        self.text_widget.config(state=tk.DISABLED)  # 只读
    
    def add_alert(self, alert: Alert) -> None:
        """
        添加报警信息
        
        Args:
            alert: 报警对象
        """
        self._alerts.append(alert)
        self._render()

    def _render(self) -> None:
        """按筛选条件渲染报警列表（V3.0）"""
        # 启用编辑
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete("1.0", tk.END)

        severity_map = {"全部": "all", "严重": "critical", "警告": "warning", "信息": "info"}
        target = severity_map.get(self.filter_var.get(), "all")

        for alert in self._alerts:
            if target != "all" and alert.severity != target:
                continue
            color = get_alert_color(alert.severity)
            time_str = f"{alert.timestamp_minutes:.1f}分钟"
            icon = ALERT_ICONS.get(alert.severity, '•')
            text = f"[{time_str}] {icon} [{alert.severity.upper()}] {alert.message}\n"
            if alert.suggestion:
                text += f"  建议：{alert.suggestion}\n"
            text += "\n"

            start_pos = self.text_widget.index(tk.END)
            self.text_widget.insert(tk.END, text)
            end_pos = self.text_widget.index(tk.END)
            self.text_widget.tag_add(alert.severity, start_pos, end_pos)
            self.text_widget.tag_config(alert.severity, foreground=color)

        self.text_widget.see(tk.END)
        # 禁用编辑
        self.text_widget.config(state=tk.DISABLED)

    def clear(self) -> None:
        """清空报警信息"""
        self._alerts = []
        self._render()

    def _apply_filter(self) -> None:
        """应用报警级别筛选"""
        self._render()

    def _clear(self) -> None:
        """清空按钮"""
        self._alerts = []
        self._render()

    def _toggle_collapse(self) -> None:
        """折叠/展开报警列表"""
        self._collapsed = not self._collapsed
        if self._collapsed:
            self.text_widget.pack_forget()
            self.btn_collapse.config(text="展开")
        else:
            self.text_widget.pack(fill=tk.BOTH, expand=True)
            self.btn_collapse.config(text="折叠")

    def _copy_alerts(self) -> None:
        """一键复制全部报警文本到剪贴板"""
        content = self.text_widget.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("提示", "当前没有报警信息")
            return
        top = self.winfo_toplevel()
        top.clipboard_clear()
        top.clipboard_append(content)
        self.btn_copy_alerts.config(text="✅ 已复制")
        self.after(1200, lambda: self.btn_copy_alerts.config(text="📋 复制报警"))

    def recolor(self) -> None:
        """按当前主题刷新报警级别颜色（V3.0）"""
        for severity in ('critical', 'warning', 'info'):
            try:
                self.text_widget.tag_config(severity, foreground=get_alert_color(severity))
            except Exception:
                pass


class StationDialog:
    """
    工序编辑对话框 - 用于添加或编辑工序
    
    这是一个模态对话框，用户输入工序参数后点击确定
    
    使用方式：
        dialog = StationDialog(parent, title="添加工序")
        if dialog.result:
            station = dialog.result  # 获取创建的工序对象
    """
    
    def __init__(self, parent, title: str = "编辑工序", station: Optional[Station] = None, production_line: Optional[Any] = None):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            title: 对话框标题
            station: 要编辑的工序对象（如果为None则是添加模式）
            production_line: 产线对象（用于生成新ID）
        """
        self.result: Optional[Station] = None  # 对话框结果
        self.production_line = production_line  # 保存产线引用
        self.station = station  # 保存原始station引用（如果是编辑模式）
        self.line_type = (
            production_line.production_type
            if production_line is not None
            else ProductionType.ASSEMBLY
        )
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("460x500")
        self.dialog.transient(parent)  # 设置为父窗口的子窗口
        self.dialog.grab_set()  # 模态对话框
        
        # 创建输入字段
        self._create_widgets(station)
        # V3.0 键盘可达：Esc 取消，Enter 确定
        self.dialog.bind('<Escape>', lambda e: self._btn_cancel())
        self.dialog.bind('<Return>', lambda e: self._btn_ok())
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def _create_widgets(self, station: Optional[Station]) -> None:
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 工序名称
        ttk.Label(main_frame, text="工序名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar(value=station.name if station else "")
        name_entry = ttk.Entry(main_frame, textvariable=self.name_var, width=30)
        name_entry.grid(row=0, column=1, pady=5)
        
        # 单颗耗时
        ttk.Label(main_frame, text="单件耗时(秒):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.time_var = tk.StringVar(value=str(station.process_time) if station else "30")
        time_entry = ttk.Entry(main_frame, textvariable=self.time_var, width=30)
        time_entry.grid(row=1, column=1, pady=5)
        
        # 工人数量
        ttk.Label(main_frame, text="工人数量:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.workers_var = tk.StringVar(value=str(station.worker_count) if station else "1")
        workers_entry = ttk.Entry(main_frame, textvariable=self.workers_var, width=30)
        workers_entry.grid(row=2, column=1, pady=5)
        
        # 协作模式
        ttk.Label(main_frame, text="协作模式:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.mode_var = tk.StringVar(value=station.collaboration_type.value if station else "parallel")
        mode_frame = ttk.Frame(main_frame)
        mode_frame.grid(row=3, column=1, pady=5, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="并联", variable=self.mode_var, value="parallel").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="协同", variable=self.mode_var, value="collaborative").pack(side=tk.LEFT, padx=5)
        
        # OEE
        ttk.Label(main_frame, text="OEE (0-1):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.oee_var = tk.StringVar(value=str(station.oee) if station else "0.85")
        oee_entry = ttk.Entry(main_frame, textvariable=self.oee_var, width=30)
        oee_entry.grid(row=4, column=1, pady=5)

        # V1.3：生产类型相关字段
        self.machine_takt_var = tk.StringVar(
            value=str(station.machine_takt) if station and station.machine_takt else ""
        )
        self.clean_time_var = tk.StringVar(
            value=str(station.clean_time_minutes) if station else "0"
        )
        self.sampling_var = tk.StringVar(
            value=str(station.sampling_rate) if station else "0"
        )
        self.defect_var = tk.StringVar(
            value=str(station.defect_rate) if station else "0"
        )
        self.rework_var = tk.StringVar(
            value=str(station.rework_minutes) if station else "0"
        )

        self.machine_takt_label = ttk.Label(main_frame, text="机台节拍(秒):")
        self.machine_takt_label.grid(row=5, column=0, sticky=tk.W, pady=5)
        self.machine_takt_entry = ttk.Entry(
            main_frame, textvariable=self.machine_takt_var, width=30
        )
        self.machine_takt_entry.grid(row=5, column=1, pady=5)

        self.clean_time_label = ttk.Label(main_frame, text="清洗时间(分钟):")
        self.clean_time_label.grid(row=6, column=0, sticky=tk.W, pady=5)
        self.clean_time_entry = ttk.Entry(
            main_frame, textvariable=self.clean_time_var, width=30
        )
        self.clean_time_entry.grid(row=6, column=1, pady=5)

        self.sampling_label = ttk.Label(main_frame, text="抽检比例(0-1):")
        self.sampling_label.grid(row=7, column=0, sticky=tk.W, pady=5)
        self.sampling_entry = ttk.Entry(
            main_frame, textvariable=self.sampling_var, width=30
        )
        self.sampling_entry.grid(row=7, column=1, pady=5)

        self.defect_label = ttk.Label(main_frame, text="缺陷率(0-1):")
        self.defect_label.grid(row=8, column=0, sticky=tk.W, pady=5)
        self.defect_entry = ttk.Entry(
            main_frame, textvariable=self.defect_var, width=30
        )
        self.defect_entry.grid(row=8, column=1, pady=5)

        self.rework_label = ttk.Label(main_frame, text="返工时长(分钟):")
        self.rework_label.grid(row=9, column=0, sticky=tk.W, pady=5)
        self.rework_entry = ttk.Entry(
            main_frame, textvariable=self.rework_var, width=30
        )
        self.rework_entry.grid(row=9, column=1, pady=5)

        self._apply_type_fields()
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=10, column=0, columnspan=2, pady=20)
        
        # 确定按钮
        btn_ok = ttk.Button(button_frame, text="确定", command=self._btn_ok, style="Primary.TButton")
        btn_ok.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        btn_cancel = ttk.Button(button_frame, text="取消", command=self._btn_cancel)
        btn_cancel.pack(side=tk.LEFT, padx=10)
        
        # 聚焦到名称输入框
        name_entry.focus()

    def _apply_type_fields(self) -> None:
        """
        按生产类型显示/隐藏 V1.3 字段（标签与输入框成对隐藏）

        映射见 station_edit_fields()。
        """
        visible = station_edit_fields(self.line_type)
        fields = {
            'machine_takt': (self.machine_takt_label, self.machine_takt_entry),
            'clean_time_minutes': (self.clean_time_label, self.clean_time_entry),
            'sampling_rate': (self.sampling_label, self.sampling_entry),
            'defect_rate': (self.defect_label, self.defect_entry),
            'rework_minutes': (self.rework_label, self.rework_entry),
        }
        for key, (label, entry) in fields.items():
            if key in visible:
                label.grid()
                entry.grid()
                entry.config(state=tk.NORMAL)
            else:
                label.grid_remove()
                entry.grid_remove()
    
    def _btn_ok(self) -> None:
        """确定按钮点击"""
        try:
            # 获取输入值
            name = self.name_var.get().strip()
            process_time = float(self.time_var.get())
            worker_count = int(self.workers_var.get())
            oee = float(self.oee_var.get())
            mode = CollaborationType(self.mode_var.get())

            # V1.3 可选字段
            machine_takt_text = self.machine_takt_var.get().strip()
            machine_takt = float(machine_takt_text) if machine_takt_text else None
            clean_time = float(self.clean_time_var.get() or 0)
            sampling = float(self.sampling_var.get() or 0)
            defect = float(self.defect_var.get() or 0)
            rework = float(self.rework_var.get() or 0)

            if machine_takt is not None and machine_takt <= 0:
                messagebox.showerror("错误", "机台节拍必须大于0")
                return
            if not 0 <= sampling <= 1 or not 0 <= defect <= 1:
                messagebox.showerror("错误", "抽检比例与缺陷率必须在0-1之间")
                return
            
            # 校验参数
            valid, error = validate_station(name, process_time, worker_count)
            if not valid:
                messagebox.showerror("错误", error)
                return
            
            # 校验OEE
            if not 0 < oee <= 1:
                messagebox.showerror("错误", "OEE必须在0-1之间")
                return
            
            # 已经导入了Station类，直接使用即可
            
            # 生成工序ID（如果是添加模式）
            if self.station is None:  # 添加模式
                if self.production_line and self.production_line.stations:
                    # 基于现有工序数量生成ID
                    max_id = max([int(s.id.replace('s', '')) for s in self.production_line.stations if s.id.startswith('s') and s.id[1:].isdigit()], default=0)
                    station_id = f"s{max_id + 1:02d}"
                else:
                    station_id = "s01"
            else:  # 编辑模式，使用原有ID
                station_id = self.station.id
            
            self.result = Station(
                id=station_id,
                name=name,
                process_time=process_time,
                worker_count=worker_count,
                collaboration_type=mode,
                oee=oee,
                machine_takt=machine_takt,
                clean_time_minutes=clean_time,
                sampling_rate=sampling,
                defect_rate=defect,
                rework_minutes=rework,
            )
            
            # 关闭对话框
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("错误", f"输入格式错误：{e}")
        except Exception as e:
            messagebox.showerror("错误", f"创建工序失败：{e}")
    
    def _btn_cancel(self) -> None:
        """取消按钮点击"""
        self.dialog.destroy()


class ShiftConfigDialog:
    """
    班次配置对话框 - 用于配置班次时间和工时成本
    
    使用方式：
        dialog = ShiftConfigDialog(parent, shift_hours=8, break_minutes=60, worker_hourly_wage=20.0)
        if dialog.result:
            config = dialog.result  # 获取配置字典
    """
    
    def __init__(
        self,
        parent,
        shift_hours: int = 8,
        break_minutes: int = 60,
        worker_hourly_wage: float = 20.0
    ):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            shift_hours: 班次时长（小时）
            break_minutes: 休息时间（分钟）
            worker_hourly_wage: 工人时薪（元/小时）
        """
        self.result: Optional[Dict[str, Any]] = None  # 对话框结果
        
        # 创建对话框窗口（更小巧）
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("班次配置")
        self.dialog.geometry("360x230")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建输入字段
        self._create_widgets(shift_hours, break_minutes, worker_hourly_wage)
        # V3.0 键盘可达：Esc 取消，Enter 确定
        self.dialog.bind('<Escape>', lambda e: self._btn_cancel())
        self.dialog.bind('<Return>', lambda e: self._btn_ok())
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def _create_widgets(self, shift_hours: int, break_minutes: int, worker_hourly_wage: float) -> None:
        """创建界面组件"""
        # 主框架（减小padding）
        main_frame = ttk.Frame(self.dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 班次时长（缩短输入框，width改为10）
        ttk.Label(main_frame, text="班次时长(小时):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.shift_hours_var = tk.StringVar(value=str(shift_hours))
        shift_entry = ttk.Entry(main_frame, textvariable=self.shift_hours_var, width=10)
        shift_entry.grid(row=0, column=1, pady=5, padx=5, sticky=tk.W)
        
        # 休息时间
        ttk.Label(main_frame, text="休息时间(分钟):").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.break_minutes_var = tk.StringVar(value=str(break_minutes))
        break_entry = ttk.Entry(main_frame, textvariable=self.break_minutes_var, width=10)
        break_entry.grid(row=1, column=1, pady=5, padx=5, sticky=tk.W)
        
        # 工人时薪
        ttk.Label(main_frame, text="工人时薪(元/小时):").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.wage_var = tk.StringVar(value=str(worker_hourly_wage))
        wage_entry = ttk.Entry(main_frame, textvariable=self.wage_var, width=10)
        wage_entry.grid(row=2, column=1, pady=5, padx=5, sticky=tk.W)
        
        # 按钮框架（减小pady）
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        # 确定按钮
        btn_ok = ttk.Button(button_frame, text="确定", command=self._btn_ok, style="Primary.TButton")
        btn_ok.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        btn_cancel = ttk.Button(button_frame, text="取消", command=self._btn_cancel)
        btn_cancel.pack(side=tk.LEFT, padx=5)
        
        # 聚焦到第一个输入框
        shift_entry.focus()

        # 日成本计算说明
        family = resolve_font_family()
        ttk.Label(
            main_frame,
            text="日成本 = 总人数 × 时薪 × 班次时长（不含休息扣减）",
            foreground=COLORS['text_secondary'],
            font=(family, 9),
        ).grid(row=4, column=0, columnspan=2, pady=(0, 5))
    
    def _btn_ok(self) -> None:
        """确定按钮点击"""
        try:
            # 获取输入值
            shift_hours = int(self.shift_hours_var.get())
            break_minutes = int(self.break_minutes_var.get())
            worker_hourly_wage = float(self.wage_var.get())
            
            # 校验参数
            if shift_hours <= 0 or shift_hours > 24:
                messagebox.showerror("错误", "班次时长必须在1-24小时之间")
                return
            
            if break_minutes < 0 or break_minutes >= shift_hours * 60:
                messagebox.showerror("错误", "休息时间不能超过班次时长")
                return
            
            if worker_hourly_wage <= 0:
                messagebox.showerror("错误", "工人时薪必须大于0")
                return
            
            # 保存结果
            self.result = {
                'shift_hours': shift_hours,
                'break_minutes': break_minutes,
                'worker_hourly_wage': worker_hourly_wage
            }
            
            # 关闭对话框
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("错误", f"输入格式错误：{e}")
        except Exception as e:
            messagebox.showerror("错误", f"配置失败：{e}")

    def _btn_cancel(self) -> None:
        """取消按钮点击：不保存，直接关闭对话框"""
        self.result = None
        self.dialog.destroy()


class SaveScenarioDialog:
    """
    保存方案对话框 - 用于保存当前产线配置为方案
    
    功能：
    - 输入方案名称（必填）
    - 输入方案描述（可选）
    - 验证名称是否重复
    - 检查方案数量限制（最多3个）
    
    使用方式：
        dialog = SaveScenarioDialog(parent, scenario_manager, production_line)
        if dialog.result:
            # 方案已保存
    """
    
    def __init__(self, parent, scenario_manager: ScenarioManager, production_line: ProductionLine):
        """
        初始化保存方案对话框
        
        Args:
            parent: 父窗口
            scenario_manager: 方案管理器
            production_line: 要保存的产线对象
        """
        self.scenario_manager = scenario_manager
        self.production_line = production_line
        self.result = None  # 保存结果：{'name': str, 'description': str} 或 None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("保存方案")
        self.dialog.resizable(False, False)
        
        # 设置对话框为模态（阻塞父窗口）
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面（先创建界面，再计算位置）
        self._create_widgets()
        
        # 绑定回车键
        self.dialog.bind('<Return>', lambda e: self._on_confirm())
        # V3.0 键盘可达：Esc 取消
        self.dialog.bind('<Escape>', lambda e: self._on_cancel())
        
        # 居中显示（相对于父窗口，而不是屏幕）
        # 必须在创建完所有widgets后调用update_idletasks()
        self.dialog.update_idletasks()
        
        # 获取父窗口位置和大小
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 获取对话框大小
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 计算居中位置（相对于父窗口）
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 确保对话框不会超出屏幕
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        # 设置对话框位置
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def _create_widgets(self) -> None:
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 方案名称输入
        ttk.Label(main_frame, text="方案名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=30)
        self.name_entry.grid(row=0, column=1, pady=5, padx=10)
        self.name_entry.focus()
        
        # 方案描述输入
        ttk.Label(main_frame, text="方案描述:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.description_text = tk.Text(main_frame, width=30, height=4)
        self.description_text.grid(row=1, column=1, pady=5, padx=10)

        # 自定义保存路径（可选）
        ttk.Label(main_frame, text="保存位置(可选):").grid(row=2, column=0, sticky=tk.W, pady=5)
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=2, column=1, pady=5, padx=10, sticky=tk.W)
        self.path_var = tk.StringVar(value="")
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=22)
        self.path_entry.pack(side=tk.LEFT)
        ttk.Button(path_frame, text="浏览...", command=self._browse_path).pack(side=tk.LEFT, padx=5)
        
        # 提示信息
        info_label = ttk.Label(
            main_frame,
            text=f"当前已保存 {self.scenario_manager.get_scenario_count()}/{self.scenario_manager.MAX_SCENARIOS} 个方案",
            font=('Arial', 9),
            foreground='gray'
        )
        info_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(
            button_frame, text="确定", command=self._on_confirm, style="Primary.TButton"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self._on_cancel).pack(side=tk.LEFT, padx=5)

    def _browse_path(self) -> None:
        """选择自定义保存路径（JSON）"""
        path = filedialog.asksaveasfilename(
            title="选择方案保存位置",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if path:
            self.path_var.set(path)
    
    def _on_confirm(self) -> None:
        """确认保存方案"""
        # 获取输入
        name = self.name_entry.get().strip()
        description = self.description_text.get("1.0", tk.END).strip()
        
        # 验证方案名称
        if not name:
            messagebox.showwarning("警告", "方案名称不能为空")
            return
        
        # 尝试保存方案
        success, error_msg = self.scenario_manager.save_scenario(
            name, self.production_line, description
        )
        
        if success:
            # 保存成功
            export_path = self.path_var.get().strip()
            if export_path:
                if not self.scenario_manager.export_scenario(name, export_path):
                    messagebox.showwarning("警告", "方案已保存到内部，但导出到自定义路径失败")
            self.result = {
                'name': name,
                'description': description,
                'path': export_path or None,
            }
            self.dialog.destroy()
        else:
            # 保存失败，显示错误信息
            messagebox.showerror("错误", error_msg or "保存方案失败")
    
    def _on_cancel(self) -> None:
        """取消保存"""
        self.result = None
        self.dialog.destroy()


class ScenarioCompareDialog:
    """
    方案对比对话框 - 显示多个方案的KPI对比
    
    功能：
    - 显示所有方案的KPI对比表格
    - 计算并显示差异（相对于第一个方案）
    - 推荐最佳方案（单颗成本最低）
    
    使用方式：
        dialog = ScenarioCompareDialog(parent, scenario_manager, scenario_names)
        # 对话框会自动显示对比结果
    """
    
    def __init__(self, parent, scenario_manager: ScenarioManager, scenario_names: List[str]):
        """
        初始化方案对比对话框
        
        Args:
            parent: 父窗口
            scenario_manager: 方案管理器
            scenario_names: 要对比的方案名称列表（至少2个）
        """
        self.scenario_manager = scenario_manager
        self.scenario_names = scenario_names
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("方案对比")
        self.dialog.geometry("900x600")
        self.dialog.resizable(True, True)
        
        # 设置对话框为模态
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 获取对比数据
        try:
            self.comparison_data = scenario_manager.compare_scenarios(scenario_names)
        except Exception as e:
            messagebox.showerror("错误", f"对比方案失败：{str(e)}")
            self.dialog.destroy()
            return

        first = self.scenario_manager.get_scenario(scenario_names[0])
        self.unit = first.production_line.get_unit() if first else "颗"
        
        # 创建界面（先创建界面，再计算位置）
        self._create_widgets()
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        
        # 居中显示（相对于父窗口）
        self.dialog.update_idletasks()
        
        # 获取父窗口位置和大小
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # 获取对话框大小
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 计算居中位置（相对于父窗口）
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # 确保对话框不会超出屏幕
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        # 设置对话框位置
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _create_widgets(self) -> None:
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(
            main_frame,
            text="方案对比",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=10)
        
        # 创建表格框架
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建Treeview表格
        # 列：指标 + 每个方案 + 差异列（每个方案相对于第一个方案的差异）
        columns = ['指标'] + self.scenario_names
        # 为每个非基准方案添加差异列
        for i, name in enumerate(self.scenario_names[1:], 1):
            columns.append(f'差异{i}')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # 设置列宽
        self.tree.column('指标', width=120, anchor=tk.W)
        for name in self.scenario_names:
            self.tree.column(name, width=100, anchor=tk.CENTER)
        for i in range(1, len(self.scenario_names)):
            self.tree.column(f'差异{i}', width=120, anchor=tk.W)
        
        # 设置列标题
        self.tree.heading('指标', text='指标')
        for name in self.scenario_names:
            self.tree.heading(name, text=name)
        # 差异列标题
        for i, name in enumerate(self.scenario_names[1:], 1):
            self.tree.heading(f'差异{i}', text=f'{name} vs {self.scenario_names[0]}')
        
        # 添加滚动条
        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # 填充数据
        self._populate_table()
        
        # 推荐方案标签
        if self.comparison_data.get('recommendation'):
            recommendation_label = ttk.Label(
                main_frame,
                text=f"💡 推荐方案：{self.comparison_data['recommendation']}",
                font=('Arial', 10, 'bold'),
                foreground='green'
            )
            recommendation_label.pack(pady=10)
        
        # 关闭按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="关闭", command=self.dialog.destroy).pack()
    
    def _populate_table(self) -> None:
        """填充对比表格数据"""
        # KPI指标配置（指标键名, 显示名称, 单位, 格式化函数）
        unit = self.unit
        kpi_configs = [
            ('total_workers', '总人数', '人', lambda x: f"{int(x)}人"),
            ('bottleneck_capacity', '瓶颈产能', f'{unit}/h', lambda x: f"{x:.0f}"),
            ('daily_output', '日产量', unit, lambda x: f"{x:.0f}"),
            ('total_cost', '日成本', '元', lambda x: f"{x:.0f}"),
            ('unit_cost', '单位成本', f'元/{unit}', lambda x: f"{x:.2f}"),
            ('balance_rate', '产线平衡率', '%', lambda x: f"{x*100:.1f}%"),
            ('upph', 'UPPH', f'{unit}/人·h', lambda x: f"{x:.1f}")
        ]

        self.tree.tag_configure('even', background=COLORS['surface'])
        self.tree.tag_configure('odd', background=COLORS['bg'])
        
        # 遍历每个KPI指标
        for row_index, (metric_key, metric_name, unit, format_func) in enumerate(kpi_configs):
            # 查找对应的差异数据
            diff_data = next(
                (d for d in self.comparison_data['differences'] if d['metric_key'] == metric_key),
                None
            )
            
            if diff_data:
                # 构建行数据
                row_values = [f"{metric_name} ({unit})"]
                
                # 添加每个方案的值
                for scenario_data in self.comparison_data['scenarios']:
                    value = scenario_data['kpis'][metric_key]
                    row_values.append(format_func(value))
                
                # 添加差异列（每个非基准方案相对于第一个方案的差异）
                for i, diff_value in enumerate(diff_data['values'][1:], 1):
                    diff_abs = diff_value['diff_absolute']
                    diff_pct = diff_value['diff_percent']
                    
                    # 格式化差异文本
                    if abs(diff_abs) < 0.01:
                        diff_text = "无变化"
                    else:
                        sign = "+" if diff_abs > 0 else ""
                        diff_text = f"{sign}{format_func(diff_abs)} ({sign}{diff_pct:.1f}%)"
                    
                    row_values.append(diff_text)
                
                # 插入行
                self.tree.insert(
                    '', tk.END,
                    values=row_values,
                    tags=('even' if row_index % 2 == 0 else 'odd'),
                )
                
                # 根据差异设置颜色（改善=绿色，恶化=红色）
                # 注意：Treeview的颜色设置需要特殊处理，这里先不设置


class ScenarioManageDialog:
    """
    方案管理对话框 - 查看与删除已保存的方案

    使用方式：
        dialog = ScenarioManageDialog(parent, scenario_manager)
        # 删除操作会自动持久化到 ScenarioManager 的存储路径
    """

    def __init__(self, parent, scenario_manager: ScenarioManager):
        self.scenario_manager = scenario_manager

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("方案管理")
        self.dialog.geometry("720x420")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._create_widgets()
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _create_widgets(self) -> None:
        """创建界面组件"""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('name', 'created_at', 'description', 'unit_cost')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=14)
        self.tree.heading('name', text='方案名称')
        self.tree.heading('created_at', text='创建时间')
        self.tree.heading('description', text='描述')
        self.tree.heading('unit_cost', text='单位成本')
        self.tree.column('name', width=140)
        self.tree.column('created_at', width=150)
        self.tree.column('description', width=260)
        self.tree.column('unit_cost', width=110)
        self.tree.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="删除选中", command=self._delete_selected).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT)

        self._refresh()

    def _refresh(self) -> None:
        """刷新方案列表"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree.tag_configure('even', background=COLORS['surface'])
        self.tree.tag_configure('odd', background=COLORS['bg'])
        for idx, name in enumerate(self.scenario_manager.list_scenarios()):
            scenario = self.scenario_manager.get_scenario(name)
            kpis = scenario.get_kpis()
            self.tree.insert('', tk.END, values=(
                name,
                scenario.created_at,
                scenario.description,
                f"{kpis['unit_cost']:.3f}",
            ), tags=(name, 'even' if idx % 2 == 0 else 'odd'))

    def _delete_selected(self) -> None:
        """删除选中的方案"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个方案")
            return
        item = selection[0]
        tags = self.tree.item(item, 'tags')
        if not tags:
            return
        name = tags[0]
        if messagebox.askyesno("确认", f"确定删除方案 '{name}' 吗？"):
            ok, err = self.scenario_manager.delete_scenario(name)
            if ok:
                self._refresh()
            else:
                messagebox.showerror("错误", err or "删除失败")


class GlossaryDialog:
    """
    术语说明对话框 - 展示供应链关键术语与意义梗概

    使用方式：
        GlossaryDialog(parent)
    """

    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("术语说明")
        self.dialog.geometry("600x520")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text="供应链关键术语速查",
            font=('Arial', 13, 'bold'),
        ).pack(anchor=tk.W, pady=(0, 8))

        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ('term', 'meaning')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=18)
        self.tree.heading('term', text='术语')
        self.tree.heading('meaning', text='意义梗概')
        self.tree.column('term', width=120, anchor=tk.W)
        self.tree.column('meaning', width=440, anchor=tk.W)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for term, meaning in GLOSSARY:
            self.tree.insert('', tk.END, values=(term, meaning))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT)

        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")


class CommandPalette:
    """
    命令面板（V3.0，Ctrl+K）

    通过关键词过滤命令，Enter 执行选中项，Esc 关闭。
    """

    def __init__(self, parent, commands: List[tuple]):
        self.commands = commands
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("命令面板")
        self.dialog.geometry("520x380")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        family = resolve_font_family()
        main = ttk.Frame(self.dialog, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            main,
            text="输入命令关键词（Enter 执行，Esc 关闭）",
            font=(family, 9),
            foreground=COLORS['text_secondary'],
        ).pack(anchor=tk.W)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._render())
        entry = ttk.Entry(main, textvariable=self.search_var, font=(family, 13))
        entry.pack(fill=tk.X, pady=5)

        self.tree = ttk.Treeview(main, columns=('label',), show='tree', height=12)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        self.dialog.bind('<Return>', lambda e: self._run_selected())

        self._render()
        entry.focus_set()

    def _render(self) -> None:
        """按关键词过滤命令列表"""
        self.tree.delete(*self.tree.get_children())
        query = self.search_var.get().strip().lower()
        for label, _ in self.commands:
            if not query or query in label.lower():
                self.tree.insert('', tk.END, text=label, values=(label,))

    def _run_selected(self) -> None:
        """执行选中的命令（无选中时执行第一条）"""
        selection = self.tree.selection()
        if not selection:
            children = self.tree.get_children()
            if not children:
                return
            selection = (children[0],)
        label = self.tree.item(selection[0], 'values')[0]
        for cmd_label, callback in self.commands:
            if cmd_label == label:
                self.dialog.destroy()
                callback()
                return


class AboutDialog:
    """
    关于对话框（V3.1）

    包含：版本/署名、隐私声明、免责声明、Bug 反馈与资助入口。
    """

    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("关于")
        self.dialog.geometry("600x660")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        family = resolve_font_family()
        main = ttk.Frame(self.dialog, padding=16)
        main.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(
            main,
            text=f"电子烟产线仿真优化工具 v{__version__}",
            font=(family, 15, 'bold'),
        )
        title.pack(anchor=tk.W, pady=(0, 4))

        ttk.Label(main, text="开发者：Max Hou", font=(family, 11)).pack(anchor=tk.W, pady=(0, 8))
        ttk.Label(
            main,
            text="基于 SimPy 的离散事件仿真引擎，用于产线设计与人力优化。",
            font=(family, 10),
            foreground=COLORS['text_secondary'],
        ).pack(anchor=tk.W, pady=(0, 10))

        text = tk.Text(main, height=10, wrap=tk.WORD, font=(family, 10))
        text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        text.insert('1.0', (
            "【隐私声明】\n"
            "本工具完全本地运行，不上传任何数据；产线配置、方案、UI 设置与日志均保存在您的设备上。\n\n"
            "【免责声明】\n"
            "仿真结果仅供产线设计与人力规划参考，不构成产能或成本承诺；实际投产前请以现场验证为准。"
            "作者不对因参考仿真结果做出的决策损失承担责任。本工具按“现状”提供。\n\n"
            "【Bug 反馈】\n"
            f"GitHub Issues：{BUG_REPORT_URL}\n\n"
            "【资助作者】\n"
            "扫描上方二维码即可支持作者一杯咖啡的钱，感谢你的资助！\n"
        ))
        text.config(state=tk.DISABLED)
        self.about_text = text

        # 内嵌微信赞赏码图片（如存在）
        self._qr_image = None
        display_path = (
            WECHAT_QR_SMALL_PATH
            if WECHAT_QR_SMALL_PATH and os.path.exists(WECHAT_QR_SMALL_PATH)
            else WECHAT_QR_PATH
        )
        if display_path and os.path.exists(display_path):
            try:
                self._qr_image = tk.PhotoImage(file=display_path)
                ttk.Label(main, image=self._qr_image).pack(pady=(0, 8))
            except Exception:
                self._qr_image = None

        button_frame = ttk.Frame(main)
        button_frame.pack(fill=tk.X)
        ttk.Button(button_frame, text="报告 Bug", command=self._open_bug).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="微信赞赏码", command=self._show_wechat).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=2)

        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

    def _open_bug(self) -> None:
        webbrowser.open(BUG_REPORT_URL)

    def _show_wechat(self) -> None:
        """打开微信赞赏码图片"""
        if not WECHAT_QR_PATH or not os.path.exists(WECHAT_QR_PATH):
            messagebox.showinfo(
                "微信赞赏码",
                "尚未配置赞赏码图片，请检查 assets/wechat_qr.png。",
            )
            return
        webbrowser.open("file://" + os.path.abspath(WECHAT_QR_PATH))

class WizardDialog:
    """
    快速配置向导 - 分步引导新手完成产线配置

    步骤：
    1. 选择模板（简单/标准/复杂/空白）
    2. 选择数据来源（模板 / Excel 导入）
    3. 设置班次
    4. 完成（可选立即开始仿真）

    使用方式：
        dialog = WizardDialog(parent)
        if dialog.result:
            line = dialog.result['production_line']
            auto_start = dialog.result['auto_start']
    """

    TEMPLATES = {
        "simple": [
            ("注油", 25.0, 2, "parallel"),
            ("焊接", 30.0, 3, "parallel"),
            ("包装", 15.0, 2, "parallel"),
        ],
        "standard": [
            ("注油", 25.0, 2, "parallel"),
            ("焊接", 30.0, 3, "parallel"),
            ("棉芯安装", 20.0, 2, "collaborative"),
            ("组装", 22.0, 2, "parallel"),
            ("包装", 15.0, 2, "parallel"),
        ],
        "complex": [
            ("镭雕", 25.0, 5, "parallel"),
            ("注油", 47.0, 1, "parallel"),
            ("预压合", 47.0, 1, "parallel"),
            ("底座压合", 48.0, 1, "parallel"),
            ("阻值&适配测试", 45.0, 1, "parallel"),
            ("异物检查", 232.0, 1, "parallel"),
            ("组装", 22.0, 2, "parallel"),
            ("包装", 15.0, 2, "parallel"),
        ],
    }

    def __init__(self, parent):
        """初始化向导对话框"""
        self.result = None
        self.parent = parent
        self.step_index = 0
        self.production_line: Optional[ProductionLine] = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("快速配置向导")
        self.dialog.geometry("680x480")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.template_var = tk.StringVar(value="standard")
        self.excel_path_var = tk.StringVar(value="")
        self.shift_hours_var = tk.StringVar(value="8")
        self.break_minutes_var = tk.StringVar(value="60")
        self.wage_var = tk.StringVar(value="20.0")
        self.auto_start_var = tk.BooleanVar(value=True)

        self._create_widgets()
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        self._show_step(0)

        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self.dialog.wait_window()

    def _create_widgets(self) -> None:
        """创建界面组件"""
        self.main_frame = ttk.Frame(self.dialog, padding=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 步骤提示
        self.step_label = ttk.Label(self.main_frame, font=('Arial', 12, 'bold'))
        self.step_label.pack(anchor=tk.W, pady=(0, 10))

        # 步骤内容容器
        self.step_container = ttk.Frame(self.main_frame)
        self.step_container.pack(fill=tk.BOTH, expand=True)

        # 创建四个步骤的页面
        self.page_template = ttk.Frame(self.step_container)
        self.page_source = ttk.Frame(self.step_container)
        self.page_shift = ttk.Frame(self.step_container)
        self.page_finish = ttk.Frame(self.step_container)

        self._build_page_template()
        self._build_page_source()
        self._build_page_shift()
        self._build_page_finish()

        # 底部按钮
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.btn_prev = ttk.Button(button_frame, text="上一步", command=self._prev)
        self.btn_prev.pack(side=tk.LEFT)
        self.btn_cancel = ttk.Button(button_frame, text="取消", command=self._cancel)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        self.btn_next = ttk.Button(button_frame, text="下一步", command=self._next)
        self.btn_next.pack(side=tk.RIGHT)

    def _build_page_template(self) -> None:
        """步骤 1：模板选择"""
        ttk.Label(self.page_template, text="选择生产类型：", font=('Arial', 10)).pack(
            anchor=tk.W, pady=(0, 5)
        )
        self.production_type_var = tk.StringVar(value="assembly")
        for key, label in [
            ("assembly", "烟弹组装（离散装配）"),
            ("liquid_filling", "烟油灌装（液体/批量）"),
            ("pouch_packaging", "尼古丁袋包装（高速机台）"),
        ]:
            ttk.Radiobutton(
                self.page_template,
                text=label,
                variable=self.production_type_var,
                value=key,
            ).pack(anchor=tk.W, pady=2)
        ttk.Separator(self.page_template, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        ttk.Label(self.page_template, text="选择产线模板：", font=('Arial', 10)).pack(anchor=tk.W, pady=5)
        for key, label in [
            ("simple", "简单产线（3 工序）"),
            ("standard", "标准产线（5 工序）"),
            ("complex", "复杂产线（8 工序，真实参数）"),
            ("blank", "空白产线（手动添加）"),
        ]:
            ttk.Radiobutton(
                self.page_template,
                text=label,
                variable=self.template_var,
                value=key,
            ).pack(anchor=tk.W, pady=3)
        ttk.Button(
            self.page_template,
            text="术语速查",
            command=lambda: GlossaryDialog(self.dialog),
        ).pack(anchor=tk.W, pady=8)

    def _build_page_source(self) -> None:
        """步骤 2：数据来源"""
        ttk.Label(self.page_source, text="数据来源：", font=('Arial', 10)).pack(anchor=tk.W, pady=5)
        ttk.Label(
            self.page_source,
            text="默认使用所选模板；也可以额外从 Excel 导入替换模板数据。",
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 10))

        source_frame = ttk.Frame(self.page_source)
        source_frame.pack(fill=tk.X)
        ttk.Button(source_frame, text="选择 Excel 文件...", command=self._pick_excel).pack(side=tk.LEFT)
        self.excel_label = ttk.Label(source_frame, text="未选择", foreground="gray")
        self.excel_label.pack(side=tk.LEFT, padx=10)

    def _build_page_shift(self) -> None:
        """步骤 3：班次设置"""
        ttk.Label(self.page_shift, text="班次设置：", font=('Arial', 10)).pack(anchor=tk.W, pady=5)
        form = ttk.Frame(self.page_shift)
        form.pack(fill=tk.X, pady=10)

        ttk.Label(form, text="班次时长(小时):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form, textvariable=self.shift_hours_var, width=10).grid(row=0, column=1, padx=10)

        ttk.Label(form, text="休息时间(分钟):").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form, textvariable=self.break_minutes_var, width=10).grid(row=1, column=1, padx=10)

        ttk.Label(form, text="工人时薪(元/小时):").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form, textvariable=self.wage_var, width=10).grid(row=2, column=1, padx=10)

    def _build_page_finish(self) -> None:
        """步骤 4：完成"""
        self.summary_text = tk.Text(self.page_finish, height=12, width=70, state=tk.DISABLED)
        self.summary_text.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Checkbutton(
            self.page_finish,
            text="配置完成后立即开始仿真",
            variable=self.auto_start_var,
        ).pack(anchor=tk.W, pady=5)

    def _pick_excel(self) -> None:
        """选择并导入 Excel 配置"""
        from tkinter import filedialog
        from src.utils import import_from_excel

        path = filedialog.askopenfilename(
            title="导入 Excel 配置",
            filetypes=[("Excel 文件", "*.xlsx *.xls"), ("所有文件", "*.*")],
        )
        if not path:
            return
        line, error = import_from_excel(path)
        if line:
            self.production_line = line
            self.excel_path_var.set(path)
            self.excel_label.config(text=f"已导入：{path}（{len(line.stations)} 个工序）", foreground="green")
        else:
            messagebox.showerror("导入失败", error or "未知错误")

    def _make_template_line(self) -> ProductionLine:
        """根据所选模板创建产线"""
        production_type = self.production_type_var.get()
        if production_type == "liquid_filling":
            return create_liquid_line()
        if production_type == "pouch_packaging":
            return create_pouch_line()
        return build_template_line(self.template_var.get())

    def _show_step(self, index: int) -> None:
        """切换步骤页面"""
        self.step_index = index
        pages = [self.page_template, self.page_source, self.page_shift, self.page_finish]
        titles = ["第 1 步 / 共 4 步：选择模板", "第 2 步 / 共 4 步：数据来源", "第 3 步 / 共 4 步：班次设置", "第 4 步 / 共 4 步：完成"]
        for i, page in enumerate(pages):
            page.pack_forget()
        pages[index].pack(fill=tk.BOTH, expand=True)
        self.step_label.config(text=titles[index])
        self.btn_prev.config(state=tk.NORMAL if index > 0 else tk.DISABLED)
        self.btn_next.config(text="完成" if index == len(pages) - 1 else "下一步")
        if index == len(pages) - 1:
            self._refresh_summary()

    def _refresh_summary(self) -> None:
        """刷新完成页摘要"""
        if self.production_line is None:
            self.production_line = self._make_template_line()
        line = self.production_line
        summary = (
            f"产线名称：{line.name}\n"
            f"工序数量：{len(line.stations)}\n"
            f"总人数：{sum(s.worker_count for s in line.stations)} 人\n"
            f"班次：{self.shift_hours_var.get()} 小时 / 休息 {self.break_minutes_var.get()} 分钟\n"
            f"时薪：{self.wage_var.get()} 元/小时\n"
        )
        if line.stations:
            summary += f"瓶颈产能：{line.get_bottleneck_capacity():.0f} 颗/h\n"
            summary += f"预计日产量：{line.calculate_daily_output():.0f} 颗\n"
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", summary)
        self.summary_text.config(state=tk.DISABLED)

    def _prev(self) -> None:
        if self.step_index > 0:
            self._show_step(self.step_index - 1)

    def _next(self) -> None:
        if self.step_index < 3:
            # 进入步骤 3 前确保产线已就绪
            if self.step_index == 1 and self.production_line is None:
                self.production_line = self._make_template_line()
            self._show_step(self.step_index + 1)
            return

        # 完成：应用班次配置
        try:
            shift_hours = int(self.shift_hours_var.get())
            break_minutes = int(self.break_minutes_var.get())
            wage = float(self.wage_var.get())
            if shift_hours <= 0 or break_minutes < 0 or wage <= 0:
                raise ValueError("班次参数不合法")
        except ValueError as e:
            messagebox.showerror("错误", f"班次参数错误：{e}")
            return

        if self.production_line is None:
            self.production_line = self._make_template_line()
        self.production_line.shift_hours = shift_hours
        self.production_line.break_minutes = break_minutes
        self.production_line.worker_hourly_wage = wage

        self.result = {
            "production_line": self.production_line,
            "auto_start": self.auto_start_var.get(),
        }
        self.dialog.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.dialog.destroy()
