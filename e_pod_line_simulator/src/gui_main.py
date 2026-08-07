"""
GUI主窗口 - 程序的主界面

这个文件包含主窗口类，负责：
1. 创建和布局所有GUI组件
2. 协调各组件之间的通信
3. 处理菜单栏事件
4. 管理仿真流程

GUI布局：
┌─────────────────────────────────────────┐
│ 菜单栏: 文件 | 编辑 | 仿真 | 分析 | 帮助 │
├──────────┬──────────────────────────────┤
│          │                              │
│ 配置面板  │      2D产线画布              │
│          │                              │
│ 工序列表  │                              │
│ [添加]    │                              │
│ [编辑]    │                              │
│ [删除]    │                              │
├──────────┴──────────────────────────────┤
│ KPI仪表盘: 瓶颈产能 | 日产量 | 成本      │
│ 控制按钮: [开始] [暂停] [重置] [速度]    │
└─────────────────────────────────────────┘
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Optional
import threading

from src.models import ProductionLine, Station, SimulationState
from src.simulation import SimulationEngine
from src.gui_canvas import CanvasView
from src.gui_panels import (
    ConfigPanel,
    KPIDashboard,
    AlertPanel,
    SaveScenarioDialog,
    ScenarioCompareDialog,
    WizardDialog,
)
from src.utils import load_config, save_config, import_from_excel, validate_production_line, setup_logger
from src.scenario_manager import ScenarioManager
from src.reporting import export_report
from src.version import __version__


class MainWindow:
    """
    主窗口类 - 应用程序的主界面
    
    这是整个GUI的核心，负责：
    - 创建窗口和布局
    - 管理产线数据
    - 控制仿真流程
    - 处理用户交互
    
    使用方式：
        app = MainWindow()
        app.run()
    """
    
    def __init__(self):
        """
        初始化主窗口
        
        创建所有GUI组件，初始化数据
        """
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title(f"电子烟产线仿真优化工具 v{__version__}")
        self.root.geometry("1400x800")  # 窗口大小：宽1400，高800
        
        # 设置窗口最小尺寸
        self.root.minsize(1000, 600)
        
        # 初始化日志
        self.logger = setup_logger()
        self.logger.info("程序启动")

        # 全局异常捕获：Tkinter 回调中的未捕获异常统一记录日志并提示
        self.root.report_callback_exception = self._on_callback_exception
        
        # 数据模型
        self.production_line: Optional[ProductionLine] = None  # 当前产线对象
        self.simulation_engine: Optional[SimulationEngine] = None  # 仿真引擎
        self.scenario_manager = ScenarioManager()  # 方案管理器（管理保存的方案）
        
        # 创建GUI组件
        self._create_menu_bar()  # 创建菜单栏
        self._create_main_layout()  # 创建主布局
        self._create_status_bar()  # 创建状态栏
        
        # 初始化一个默认产线（可选）
        # self._create_default_line()  # 暂时注释，避免导入问题
    
    def _create_menu_bar(self) -> None:
        """
        创建菜单栏
        
        菜单栏包含：
        - 文件：新建、打开、保存、退出
        - 编辑：添加工序、删除工序
        - 仿真：开始、暂停、停止
        - 分析：方案对比、导出报告
        - 帮助：使用说明、关于
        """
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="新建产线", command=self._menu_new_line)
        file_menu.add_command(label="打开配置", command=self._menu_open_config)
        file_menu.add_command(label="保存配置", command=self._menu_save_config)
        file_menu.add_separator()
        file_menu.add_command(label="导入Excel", command=self._menu_import_excel)
        file_menu.add_separator()
        file_menu.add_command(label="快速配置向导...", command=self._menu_wizard)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._menu_exit)
        
        # 编辑菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        edit_menu.add_command(label="添加工序", command=self._menu_add_station)
        edit_menu.add_command(label="编辑工序", command=self._menu_edit_station)
        edit_menu.add_command(label="删除工序", command=self._menu_delete_station)
        
        # 仿真菜单
        sim_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="仿真", menu=sim_menu)
        sim_menu.add_command(label="开始仿真", command=self._menu_start_simulation)
        sim_menu.add_command(label="暂停仿真", command=self._menu_pause_simulation)
        sim_menu.add_command(label="停止仿真", command=self._menu_stop_simulation)
        sim_menu.add_separator()
        sim_menu.add_command(label="触发切换...", command=self._menu_trigger_changeover)
        
        # 分析菜单
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="分析", menu=analysis_menu)
        analysis_menu.add_command(label="方案对比", command=self._menu_compare_solutions)
        analysis_menu.add_command(label="导出报告", command=self._menu_export_report)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self._menu_help)
        help_menu.add_command(label="关于", command=self._menu_about)
    
    def _create_main_layout(self) -> None:
        """
        创建主布局
        
        主布局分为三个区域：
        1. 左侧：配置面板（工序列表、编辑功能）
        2. 中间：画布视图（2D产线可视化）
        3. 底部：KPI仪表盘和控制按钮
        """
        # 创建主容器（使用PanedWindow实现可调整大小的分割）
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧：配置面板
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame, weight=1)
        
        self.config_panel = ConfigPanel(
            left_frame,
            on_add=self._on_add_station,
            on_edit=self._on_edit_station,
            on_delete=self._on_delete_station,
            on_select=self._on_select_station
        )
        self.config_panel.pack(fill=tk.BOTH, expand=True)
        
        # 右侧：画布和KPI
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=3)
        
        # 画布视图（2D可视化）
        canvas_frame = ttk.Frame(right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas_view = CanvasView(
            canvas_frame,
            width=1000,
            height=500,
            on_reorder=self._on_canvas_reorder,
            on_station_edit=self._on_edit_station,
            on_station_select=self._on_canvas_select_station,
            on_station_menu=self._on_canvas_station_menu,
        )
        self.canvas_view.pack(fill=tk.BOTH, expand=True)
        
        # 底部：KPI仪表盘和控制按钮
        bottom_frame = ttk.Frame(right_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # KPI仪表盘
        self.kpi_dashboard = KPIDashboard(bottom_frame)
        self.kpi_dashboard.pack(fill=tk.X, pady=5)
        
        # 控制按钮
        control_frame = ttk.Frame(bottom_frame)
        control_frame.pack(fill=tk.X)
        
        # 开始按钮
        self.btn_start = ttk.Button(
            control_frame,
            text="开始仿真",
            command=self._btn_start_simulation
        )
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        # 暂停按钮
        self.btn_pause = ttk.Button(
            control_frame,
            text="暂停",
            command=self._btn_pause_simulation,
            state=tk.DISABLED
        )
        self.btn_pause.pack(side=tk.LEFT, padx=5)
        
        # 停止按钮
        self.btn_stop = ttk.Button(
            control_frame,
            text="停止",
            command=self._btn_stop_simulation,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        # 速度选择
        speed_frame = ttk.Frame(control_frame)
        speed_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(speed_frame, text="速度:").pack(side=tk.LEFT)
        self.speed_var = tk.StringVar(value="16")
        speed_combo = ttk.Combobox(
            speed_frame,
            textvariable=self.speed_var,
            values=["1", "2", "8", "16", "32", "64"],  # 添加32倍和64倍速
            width=5,
            state="readonly"
        )
        speed_combo.pack(side=tk.LEFT)
        
        # 班次配置按钮
        btn_config = ttk.Button(control_frame, text="班次配置", command=self._btn_config_shift)
        btn_config.pack(side=tk.LEFT, padx=5)
        
        # 保存方案按钮
        ttk.Button(
            control_frame,
            text="保存方案",
            command=self._btn_save_scenario
        ).pack(side=tk.LEFT, padx=5)
        
        # 报警面板
        alert_frame = ttk.Frame(right_frame)
        alert_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.alert_panel = AlertPanel(alert_frame)
        self.alert_panel.pack(fill=tk.BOTH, expand=True)
    
    def _create_status_bar(self) -> None:
        """
        创建状态栏
        
        状态栏显示程序运行状态和提示信息
        """
        self.status_bar = ttk.Label(
            self.root,
            text="就绪",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_default_line(self) -> None:
        """
        创建一个默认产线（用于测试和演示）
        
        如果用户没有加载配置，提供一个示例产线
        """
        try:
            from .models import CollaborationType
        except ImportError:
            from models import CollaborationType
        
        line = ProductionLine("示例产线")
        
        # 添加几个示例工序
        line.add_station(Station(
            id="s01",
            name="注油",
            process_time=25,
            worker_count=2,
            collaboration_type=CollaborationType.PARALLEL
        ))
        
        line.add_station(Station(
            id="s02",
            name="焊接",
            process_time=30,
            worker_count=3,
            collaboration_type=CollaborationType.PARALLEL
        ))
        
        line.add_station(Station(
            id="s03",
            name="包装",
            process_time=15,
            worker_count=2,
            collaboration_type=CollaborationType.PARALLEL
        ))
        
        self.production_line = line
        self._update_display()
    
    def _update_display(self) -> None:
        """
        更新所有GUI显示
        
        当产线数据发生变化时，调用此方法更新所有显示
        """
        if self.production_line is None:
            return
        
        # 更新配置面板（传递产线引用，用于查找Station对象）
        self.config_panel.update_stations(self.production_line.stations, self.production_line)
        
        # 更新画布
        self.canvas_view.update_production_line(self.production_line)
        
        # 更新KPI
        self._update_kpi()
    
    def _update_kpi(self) -> None:
        """
        更新KPI仪表盘
        
        计算并显示关键绩效指标
        """
        if self.production_line is None:
            return
        
        bottleneck_capacity = self.production_line.get_bottleneck_capacity()
        daily_output = self.production_line.calculate_daily_output()
        total_cost = self.production_line.calculate_total_cost()
        unit_cost = self.production_line.calculate_unit_cost()
        balance_rate = self.production_line.calculate_line_balance_rate()
        upph = self.production_line.calculate_upph()
        
        self.kpi_dashboard.update_kpis({
            'bottleneck_capacity': bottleneck_capacity,
            'daily_output': daily_output,
            'total_cost': total_cost,
            'unit_cost': unit_cost,
            'balance_rate': balance_rate,
            'upph': upph
        })
    
    # ==================== 菜单事件处理 ====================
    
    def _menu_new_line(self) -> None:
        """文件菜单 - 新建产线"""
        if messagebox.askyesno("确认", "创建新产线将清空当前配置，是否继续？"):
            self.production_line = ProductionLine("新产线")
            self._update_display()
            self.status_bar.config(text="已创建新产线")
    
    def _menu_open_config(self) -> None:
        """文件菜单 - 打开配置"""
        file_path = filedialog.askopenfilename(
            title="打开配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            line = load_config(file_path)
            if line:
                self.production_line = line
                self._update_display()
                self.status_bar.config(text=f"已加载：{line.name}")
            else:
                messagebox.showerror("错误", "加载配置失败")
    
    def _menu_save_config(self) -> None:
        """文件菜单 - 保存配置"""
        if self.production_line is None:
            messagebox.showwarning("警告", "没有可保存的产线配置")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="保存配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            if save_config(self.production_line, file_path):
                self.status_bar.config(text=f"已保存：{file_path}")
            else:
                messagebox.showerror("错误", "保存配置失败")
    
    def _menu_import_excel(self) -> None:
        """文件菜单 - 导入Excel配置"""
        file_path = filedialog.askopenfilename(
            title="导入Excel配置",
            filetypes=[("Excel文件", "*.xlsx *.xls"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        # 导入Excel文件
        line, error_msg = import_from_excel(file_path)
        
        if line:
            # 导入成功
            self.production_line = line
            self._update_display()
            
            # 如果有警告信息，显示警告对话框
            if error_msg:
                messagebox.showwarning("导入完成（有警告）", f"成功导入{len(line.stations)}个工序\n\n{error_msg}")
                self.status_bar.config(text=f"已导入：{line.name}（{len(line.stations)}个工序，有警告）")
            else:
                self.status_bar.config(text=f"已导入：{line.name}（{len(line.stations)}个工序）")
        else:
            # 导入失败，显示错误信息
            messagebox.showerror("导入失败", error_msg or "未知错误")
    
    def _menu_exit(self) -> None:
        """文件菜单 - 退出"""
        if messagebox.askyesno("确认", "确定要退出吗？"):
            self.root.quit()

    def _menu_wizard(self) -> None:
        """文件菜单 - 快速配置向导"""
        dialog = WizardDialog(self.root)
        if not dialog.result:
            return

        self.production_line = dialog.result["production_line"]
        self._update_display()
        self.status_bar.config(text="快速配置向导完成")
        self.logger.info("快速配置向导完成：%s", self.production_line.name)

        if dialog.result.get("auto_start") and self.production_line.stations:
            self._btn_start_simulation()
    
    def _menu_add_station(self) -> None:
        """编辑菜单 - 添加工序"""
        self._on_add_station()
    
    def _menu_edit_station(self) -> None:
        """编辑菜单 - 编辑工序"""
        self._on_edit_station()
    
    def _menu_delete_station(self) -> None:
        """编辑菜单 - 删除工序"""
        self._on_delete_station()
    
    def _menu_start_simulation(self) -> None:
        """仿真菜单 - 开始仿真"""
        self._btn_start_simulation()
    
    def _menu_pause_simulation(self) -> None:
        """仿真菜单 - 暂停仿真"""
        self._btn_pause_simulation()
    
    def _menu_stop_simulation(self) -> None:
        """仿真菜单 - 停止仿真"""
        self._btn_stop_simulation()
    
    def _menu_compare_solutions(self) -> None:
        """分析菜单 - 方案对比"""
        # 检查方案数量
        scenario_count = self.scenario_manager.get_scenario_count()
        
        if scenario_count < self.scenario_manager.MIN_SCENARIOS_FOR_COMPARE:
            messagebox.showwarning(
                "无法对比",
                f"至少需要{self.scenario_manager.MIN_SCENARIOS_FOR_COMPARE}个方案才能对比\n"
                f"当前已保存 {scenario_count} 个方案\n\n"
                f"请先保存至少{self.scenario_manager.MIN_SCENARIOS_FOR_COMPARE}个方案"
            )
            return
        
        # 获取所有方案名称
        scenario_names = self.scenario_manager.list_scenarios()
        
        # 打开对比对话框（对比所有方案）
        ScenarioCompareDialog(self.root, self.scenario_manager, scenario_names)
    
    def _btn_save_scenario(self) -> None:
        """保存方案按钮点击事件"""
        # 检查是否有产线配置
        if self.production_line is None:
            messagebox.showwarning("警告", "没有可保存的产线配置\n请先创建或加载产线")
            return
        
        # 检查方案数量限制
        if not self.scenario_manager.can_add_scenario():
            messagebox.showwarning(
                "方案数量已达上限",
                f"方案数量已达到上限（{self.scenario_manager.MAX_SCENARIOS}个）\n"
                f"请先删除一个方案或使用方案对比功能"
            )
            return
        
        # 打开保存方案对话框
        dialog = SaveScenarioDialog(self.root, self.scenario_manager, self.production_line)
        
        # 检查保存结果
        if dialog.result:
            messagebox.showinfo("成功", f"方案'{dialog.result['name']}'已保存")
            self.status_bar.config(text=f"已保存方案：{dialog.result['name']}")
    
    def _menu_export_report(self) -> None:
        """分析菜单 - 导出报告"""
        if self.production_line is None or not self.production_line.stations:
            messagebox.showwarning("警告", "没有可导出的产线配置")
            return

        # 有正在运行的仿真时导出当前进度；否则用当前配置快速仿真一次
        result = None
        try:
            if self.simulation_engine and self.simulation_engine.is_running:
                result = self.simulation_engine.build_result()
            else:
                engine = SimulationEngine(self.production_line)
                result = engine.run_sync(duration_hours=self.production_line.shift_hours)
        except Exception as e:
            messagebox.showerror("导出失败", f"仿真失败：{e}")
            self.logger.error("导出前仿真失败", exc_info=True)
            return

        file_path = filedialog.asksaveasfilename(
            title="导出报告",
            defaultextension=".xlsx",
            filetypes=[
                ("Excel 报告", "*.xlsx"),
                ("PDF 报告", "*.pdf"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return

        if export_report(result, file_path):
            messagebox.showinfo("成功", f"报告已导出：\n{file_path}")
            self.status_bar.config(text=f"报告已导出：{file_path}")
            self.logger.info("导出报告成功：%s", file_path)
        else:
            messagebox.showerror("失败", "报告导出失败，请检查路径或依赖（reportlab/openpyxl）")
            self.logger.error("导出报告失败：%s", file_path)
    
    def _menu_help(self) -> None:
        """帮助菜单 - 使用说明"""
        help_text = """
