"""
GUI画布视图 - 2D产线可视化

这个文件包含画布视图类，负责：
1. 绘制产线布局（工序节点、连接线）
2. 显示实时状态（颜色、数值）
3. 物料流动动画
4. 交互操作（双击编辑、拖拽等）

Canvas绘制原理：
- Tkinter的Canvas是2D绘图画布
- 使用create_rectangle、create_text等绘制图形
- 使用itemconfig更新已有图形
- 使用tags管理图形元素
"""

import tkinter as tk
from typing import Optional, Dict, Any, List, Callable

from src.models import ProductionLine, Station, SimulationState
from src.utils import get_status_color, CANVAS_WIDTH, CANVAS_HEIGHT, STATION_WIDTH, STATION_HEIGHT


class CanvasView(tk.Canvas):
    """
    画布视图类 - 2D产线可视化
    
    继承自tk.Canvas，提供产线的2D可视化功能
    
    绘制内容：
    - 工序节点：矩形框，显示工序信息
    - 连接线：箭头，表示物料流向
    - WIP显示：数字，显示在制品数量
    - 物料粒子：小圆点，模拟物料流动
    
    使用方式：
        canvas = CanvasView(parent, width=1000, height=500)
        canvas.update_production_line(production_line)
    """
    
    def __init__(
        self,
        parent,
        width: int = CANVAS_WIDTH,
        height: int = CANVAS_HEIGHT,
        on_reorder: Optional[Callable[[List[str]], None]] = None,
        on_station_edit: Optional[Callable[[str], None]] = None,
        on_station_select: Optional[Callable[[str], None]] = None,
        on_station_menu: Optional[Callable[[str, int, int], None]] = None,
        **kwargs
    ):
        """
        初始化画布视图
        
        Args:
            parent: 父组件
            width: 画布宽度（像素）
            height: 画布高度（像素）
        """
        super().__init__(parent, width=width, height=height, bg='white', **kwargs)
        
        # 产线数据
        self.production_line: Optional[ProductionLine] = None
        self.simulation_state: Optional[SimulationState] = None

        # 交互回调
        self.on_reorder = on_reorder
        self.on_station_edit = on_station_edit
        self.on_station_select = on_station_select
        self.on_station_menu = on_station_menu
        
        # 图形元素存储（用于更新）
        self.station_rects: Dict[str, int] = {}  # 工序矩形ID
        self.station_texts: Dict[str, List[int]] = {}  # 工序文本ID列表
        self.connection_lines: Dict[str, int] = {}  # 连接线ID
        self.wip_labels: Dict[str, int] = {}  # WIP标签ID
        self.station_positions: Dict[str, tuple] = {}  # 工序中心坐标

        # 拖拽状态
        self._drag_station_id: Optional[str] = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_last_x = 0
        self._drag_last_y = 0
        self._drag_total_dx = 0
        self._drag_total_dy = 0
        self._drag_moved = False
        
        # 布局参数
        self.station_spacing = 200  # 工序间距（像素）
        self.station_y = height // 2  # 工序Y坐标（居中）
        self.start_x = 100  # 起始X坐标
        self.station_row_height = 150  # 每行工序的垂直间距（像素）
        self.max_stations_per_row = 0  # 每行最大工序数（自动计算）
        
        # 绑定事件
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_move)
        self.bind("<ButtonRelease-1>", self._on_drag_end)
        self.bind("<Button-3>", self._on_right_click)
        
        # 绑定窗口大小变化事件（当画布大小变化时重新布局）
        self.bind("<Configure>", self._on_canvas_resize)
    
    def update_production_line(self, production_line: ProductionLine) -> None:
        """
        更新产线显示
        
        当产线数据变化时，重新绘制整个画布
        支持蛇形布局：当工序超出画布宽度时，自动换行显示
        
        Args:
            production_line: 产线对象
        """
        self.production_line = production_line
        
        # 清空画布
        self.delete("all")
        self.station_rects.clear()
        self.station_texts.clear()
        self.connection_lines.clear()
        self.wip_labels.clear()
        self.station_positions.clear()
        
        if not production_line or not production_line.stations:
            return
        
        # 计算每行最大工序数（基于画布宽度）
        # 使用实际画布宽度，而不是固定值
        canvas_width = self.winfo_reqwidth()  # 请求的宽度（实际可用宽度）
        if canvas_width <= 1:  # 如果画布还没有初始化，使用当前画布宽度
            canvas_width = self.winfo_width()
        if canvas_width <= 1:  # 如果还是无效，使用默认宽度
            canvas_width = CANVAS_WIDTH
        
        available_width = canvas_width - 2 * self.start_x  # 可用宽度（减去左右边距）
        self.max_stations_per_row = max(1, int(available_width / self.station_spacing))
        
        # 计算需要多少行（蛇形布局）
        num_stations = len(production_line.stations)
        num_rows = (num_stations + self.max_stations_per_row - 1) // self.max_stations_per_row
        
        # 计算起始Y坐标（居中显示所有行）
        # 使用实际画布高度
        canvas_height = self.winfo_reqheight()  # 请求的高度（实际可用高度）
        if canvas_height <= 1:
            canvas_height = self.winfo_height()
        if canvas_height <= 1:
            canvas_height = CANVAS_HEIGHT
        
        total_height = (num_rows - 1) * self.station_row_height
        start_y = (canvas_height - total_height) // 2
        start_y = max(50, start_y)  # 确保至少距离顶部50像素
        
        # 蛇形布局：先计算所有工序的位置
        station_positions = {}  # 存储每个工序的坐标
        
        # 第一步：计算所有工序的位置（不绘制）
        # 蛇形布局逻辑：
        # - 偶数行（0, 2, 4...）：从左到右，col = 0, 1, 2, ...
        # - 奇数行（1, 3, 5...）：从右到左，col = max-1, max-2, ..., 0
        for i, station in enumerate(production_line.stations):
            # 计算当前工序所在的行和列（在行内的位置）
            row = i // self.max_stations_per_row
            col_in_row = i % self.max_stations_per_row  # 在行内的列索引（0-based）
            
            # 如果是奇数行，需要反向排列（蛇形效果）
            if row % 2 == 1:
                # 奇数行：从右到左
                # 例如：如果max_stations_per_row=4，col_in_row=0,1,2,3
                # 应该映射为：3,2,1,0
                actual_col = self.max_stations_per_row - 1 - col_in_row
            else:
                # 偶数行：从左到右
                # 例如：如果max_stations_per_row=4，col_in_row=0,1,2,3
                # 应该映射为：0,1,2,3
                actual_col = col_in_row
            
            # 计算坐标
            x = self.start_x + actual_col * self.station_spacing
            y = start_y + row * self.station_row_height
            
            # 保存位置
            station_positions[station.id] = (x, y)
        self.station_positions = station_positions
        
        # 第二步：绘制所有工序节点
        for station in production_line.stations:
            pos = station_positions[station.id]
            self._draw_station(station, pos[0], pos[1])
        
        # 第三步：按顺序绘制连接线（确保箭头方向正确）
        for i in range(len(production_line.stations) - 1):
            current_station = production_line.stations[i]
            next_station = production_line.stations[i + 1]
            
            current_pos = station_positions[current_station.id]
            next_pos = station_positions[next_station.id]
            
            # 绘制连接线（从当前工序到下一个工序）
            self._draw_connection_curved(current_station.id, next_station.id, current_pos, next_pos)
    
    def _draw_station(self, station: Station, x: int, y: int) -> None:
        """
        绘制一个工序节点
        
        Args:
            station: 工序对象
            x: X坐标
            y: Y坐标（中心点）
        """
        # 计算矩形坐标
        rect_x1 = x - STATION_WIDTH // 2
        rect_y1 = y - STATION_HEIGHT // 2
        rect_x2 = x + STATION_WIDTH // 2
        rect_y2 = y + STATION_HEIGHT // 2
        
        # 获取状态颜色
        color = get_status_color(station.current_status)
        
        # 绘制矩形（工序节点）
        rect_id = self.create_rectangle(
            rect_x1, rect_y1, rect_x2, rect_y2,
            fill=color,
            outline='black',
            width=2,
            tags=(f"station_{station.id}", "station")  # 使用tags便于管理
        )
        self.station_rects[station.id] = rect_id
        
        # 绘制文本信息
        text_ids = []
        
        # 工序名称（第一行）
        text_id1 = self.create_text(
            x, y - 25,
            text=station.name,
            font=('Arial', 12, 'bold'),
            tags=(f"station_{station.id}", "station")
        )
        text_ids.append(text_id1)
        
        # 工人数量（第二行）
        text_id2 = self.create_text(
            x, y - 5,
            text=f"👥 {station.worker_count}人",
            font=('Arial', 10),
            tags=(f"station_{station.id}", "station")
        )
        text_ids.append(text_id2)
        
        # 产能（第三行）
        capacity = station.get_capacity()
        text_id3 = self.create_text(
            x, y + 15,
            text=f"⚡ {capacity:.0f} 颗/h",
            font=('Arial', 10),
            tags=(f"station_{station.id}", "station")
        )
        text_ids.append(text_id3)
        
        # 负荷率（第四行）
        if self.production_line:
            bottleneck_capacity = self.production_line.get_bottleneck_capacity()
            utilization = station.get_utilization(bottleneck_capacity)
            text_id4 = self.create_text(
                x, y + 35,
                text=f"📊 {utilization:.0%}",
                font=('Arial', 10),
                tags=(f"station_{station.id}", "station")
            )
            text_ids.append(text_id4)
        
        self.station_texts[station.id] = text_ids
    
    def _draw_connection_curved(self, from_station_id: str, to_station_id: str, pos1: tuple, pos2: tuple) -> None:
        """
        绘制连接线（支持曲线，用于蛇形布局）
        
        优化点：
        1. 连接线从节点边缘开始，不穿过节点
        2. 根据方向确定连接点（左/右/上/下边缘）
        3. 跨行时使用平滑曲线
        
        Args:
            from_station_id: 上游工序ID
            to_station_id: 下游工序ID
            pos1: 起始位置 (x, y) - 节点中心
            pos2: 结束位置 (x, y) - 节点中心
        """
        x1, y1 = pos1  # 上游工序中心
        x2, y2 = pos2  # 下游工序中心
        
        # 判断连接方向，确定连接点位置
        # 计算方向向量
        dx = x2 - x1
        dy = y2 - y1
        
        # 确定连接点（从节点边缘开始，避免穿过节点）
        # 根据方向确定从哪个边缘连接
        edge_offset_x = STATION_WIDTH // 2 + 5  # 边缘偏移量（多加5像素避免贴边）
        edge_offset_y = STATION_HEIGHT // 2 + 5
        
        if abs(dx) > abs(dy):
            # 主要是水平方向
            if dx > 0:
                # 从左到右：从右边缘连接到左边缘
                start_x = x1 + edge_offset_x
                start_y = y1
                end_x = x2 - edge_offset_x
                end_y = y2
            else:
                # 从右到左：从左边缘连接到右边缘
                start_x = x1 - edge_offset_x
                start_y = y1
                end_x = x2 + edge_offset_x
                end_y = y2
        else:
            # 主要是垂直方向
            if dy > 0:
                # 从上到下：从下边缘连接到上边缘
                start_x = x1
                start_y = y1 + edge_offset_y
                end_x = x2
                end_y = y2 - edge_offset_y
            else:
                # 从下到上：从上边缘连接到下边缘
                start_x = x1
                start_y = y1 - edge_offset_y
                end_x = x2
                end_y = y2 + edge_offset_y
        
        # 判断是否需要绘制曲线（跨行时）
        if abs(y2 - y1) > STATION_HEIGHT // 2:  # 跨行，需要曲线
            # 计算控制点，使曲线更平滑
            # 使用二次贝塞尔曲线，控制点在中间位置
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            
            # 创建平滑的曲线路径
            points = []
            num_points = 30  # 曲线平滑度（增加点数使曲线更平滑）
            
            for i in range(num_points + 1):
                t = i / num_points
                # 二次贝塞尔曲线公式
                x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * mid_x + t ** 2 * end_x
                y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * mid_y + t ** 2 * end_y
                points.extend([x, y])
            
            # 绘制曲线
            line_id = self.create_line(
                *points,
                fill='gray',
                width=2,
                smooth=True,  # 平滑曲线
                tags=(f"connection_{from_station_id}_{to_station_id}", "connection")
            )
            
            # 在终点绘制箭头（计算箭头方向）
            arrow_length = 15
            arrow_width = 5
            
            # 计算箭头方向（指向下游工序）
            arrow_dx = end_x - points[-2]
            arrow_dy = end_y - points[-3]
            arrow_len = (arrow_dx ** 2 + arrow_dy ** 2) ** 0.5
            
            if arrow_len > 0:
                # 归一化方向向量
                arrow_dx = arrow_dx / arrow_len * arrow_length
                arrow_dy = arrow_dy / arrow_len * arrow_length
                
                # 计算箭头两个端点（垂直于箭头方向）
                perp_x = -arrow_dy / arrow_len * arrow_width
                perp_y = arrow_dx / arrow_len * arrow_width
                
                arrow_id = self.create_line(
                    end_x - arrow_dx + perp_x, end_y - arrow_dy + perp_y,
                    end_x, end_y,
                    end_x - arrow_dx - perp_x, end_y - arrow_dy - perp_y,
                    fill='gray',
                    width=2,
                    tags=(f"connection_{from_station_id}_{to_station_id}", "connection")
                )
        else:
            # 同一行或同一列，绘制直线
            line_id = self.create_line(
                start_x, start_y,
                end_x, end_y,
                fill='gray',
                width=2,
                arrow=tk.LAST,  # 在终点绘制箭头
                arrowshape=(10, 12, 3),
                tags=(f"connection_{from_station_id}_{to_station_id}", "connection")
            )
        
        self.connection_lines[f"{from_station_id}_{to_station_id}"] = line_id
        
        # 智能定位WIP数量，避免覆盖箭头
        # 计算连接线的主方向
        abs_dx = abs(end_x - start_x)
        abs_dy = abs(end_y - start_y)
        
        if abs_dy > abs_dx:  # 垂直方向连接（包括曲线连接）
            # 垂直连接，WIP显示在连接线旁边
            # 计算中间点
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            
            # WIP显示在连接线右侧，避免覆盖箭头
            wip_x = mid_x + 20  # 向右偏移20像素
            wip_y = mid_y
        else:  # 水平方向连接
            # 水平连接，WIP显示在连接线上方，距离连接线有一定间距
            wip_x = (start_x + end_x) // 2
            wip_y = (start_y + end_y) // 2 - 25  # 向上偏移25像素，增加间距
        
        wip_id = self.create_text(
            wip_x, wip_y,
            text="WIP: 0",
            font=('Arial', 9),
            fill='blue',
            tags=(f"wip_{from_station_id}_{to_station_id}", "wip")
        )
        self.wip_labels[f"{from_station_id}_{to_station_id}"] = wip_id
    
    def update_simulation_state(self, state: SimulationState) -> None:
        """
        更新仿真状态显示
        
        当仿真运行时，定期调用此方法更新显示
        只更新变化的部分，而不是重绘整个画布（性能优化）
        
        Args:
            state: 仿真状态对象
        """
        self.simulation_state = state
        
        if not self.production_line:
            return
        
        # 更新各工序的状态
        for station in self.production_line.stations:
            station_state = state.station_states.get(station.id, {})
            
            # 更新状态颜色
            status = station_state.get('status', 'idle')
            color = get_status_color(status)
            
            # 更新矩形颜色
            if station.id in self.station_rects:
                self.itemconfig(self.station_rects[station.id], fill=color)
            
            # 更新产能文本（如果有变化）
            if station.id in self.station_texts and len(self.station_texts[station.id]) >= 3:
                capacity = station_state.get('capacity', station.get_capacity())
                self.itemconfig(
                    self.station_texts[station.id][2],
                    text=f"⚡ {capacity:.0f} 颗/h"
                )
        
        # 更新WIP显示
        for i in range(len(self.production_line.stations) - 1):
            from_station = self.production_line.stations[i]
            to_station = self.production_line.stations[i + 1]
            
            key = f"{from_station.id}_{to_station.id}"
            if key in self.wip_labels:
                wip = state.station_states.get(to_station.id, {}).get('wip', 0)
                self.itemconfig(self.wip_labels[key], text=f"WIP: {wip}")
    
    def highlight_station(self, station_id: str) -> None:
        """
        高亮显示指定工序
        
        Args:
            station_id: 工序ID
        """
        # 先取消所有高亮
        for station in self.production_line.stations if self.production_line else []:
            if station.id in self.station_rects:
                self.itemconfig(self.station_rects[station.id], outline='black', width=2)
        
        # 高亮指定工序
        if station_id in self.station_rects:
            self.itemconfig(self.station_rects[station_id], outline='red', width=4)
    
    def _on_double_click(self, event: tk.Event) -> None:
        """
        双击事件处理
        
        双击工序节点时，触发编辑对话框
        
        Args:
            event: 鼠标事件
        """
        station_id = self._station_id_at(event.x, event.y)
        if station_id and self.on_station_edit:
            self.on_station_edit(station_id)

    def _station_id_at(self, x: int, y: int) -> Optional[str]:
        """获取坐标处的工序 ID（通过 Canvas tags 查找）"""
        items = self.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        if not items:
            items = [self.find_closest(x, y)[0]]
        for item in items:
            for tag in self.gettags(item):
                if tag.startswith("station_"):
                    return tag.replace("station_", "")
        return None

    def _on_drag_start(self, event: tk.Event) -> None:
        """拖拽开始：记录被拖动的工序与起始位置"""
        station_id = self._station_id_at(event.x, event.y)
        self._drag_station_id = station_id
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._drag_last_x = event.x
        self._drag_last_y = event.y
        self._drag_total_dx = 0
        self._drag_total_dy = 0
        self._drag_moved = False

    def _on_drag_move(self, event: tk.Event) -> None:
        """拖拽移动：移动工序节点及其文本，提供视觉反馈"""
        if not self._drag_station_id:
            return
        dx = event.x - self._drag_last_x
        dy = event.y - self._drag_last_y
        self._drag_last_x = event.x
        self._drag_last_y = event.y
        self._drag_total_dx += dx
        self._drag_total_dy += dy
        if abs(self._drag_total_dx) > 5 or abs(self._drag_total_dy) > 5:
            self._drag_moved = True
        self.move(f"station_{self._drag_station_id}", dx, dy)

    def _on_drag_end(self, event: tk.Event) -> None:
        """拖拽结束：若发生位移则计算新顺序并触发重排回调"""
        station_id = self._drag_station_id
        moved = self._drag_moved
        self._drag_station_id = None

        if not station_id or not moved or not self.on_reorder:
            # 未发生拖拽视为单击选择
            if station_id and not moved and self.on_station_select:
                self.on_station_select(station_id)
            return

        if station_id not in self.station_positions or not self.production_line:
            return

        old_x, old_y = self.station_positions[station_id]
        final_x = old_x + self._drag_total_dx
        final_y = old_y + self._drag_total_dy

        # 找到距离拖拽终点最近的其它工序
        nearest_id = None
        nearest_dist = float("inf")
        for other_id, (ox, oy) in self.station_positions.items():
            if other_id == station_id:
                continue
            dist = (final_x - ox) ** 2 + (final_y - oy) ** 2
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_id = other_id

        if nearest_id is None:
            return

        order_ids = [s.id for s in self.production_line.stations]
        current_index = order_ids.index(station_id)
        target_index = order_ids.index(nearest_id)

        # 将工序移动到目标位置（模拟插入）
        order_ids.pop(current_index)
        order_ids.insert(target_index, station_id)

        if order_ids != [s.id for s in self.production_line.stations]:
            self.on_reorder(order_ids)

    def _on_right_click(self, event: tk.Event) -> None:
        """右键菜单：弹出工序操作菜单"""
        station_id = self._station_id_at(event.x, event.y)
        if station_id and self.on_station_menu:
            self.on_station_menu(station_id, event.x_root, event.y_root)
    
    def _on_canvas_resize(self, event: tk.Event) -> None:
        """
        画布大小变化事件处理
        
        当画布大小变化时（窗口调整大小），重新计算布局并重绘
        
        Args:
            event: Configure事件，包含新的画布大小信息
        """
        # 只有当画布实际大小发生变化时才重绘
        # 避免初始化时的多次重绘
        if event.width <= 1 or event.height <= 1:
            return
        
        # 如果已有产线数据，重新绘制
        if self.production_line:
            # 延迟重绘，避免频繁触发（防抖）
            # 使用after_idle确保在事件处理完成后重绘
            self.after_idle(self._redraw_production_line)
    
    def _redraw_production_line(self) -> None:
        """
        重新绘制产线（内部方法，用于窗口大小变化时）
        
        这个方法与update_production_line类似，但专门用于窗口大小变化时的重绘
        """
        if not self.production_line:
            return
        
        # 重新绘制产线（会重新计算布局）
        self.update_production_line(self.production_line)
        
        # 如果有仿真状态，也更新状态显示
        if self.simulation_state:
            self.update_simulation_state(self.simulation_state)
