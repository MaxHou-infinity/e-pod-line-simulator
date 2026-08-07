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
from tkinter import ttk, messagebox
from typing import List, Optional, Callable, Dict, Any

from src.models import Station, Alert, CollaborationType, ProductionLine
from src.utils import validate_station, get_alert_color
from src.scenario_manager import ScenarioManager


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
        # 标题
        title_label = ttk.Label(self, text="工序配置", font=('Arial', 12, 'bold'))
        title_label.pack(pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 添加按钮
        btn_add = ttk.Button(button_frame, text="添加", command=self._btn_add)
        btn_add.pack(side=tk.LEFT, padx=2)
        
        # 编辑按钮
        btn_edit = ttk.Button(button_frame, text="编辑", command=self._btn_edit)
        btn_edit.pack(side=tk.LEFT, padx=2)
        
        # 删除按钮
        btn_delete = ttk.Button(button_frame, text="删除", command=self._btn_delete)
        btn_delete.pack(side=tk.LEFT, padx=2)
        
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
        
        # 分隔线
        separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=10)
        
        # 使用Grid布局，6列显示6个KPI
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
        
        for i, (key, label, unit) in enumerate(kpis):
            # KPI名称
            name_label = ttk.Label(kpi_frame, text=label)
            name_label.grid(row=0, column=i, padx=10, pady=5)
            
            # KPI数值
            value_label = ttk.Label(
                kpi_frame,
                text="--",
                font=('Arial', 14, 'bold'),
                foreground='blue'
            )
            value_label.grid(row=1, column=i, padx=10, pady=5)
            
            # 单位标签
            unit_label = ttk.Label(kpi_frame, text=unit, font=('Arial', 9))
            unit_label.grid(row=2, column=i, padx=10)
            
            # 保存标签引用
            self.kpi_labels[key] = value_label
    
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
        
        # 报警列表（使用Text组件显示）
        self.text_widget = tk.Text(self, height=10, wrap=tk.WORD)
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        
        # 配置文本样式
        self.text_widget.config(state=tk.DISABLED)  # 只读
    
    def add_alert(self, alert: Alert) -> None:
        """
        添加报警信息
        
        Args:
            alert: 报警对象
        """
        # 启用编辑
        self.text_widget.config(state=tk.NORMAL)
        
        # 获取颜色
        color = get_alert_color(alert.severity)
        
        # 格式化时间戳（分钟）
        time_str = f"{alert.timestamp_minutes:.1f}分钟"
        
        # 插入报警文本（包含时间戳）
        text = f"[{time_str}] [{alert.severity.upper()}] {alert.message}\n"
        if alert.suggestion:
            text += f"  建议：{alert.suggestion}\n"
        text += "\n"
        
        # 插入文本并应用颜色标记
        start_pos = self.text_widget.index(tk.END)
        self.text_widget.insert(tk.END, text)
        end_pos = self.text_widget.index(tk.END)
        
        # 应用颜色标记（整个文本）
        self.text_widget.tag_add(alert.severity, start_pos, end_pos)
        self.text_widget.tag_config(alert.severity, foreground=color)
        
        # 滚动到底部
        self.text_widget.see(tk.END)
        
        # 禁用编辑
        self.text_widget.config(state=tk.DISABLED)
    
    def clear(self) -> None:
        """清空报警信息"""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.config(state=tk.DISABLED)


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
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x350")
        self.dialog.transient(parent)  # 设置为父窗口的子窗口
        self.dialog.grab_set()  # 模态对话框
        
        # 创建输入字段
        self._create_widgets(station)
        
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
        ttk.Label(main_frame, text="单颗耗时(秒):").grid(row=1, column=0, sticky=tk.W, pady=5)
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
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        # 确定按钮
        btn_ok = ttk.Button(button_frame, text="确定", command=self._btn_ok)
        btn_ok.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        btn_cancel = ttk.Button(button_frame, text="取消", command=self._btn_cancel)
        btn_cancel.pack(side=tk.LEFT, padx=10)
        
        # 聚焦到名称输入框
        name_entry.focus()
    
    def _btn_ok(self) -> None:
        """确定按钮点击"""
        try:
            # 获取输入值
            name = self.name_var.get().strip()
            process_time = float(self.time_var.get())
            worker_count = int(self.workers_var.get())
            oee = float(self.oee_var.get())
            mode = CollaborationType(self.mode_var.get())
            
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
                oee=oee
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
        self.dialog.geometry("320x200")  # 缩小对话框尺寸
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建输入字段
        self._create_widgets(shift_hours, break_minutes, worker_hourly_wage)
        
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
        btn_ok = ttk.Button(button_frame, text="确定", command=self._btn_ok)
        btn_ok.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        btn_cancel = ttk.Button(button_frame, text="取消", command=self._btn_cancel)
        btn_cancel.pack(side=tk.LEFT, padx=5)
        
        # 聚焦到第一个输入框
        shift_entry.focus()
    
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
        
        # 提示信息
        info_label = ttk.Label(
            main_frame,
            text=f"当前已保存 {self.scenario_manager.get_scenario_count()}/{self.scenario_manager.MAX_SCENARIOS} 个方案",
            font=('Arial', 9),
            foreground='gray'
        )
        info_label.grid(row=2, column=0, columnspan=2, pady=10)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="确定", command=self._on_confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=self._on_cancel).pack(side=tk.LEFT, padx=5)
    
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
            self.result = {'name': name, 'description': description}
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
        
        # 创建界面（先创建界面，再计算位置）
        self._create_widgets()
        
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
        kpi_configs = [
            ('total_workers', '总人数', '人', lambda x: f"{int(x)}人"),
            ('bottleneck_capacity', '瓶颈产能', '颗/h', lambda x: f"{x:.0f}"),
            ('daily_output', '日产量', '颗', lambda x: f"{x:.0f}"),
            ('total_cost', '日成本', '元', lambda x: f"{x:.0f}"),
            ('unit_cost', '单颗成本', '元/颗', lambda x: f"{x:.2f}"),
            ('balance_rate', '产线平衡率', '%', lambda x: f"{x*100:.1f}%"),
            ('upph', 'UPPH', '颗/人·h', lambda x: f"{x:.1f}")
        ]
        
        # 遍历每个KPI指标
        for metric_key, metric_name, unit, format_func in kpi_configs:
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
                item_id = self.tree.insert('', tk.END, values=row_values)
                
                # 根据差异设置颜色（改善=绿色，恶化=红色）
                # 注意：Treeview的颜色设置需要特殊处理，这里先不设置