电子烟产线仿真优化工具 v{__version__}

使用步骤：
1. 创建或加载产线配置
2. 添加/编辑工序参数
3. 点击"开始仿真"运行仿真
4. 观察瓶颈和KPI指标
5. 调整参数优化产线

更多信息请查看文档。
        """
        messagebox.showinfo("使用说明", help_text)
    
    def _menu_about(self) -> None:
        """帮助菜单 - 关于"""
        about_text = """
电子烟产线仿真优化工具 v{__version__}

基于SimPy的离散事件仿真引擎
用于产线设计和人力优化

开发：Max主人
        """
        messagebox.showinfo("关于", about_text)

    def _on_callback_exception(self, exc_type, exc_value, exc_tb) -> None:
        """Tkinter 回调异常统一处理：记录日志并弹窗提示"""
        if self.logger:
            self.logger.error("界面回调异常", exc_info=(exc_type, exc_value, exc_tb))
        messagebox.showerror("程序错误", f"发生未预期错误：{exc_value}")
    
    # ==================== 按钮事件处理 ====================
    
    def _btn_start_simulation(self) -> None:
        """开始仿真按钮"""
        if self.production_line is None or not self.production_line.stations:
            messagebox.showwarning("警告", "请先添加至少一个工序")
            return
        
        # 校验产线配置
        valid, error = validate_production_line(self.production_line)
        if not valid:
            messagebox.showerror("错误", f"产线配置无效：{error}")
            return
        
        # 判断是否是新的仿真（停止后重新开始）还是暂停后继续
        is_new_simulation = False
        
        if self.simulation_engine is None:
            # 没有仿真引擎，是新的仿真
            is_new_simulation = True
            # 创建新的仿真引擎
            self.simulation_engine = SimulationEngine(self.production_line)
            # 设置状态更新回调
            self.simulation_engine.set_callback(self._on_simulation_state_update)
        elif not self.simulation_engine.is_running:
            # 仿真已停止，是新的仿真
            is_new_simulation = True
            # 创建新的仿真引擎
            self.simulation_engine = SimulationEngine(self.production_line)
            # 设置状态更新回调
            self.simulation_engine.set_callback(self._on_simulation_state_update)
        elif self.simulation_engine.is_paused:
            # 暂停后继续，恢复仿真
            self.simulation_engine.resume()
            # 不清空报警信息
            self.status_bar.config(text="仿真已恢复")
            # 更新按钮状态
            self.btn_start.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.NORMAL)
            return  # 不需要重新启动仿真
        
        # 如果是新的仿真，清空报警信息并重置时间戳
        if is_new_simulation:
            self.alert_panel.clear()
            self.kpi_dashboard.reset_timestamp()  # 重置时间戳
        
        # 获取仿真速度
        speed = int(self.speed_var.get())
        
        # 运行仿真（使用产线的班次配置）
        duration_hours = self.production_line.shift_hours if self.production_line else 8.0
        self.simulation_engine.run(duration_hours=duration_hours, speed=speed)
        
        # 更新按钮状态
        self.btn_start.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        
        self.status_bar.config(text="仿真运行中...")
    
    def _btn_pause_simulation(self) -> None:
        """暂停仿真按钮"""
        if self.simulation_engine:
            self.simulation_engine.pause()
            self.status_bar.config(text="仿真已暂停")
            # 暂停时，时间戳不再更新（保持当前值）
    
    def _btn_stop_simulation(self) -> None:
        """停止仿真按钮"""
        if self.simulation_engine:
            try:
                self.simulation_engine.stop()
            except:
                pass  # 忽略停止时的错误
            finally:
                # 确保清理资源
                self.simulation_engine = None
                
                # 更新按钮状态
                self.btn_start.config(state=tk.NORMAL)
                self.btn_pause.config(state=tk.DISABLED)
                self.btn_stop.config(state=tk.DISABLED)
                
                # 重置画布状态（如果有的话）
                if self.canvas_view and self.production_line:
                    # 重置所有工序状态为idle
                    for station in self.production_line.stations:
                        station.current_status = "idle"
                        station.wip_count = 0
                    # 更新画布显示
                    self.canvas_view.update_production_line(self.production_line)
                
                # 注意：停止时不清空报警信息，只在重新开始仿真时清空
                self.status_bar.config(text="仿真已停止")
    
    def _btn_config_shift(self) -> None:
        """班次配置按钮"""
        if self.production_line is None:
            self.production_line = ProductionLine("新产线")
        
        # 打开班次配置对话框
        try:
            from .gui_panels import ShiftConfigDialog
        except ImportError:
            from gui_panels import ShiftConfigDialog
        
        dialog = ShiftConfigDialog(
            self.root,
            shift_hours=self.production_line.shift_hours,
            break_minutes=self.production_line.break_minutes,
            worker_hourly_wage=self.production_line.worker_hourly_wage
        )
        
        if dialog.result:
            # 更新产线配置
            self.production_line.shift_hours = dialog.result['shift_hours']
            self.production_line.break_minutes = dialog.result['break_minutes']
            self.production_line.worker_hourly_wage = dialog.result['worker_hourly_wage']
            
            # 更新KPI显示
            self._update_kpi()
            
            self.status_bar.config(text="班次配置已更新")
    
    # ==================== 配置面板回调 ====================
    
    def _on_add_station(self) -> None:
        """配置面板 - 添加工序回调"""
        try:
            from .gui_panels import StationDialog
        except ImportError:
            from gui_panels import StationDialog
        
        dialog = StationDialog(self.root, title="添加工序", production_line=self.production_line)
        if dialog.result:
            if self.production_line is None:
                self.production_line = ProductionLine("新产线")
            
            station = dialog.result
            self.production_line.add_station(station)
            self._update_display()
            self.status_bar.config(text=f"已添加工序：{station.name}")
    
    def _on_edit_station(self, station_id: Optional[str] = None) -> None:
        """配置面板 - 编辑工序回调"""
        try:
            from .gui_panels import StationDialog
        except ImportError:
            from gui_panels import StationDialog
        
        if self.production_line is None or not self.production_line.stations:
            messagebox.showwarning("警告", "没有可编辑的工序")
            return
        
        # 如果没有指定ID，获取选中的工序
        if station_id is None:
            selected = self.config_panel.get_selected_station()
            if selected is None:
                messagebox.showwarning("警告", "请先选择一个工序")
                return
            station_id = selected.id
        
        # 找到要编辑的工序
        station = self.production_line.get_station(station_id)
        if station is None:
            messagebox.showerror("错误", f"找不到工序：{station_id}")
            return
        
        # 打开编辑对话框
        dialog = StationDialog(self.root, title="编辑工序", station=station)
        if dialog.result:
            # 更新工序数据
            updated = dialog.result
            station.name = updated.name
            station.process_time = updated.process_time
            station.worker_count = updated.worker_count
            station.oee = updated.oee
            station.collaboration_type = updated.collaboration_type
            
            self._update_display()
            self.status_bar.config(text=f"已更新工序：{station.name}")
    
    def _on_delete_station(self) -> None:
        """配置面板 - 删除工序回调"""
        if self.production_line is None or not self.production_line.stations:
            messagebox.showwarning("警告", "没有可删除的工序")
            return
        
        selected = self.config_panel.get_selected_station()
        if selected is None:
            messagebox.showwarning("警告", "请先选择一个工序")
            return
        
        if messagebox.askyesno("确认", f"确定要删除工序 '{selected.name}' 吗？"):
            self.production_line.remove_station(selected.id)
            self._update_display()
            self.status_bar.config(text=f"已删除工序：{selected.name}")
    
    def _on_select_station(self, station: Station) -> None:
        """配置面板 - 选择工序回调"""
        # 在画布上高亮显示选中的工序
        if self.canvas_view:
            self.canvas_view.highlight_station(station.id)

    def _on_canvas_reorder(self, order_ids: list) -> None:
        """画布拖拽排序回调：更新产线工序顺序"""
        if self.production_line is None:
            return
        if self.simulation_engine and self.simulation_engine.is_running:
            messagebox.showwarning("警告", "仿真运行中不能调整工序顺序")
            self.canvas_view.update_production_line(self.production_line)
            return

        station_map = {s.id: s for s in self.production_line.stations}
        self.production_line.stations = [
            station_map[sid] for sid in order_ids if sid in station_map
        ]
        self._update_display()
        self.status_bar.config(text="工序顺序已调整")
        self.logger.info("拖拽调整工序顺序：%s", order_ids)

    def _on_canvas_select_station(self, station_id: str) -> None:
        """画布单击工序：高亮并联动配置面板"""
        if self.canvas_view:
            self.canvas_view.highlight_station(station_id)
        if self.config_panel:
            self.config_panel.select_station(station_id)

    def _on_canvas_station_menu(self, station_id: str, x: int, y: int) -> None:
        """画布右键菜单：编辑 / 删除 / 触发切换"""
        station = self.production_line.get_station(station_id) if self.production_line else None
        if station is None:
            return

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="编辑工序", command=lambda: self._on_edit_station(station_id))
        menu.add_command(label="删除工序", command=lambda: self._delete_station_by_id(station_id))
        menu.add_separator()
        menu.add_command(label="触发切换...", command=lambda: self._trigger_changeover(station_id))
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _delete_station_by_id(self, station_id: str) -> None:
        """按 ID 删除工序（供右键菜单调用）"""
        if self.production_line is None:
            return
        station = self.production_line.get_station(station_id)
        if station is None:
            return
        if messagebox.askyesno("确认", f"确定要删除工序 '{station.name}' 吗？"):
            self.production_line.remove_station(station_id)
            self._update_display()
            self.status_bar.config(text=f"已删除工序：{station.name}")

    def _menu_trigger_changeover(self) -> None:
        """仿真菜单 - 触发切换（使用当前选中工序）"""
        selected = self.config_panel.get_selected_station()
        if selected is None:
            messagebox.showwarning("警告", "请先选择一个工序")
            return
        self._trigger_changeover(selected.id)

    def _trigger_changeover(self, station_id: str) -> None:
        """触发指定工序的切换停机"""
        if not self.simulation_engine or not self.simulation_engine.is_running:
            messagebox.showwarning("警告", "请先开始仿真，再触发切换")
            return
        station = self.production_line.get_station(station_id)
        if station is None:
            return
        minutes = simpledialog.askinteger(
            "触发切换",
            f"请输入「{station.name}」的切换停机时长（分钟）：",
            initialvalue=station.changeover_time or 45,
            minvalue=1,
            maxvalue=600,
        )
        if not minutes:
            return
        try:
            self.simulation_engine.trigger_changeover(station_id, minutes)
            self.status_bar.config(text=f"已触发「{station.name}」切换，停机{minutes}分钟")
        except ValueError as e:
            messagebox.showerror("错误", str(e))

    # ==================== 仿真回调 ====================
    
    def _on_simulation_state_update(self, state: SimulationState) -> None:
        """
        仿真状态更新回调
        
        当仿真状态发生变化时，SimPy会调用这个函数
        注意：这个函数可能在SimPy线程中调用，需要切换到GUI线程
        
        Args:
            state: 新的仿真状态
        """
        # 使用after()方法确保在GUI线程中执行
        self.root.after(0, lambda: self._update_simulation_state(state))
    
    def _update_simulation_state(self, state: SimulationState) -> None:
        """
        更新仿真状态显示（在GUI线程中执行）
        
        Args:
            state: 仿真状态
        """
        # 更新画布显示
        self.canvas_view.update_simulation_state(state)
        
        # 更新状态栏显示仿真时间
        if state:
            hours = int(state.current_time // 3600)
            minutes = int((state.current_time % 3600) // 60)
            seconds = int(state.current_time % 60)
            time_str = f"仿真时间: {hours:02d}:{minutes:02d}:{seconds:02d}"
            self.status_bar.config(text=time_str)
            
            # 更新KPI仪表盘的时间戳（单位：分钟）
            if self.simulation_engine and self.simulation_engine.is_running and not self.simulation_engine.is_paused:
                # 仿真运行中且未暂停，更新时间戳
                timestamp_minutes = state.current_time / 60.0
                self.kpi_dashboard.update_timestamp(timestamp_minutes)
        
        # 更新KPI（如果有新的数据）
        # 这里可以添加实时KPI更新逻辑
        
        # 检查报警队列
        if self.simulation_engine:
            from queue import Queue
            while not self.simulation_engine.alert_queue.empty():
                alert = self.simulation_engine.alert_queue.get()
                self.alert_panel.add_alert(alert)
    
    def run(self) -> None:
        """
        运行主循环
        
        启动Tkinter的事件循环，程序开始运行
        """
        self.root.mainloop()
