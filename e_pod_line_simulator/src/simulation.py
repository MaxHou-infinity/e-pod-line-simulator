"""
仿真引擎层 - 基于SimPy的离散事件仿真

这个文件包含所有仿真相关的逻辑，包括：
- SimulationEngine: 仿真引擎核心类
- 瓶颈识别算法
- 资源浪费检测算法
- WIP监控逻辑

SimPy简介：
SimPy是一个离散事件仿真库，用于模拟系统中的事件流。
在产线仿真中，每个"物料加工完成"就是一个事件。

核心概念：
- Environment: 仿真环境，管理仿真时钟和事件队列
- Process: 仿真进程，用生成器函数实现（yield）
- Resource: 资源（如工人），可以被多个进程竞争使用
- Store: 存储（如WIP缓冲区），可以存储物品

仿真流程：
1. 创建SimPy环境
2. 为每个工序创建工作进程
3. 创建监控进程（瓶颈、WIP）
4. 运行仿真直到指定时间
5. 收集结果并返回
"""

import random
import simpy
from typing import List, Dict, Callable, Optional, Any
from queue import Queue, Empty
import threading
import time

from src.models import (
    BatchStatus,
    JobRole,
    ProductionLine,
    ProductionType,
    Station,
    Alert,
    SimulationState,
    SimulationResult,
    CollaborationType,
)


class SimulationEngine:
    """
    仿真引擎类 - 运行产线仿真并收集数据
    
    这是整个仿真系统的核心，负责：
    1. 初始化SimPy环境
    2. 启动各工序的仿真进程
    3. 监控瓶颈和WIP
    4. 收集仿真结果
    5. 通过回调函数通知GUI更新
    
    使用方式：
        engine = SimulationEngine(production_line)
        engine.set_callback(on_state_update)  # 设置更新回调
        engine.run(duration_hours=8, speed=16)  # 运行仿真
        results = engine.get_results()  # 获取结果
    """
    
    def __init__(self, production_line: ProductionLine):
        """
        初始化仿真引擎
        
        Args:
            production_line: 要仿真的产线对象
        """
        self.line = production_line  # 产线对象
        self.env = None  # SimPy环境，在run()方法中创建
        
        # 仿真状态
        self.is_running = False  # 是否正在运行
        self.is_paused = False  # 是否暂停
        self.speed = 1  # 仿真速度倍数
        
        # 统计数据
        self.station_outputs: Dict[str, int] = {}  # 各工序产出统计
        self.station_wips: Dict[str, int] = {}  # 各工序WIP统计
        self.total_output = 0  # 总产出
        
        # SimPy资源（在run()中初始化）
        self.station_resources: Dict[str, simpy.Resource] = {}  # 工序资源（工人）
        self.buffers: Dict[str, simpy.Store] = {}  # WIP缓冲区
        
        # 回调函数
        self.state_callback: Optional[Callable[[SimulationState], None]] = None
        
        # 报警队列
        self.alert_queue: Queue = Queue()
        # 外部事件注入队列（如切换事件），跨线程安全
        self.event_queue: Queue = Queue()
        # 报警完整记录（供报告导出与测试断言）
        self.alert_log: List[Alert] = []
        # WIP 时间序列采样（供报告导出）
        self.wip_samples: List[Dict[str, Any]] = []
        # 切换事件记录（供报告导出与测试断言）
        self.changeover_events: List[Dict[str, Any]] = []
        # V1.3：批次/质量/清洗结果
        self.batch_results: List[Dict[str, Any]] = []
        self.quality_results: List[Dict[str, Any]] = []
        self.cleaning_events: List[Dict[str, Any]] = []
        self._last_batch_recipe: Optional[str] = None
        self.random_seed: Optional[int] = None
    
    def set_callback(self, callback: Callable[[SimulationState], None]) -> None:
        """
        设置状态更新回调函数
        
        当仿真状态发生变化时，会调用这个函数通知GUI更新
        
        Args:
            callback: 回调函数，接收SimulationState参数
        """
        self.state_callback = callback

    def _emit_alert(self, alert: Alert) -> None:
        """记录报警：同时写入完整记录列表与 GUI 消费队列"""
        self.alert_log.append(alert)
        self.alert_queue.put(alert)

    def trigger_changeover(self, station_id: str, minutes: int = 45) -> bool:
        """
        触发指定工序的切换（口味更换）停机事件

        Args:
            station_id: 工序 ID
            minutes: 切换停机时长（分钟），默认 45

        Returns:
            bool: 是否成功触发
        """
        if minutes <= 0:
            raise ValueError("切换时长必须大于0分钟")

        station = self.line.get_station(station_id)
        if station is None:
            raise ValueError(f"工序不存在：{station_id}")

        event = {
            'type': 'changeover',
            'station_id': station_id,
            'minutes': int(minutes),
        }
        self.event_queue.put(event)

        timestamp_minutes = self.env.now / 60.0 if self.env else 0.0
        self.changeover_events.append({
            'time': self.env.now if self.env else 0.0,
            'station_id': station_id,
            'station_name': station.name,
            'minutes': int(minutes),
        })
        self._emit_alert(Alert(
            alert_type='changeover',
            severity='info',
            station_id=station_id,
            message=f"{station.name}开始切换，停机{int(minutes)}分钟",
            suggestion="切换完成后自动恢复生产",
            timestamp_minutes=timestamp_minutes,
        ))
        return True

    def _drain_events(self, station_id: str) -> List[Dict[str, Any]]:
        """
        从事件队列取出属于指定工序的切换事件，其余事件放回队列

        SimPy 进程为单线程执行，此方法在工序进程内调用是安全的；
        事件队列本身由 queue.Queue 保证跨线程安全。
        """
        events = []
        others = []
        while True:
            try:
                event = self.event_queue.get_nowait()
            except Empty:
                break
            if event.get('type') == 'changeover' and event.get('station_id') == station_id:
                events.append(event)
            else:
                others.append(event)
        for event in others:
            self.event_queue.put(event)
        return events

    def _batch_process(self, batch) -> simpy.events.Process:
        """
        批次过程（V1.3 烟油灌装）

        流程：调配 → 陈化 → 灌装 → QC → 放行；罐液位同步更新。
        """
        recipe = next((r for r in self.line.recipes if r.name == batch.recipe_name), None)
        if recipe is None:
            batch.status = BatchStatus.RELEASED
            self.batch_results.append({
                'batch_id': batch.id,
                'recipe_name': batch.recipe_name,
                'status': 'released',
                'error': '配方不存在',
                'start_time': self.env.now,
                'end_time': self.env.now,
                'yield_l': 0.0,
                'cycle_min': 0.0,
                'pass_rate': 0.0,
            })
            return

        # CIP/SIP 清洗切换：换配方时按配方清洗时长停机
        if (
            self._last_batch_recipe is not None
            and self._last_batch_recipe != recipe.name
            and recipe.clean_time_min > 0
        ):
            clean_start = self.env.now
            yield self.env.timeout(recipe.clean_time_min * 60)
            self.cleaning_events.append({
                'time': clean_start,
                'recipe_from': self._last_batch_recipe,
                'recipe_to': recipe.name,
                'clean_min': recipe.clean_time_min,
            })
        self._last_batch_recipe = recipe.name

        batch.status = BatchStatus.MIXING
        start_time = self.env.now
        yield self.env.timeout(recipe.mixing_time_min * 60)

        if recipe.aging_time_min > 0:
            batch.status = BatchStatus.AGING
            yield self.env.timeout(recipe.aging_time_min * 60)

        batch.status = BatchStatus.FILLING
        fill_seconds = recipe.batch_volume_l / recipe.filling_rate_l_per_h * 3600
        yield self.env.timeout(fill_seconds)

        batch.status = BatchStatus.QC
        yield self.env.timeout(recipe.qc_time_min * 60)

        yielded_l = recipe.batch_volume_l * recipe.yield_rate

        # 质量门：QC 化验按抽检比例与缺陷率判定
        pass_rate = 1.0
        qc_station = next(
            (s for s in self.line.stations if s.job_role == JobRole.QC_TECHNICIAN),
            None,
        )
        if qc_station and qc_station.sampling_rate > 0 and qc_station.defect_rate > 0:
            if self._rng.random() < qc_station.sampling_rate:
                if self._rng.random() < qc_station.defect_rate:
                    batch.status = BatchStatus.REWORK
                    batch.rework_count += 1
                    yield self.env.timeout(qc_station.rework_minutes * 60)
                    pass_rate = max(0.0, 1.0 - qc_station.defect_rate)
        self.quality_results.append({
            'time': self.env.now,
            'batch_id': batch.id,
            'pass_rate': round(pass_rate, 4),
            'rework_count': batch.rework_count,
        })

        batch.status = BatchStatus.RELEASED
        end_time = self.env.now
        batch.end_time = end_time
        batch.pass_rate = pass_rate

        # 罐液位更新（取第一个有空间的罐）
        for tank in self.line.tanks:
            if tank.current_level_l + yielded_l <= tank.capacity_l + 1e-6:
                tank.current_level_l += yielded_l
                break

        self.batch_results.append({
            'batch_id': batch.id,
            'recipe_name': batch.recipe_name,
            'status': 'released',
            'start_time': start_time,
            'end_time': end_time,
            'yield_l': round(yielded_l, 3),
            'cycle_min': round((end_time - start_time) / 60.0, 3),
            'pass_rate': pass_rate,
        })
    
    def run(self, duration_hours: float = 8.0, speed: int = 16) -> None:
        """
        运行仿真
        
        这是仿真的主入口，执行以下步骤：
        1. 创建SimPy环境
        2. 初始化资源（工人、缓冲区）
        3. 启动各工序进程
        4. 启动监控进程
        5. 运行仿真直到指定时间
        6. 收集结果
        
        Args:
            duration_hours: 仿真时长（小时），默认8小时（一个班次）
            speed: 仿真速度倍数，默认16倍（16x表示16倍速）
                   speed=1是实时，speed=16表示16倍速
        """
        # 初始化状态
        self.is_running = True
        self.is_paused = False
        self.speed = speed
        
        # 初始化统计数据
        self.station_outputs = {station.id: 0 for station in self.line.stations}
        self.station_wips = {station.id: 0 for station in self.line.stations}
        self.total_output = 0
        self.batch_results = []
        self.quality_results = []
        self.cleaning_events = []
        self._rng = random.Random(self.random_seed)

        # 步骤1：创建SimPy环境
        # Environment是SimPy的核心，管理仿真时钟和事件队列
        self.env = simpy.Environment()
        
        # 步骤2：初始化资源
        # Resource：代表工人，可以同时被多个进程使用（并联模式）
        # Store：代表WIP缓冲区，用于存储物料
        self._init_resources()
        
        # 步骤3：启动各工序的工作进程
        # 每个工序都有一个独立的工作进程，模拟物料加工
        self._spawn_station_processes()
        
        # 步骤4：启动监控进程
        # 监控瓶颈变化和WIP堆积
        self.env.process(self._monitor_bottleneck())
        self.env.process(self._monitor_wip())
        self.env.process(self._update_state_periodically())
        
        # 步骤5：运行仿真
        # 在单独的线程中运行，避免阻塞GUI主线程
        duration_seconds = duration_hours * 3600  # 转换为秒
        
        # 保存仿真参数
        self.duration_seconds = duration_seconds
        self.speed = speed
        
        # 在新线程中运行SimPy
        sim_thread = threading.Thread(
            target=self._run_simulation_thread,
            args=(duration_seconds, speed),
            daemon=True  # 守护线程，主程序退出时自动结束
        )
        sim_thread.start()
    
    def _init_resources(self) -> None:
        """
        初始化SimPy资源（工人和缓冲区）
        
        为每个工序创建：
        - Resource：代表工人资源（并联模式时容量=工人数，协同模式时容量=1）
        - Store：代表WIP缓冲区（用于工序间物料传递）
        """
        for station in self.line.stations:
            # 创建工人资源
            if station.collaboration_type == CollaborationType.PARALLEL:
                # 并联模式：资源容量 = 工人数，可以同时处理多个物料
                capacity = station.worker_count
            else:
                # 协同模式：资源容量 = 1，只能处理一个物料
                capacity = 1
            
            self.station_resources[station.id] = simpy.Resource(self.env, capacity=capacity)
            
            # 创建WIP缓冲区
            # Store用于存储物料，容量为buffer_capacity
            self.buffers[station.id] = simpy.Store(self.env, capacity=station.buffer_capacity)

    def _spawn_station_processes(self) -> None:
        """
        按协作模式启动工序进程

        - 并联：每名工人一个进程，产能 = 节拍 × 工位数（匹配 get_capacity）
        - 协同：单进程，多人共享（资源容量 1，自动排队）
        """
        for station in self.line.stations:
            if station.collaboration_type == CollaborationType.PARALLEL:
                count = max(1, station.worker_count)
            else:
                count = 1
            for _ in range(count):
                self.env.process(self._station_process(station))
    
    def _station_process(self, station: Station) -> simpy.events.Process:
        """
        工序工作进程（SimPy生成器函数）
        
        这是每个工序的核心逻辑，模拟物料加工过程：
        1. 从上游缓冲区获取物料（如果有上游）
        2. 请求工人资源（等待可用工人）
        3. 占用工人资源，开始加工
        4. 等待加工时间（process_time）
        5. 释放工人资源
        6. 将物料放入下游缓冲区（如果有下游）
        7. 更新统计数据
        
        这是SimPy的生成器函数，使用yield来暂停和恢复执行
        
        Args:
            station: 工序对象
            
        Yields:
            simpy.events: SimPy事件（timeout、request等）
        """
        # 获取资源引用
        resource = self.station_resources[station.id]
        
        # 获取缓冲区引用
        # 本工序的缓冲区用于接收上游物料
        input_buffer = self.buffers[station.id]
        
        # 找到下游工序的缓冲区（用于输出物料）
        downstream_buffer = None
        station_index = self.line.stations.index(station)
        if station_index < len(self.line.stations) - 1:
            # 如果不是最后一个工序，有下游
            downstream_station = self.line.stations[station_index + 1]
            downstream_buffer = self.buffers[downstream_station.id]
        
        # 无限循环，模拟持续的物料加工
        while True:
            # 检查是否有针对本工序的切换事件
            changeover_events = self._drain_events(station.id)
            if changeover_events:
                changeover = changeover_events[0]
                # 同工序的其余切换事件放回队列，按顺序继续执行
                for extra in changeover_events[1:]:
                    self.event_queue.put(extra)
                station.current_status = "changeover"
                yield self.env.timeout(float(changeover['minutes']) * 60)
                station.current_status = "idle"
                continue

            try:
                # 步骤1：从上游缓冲区获取物料（如果不是第一个工序）
                if station_index > 0:
                    # 有上游，需要等待物料
                    # get()会阻塞直到有物料可用
                    yield input_buffer.get()
                    # 更新WIP统计（取走一个物料，WIP-1）
                    self.station_wips[station.id] = len(input_buffer.items)
                else:
                    # 第一个工序，没有上游，直接开始加工
                    # 模拟物料源持续供应
                    pass
                
                # 步骤2：请求工人资源
                # request()会阻塞直到有可用工人
                # 在并联模式下，如果有多个工人，可以同时处理多个物料
                with resource.request() as req:
                    yield req  # 等待获得资源
                    
                    # 步骤3：开始加工，占用工人资源
                    station.current_status = "running"
                    
                    # 步骤4：等待加工时间
                    # timeout是SimPy的核心，用于模拟时间流逝
                    # process_time是实际加工时间，但需要考虑效率
                    # 实际时间 = 理论时间 / (OEE × efficiency)
                    # 机台节拍模式（尼古丁袋）使用 machine_takt，否则使用单颗耗时
                    effective_time = station.machine_takt if station.machine_takt else station.process_time
                    actual_process_time = effective_time / (station.oee * station.efficiency)
                    yield self.env.timeout(actual_process_time)
                    
                    # 步骤5：加工完成，释放资源（自动释放，with语句结束）
                    station.current_status = "idle"
                    
                    # 步骤6：将物料放入下游缓冲区
                    if downstream_buffer is not None:
                        # 如果不是最后一个工序，放入下游缓冲区
                        # put()会阻塞如果缓冲区满了（模拟堵塞）
                        try:
                            yield downstream_buffer.put("material")  # "material"是物料标识
                            # 更新下游WIP统计
                            if station_index < len(self.line.stations) - 1:
                                downstream_station = self.line.stations[station_index + 1]
                                self.station_wips[downstream_station.id] = len(downstream_buffer.items)
                        except simpy.Interrupt:
                            # 如果缓冲区满了，工序进入堵塞状态
                            station.current_status = "blocked"
                            continue
                    else:
                        # 最后一个工序，物料完成，直接计入产出
                        pass

                    # 步骤6.5：质量门（在线检测）
                    if station.sampling_rate > 0 and station.defect_rate > 0:
                        if self._rng.random() < station.sampling_rate:
                            if self._rng.random() < station.defect_rate:
                                station.current_status = "waiting"
                                yield self.env.timeout(station.rework_minutes * 60)
                                self.quality_results.append({
                                    'time': self.env.now,
                                    'station_id': station.id,
                                    'station_name': station.name,
                                    'defect': True,
                                    'rework_min': station.rework_minutes,
                                })
                                station.current_status = "idle"
                                continue
                    
                    # 步骤7：更新统计数据
                    self.station_outputs[station.id] += 1
                    self.total_output += 1
                    
            except simpy.Interrupt:
                # 处理中断（如暂停、停止）
                continue
    
    def _monitor_bottleneck(self) -> simpy.events.Process:
        """
        监控瓶颈进程
        
        定期检查瓶颈工序是否发生变化，如果变化则发出警报
        
        Yields:
            simpy.events: SimPy事件
        """
        last_bottleneck_id = None
        
        while True:
            # 每60秒检查一次（仿真时间）
            yield self.env.timeout(60)
            
            # 找出当前瓶颈
            bottleneck = self.line.find_bottleneck()
            if bottleneck is None:
                continue
            
            # 如果瓶颈发生变化，发出警报
            if bottleneck.id != last_bottleneck_id:
                # 计算从仿真开始经过的分钟数
                timestamp_minutes = self.env.now / 60.0
                alert = Alert(
                    alert_type="bottleneck",
                    severity="critical",
                    station_id=bottleneck.id,
                    message=f"瓶颈工序：{bottleneck.name}，产能：{bottleneck.get_capacity():.0f}颗/h",
                    suggestion=f"建议增加{bottleneck.name}的工人数量或提升OEE",
                    timestamp_minutes=timestamp_minutes
                )
                self._emit_alert(alert)
                last_bottleneck_id = bottleneck.id
    
    def _monitor_wip(self) -> simpy.events.Process:
        """
        监控WIP堆积进程
        
        检查各工序的WIP是否接近缓冲区容量，如果接近则发出警报
        
        Yields:
            simpy.events: SimPy事件
        """
        while True:
            # 每30秒检查一次（仿真时间）
            yield self.env.timeout(30)
            
            # 计算从仿真开始经过的分钟数
            timestamp_minutes = self.env.now / 60.0
            
            # 检查每个工序的WIP
            for station in self.line.stations:
                buffer = self.buffers[station.id]
                wip_count = len(buffer.items)
                utilization = wip_count / station.buffer_capacity if station.buffer_capacity > 0 else 0

                # 记录 WIP 时间序列采样（供报告导出）
                self.wip_samples.append({
                    'time': self.env.now,
                    'station_id': station.id,
                    'station_name': station.name,
                    'wip': wip_count,
                })
                
                # 如果WIP超过80%容量，发出警报
                if utilization >= 0.8:
                    alert = Alert(
                        alert_type="blockage",
                        severity="warning",
                        station_id=station.id,
                        message=f"{station.name}的WIP堆积：{wip_count}/{station.buffer_capacity}",
                        suggestion=f"建议增加{station.name}的下游产能或扩大缓冲区",
                        timestamp_minutes=timestamp_minutes
                    )
                    self._emit_alert(alert)
    
    def _update_state_periodically(self) -> simpy.events.Process:
        """
        定期更新状态并通知GUI
        
        这是GUI更新的关键，定期收集仿真状态并通过回调函数通知GUI
        根据仿真速度调整更新频率，1倍速时按真实时间更新
        
        Yields:
            simpy.events: SimPy事件
        """
        while True:
            # 根据仿真速度调整更新间隔
            # 1倍速：每1秒（真实时间）更新一次，对应1秒仿真时间
            # 16倍速：每1秒（真实时间）更新一次，对应16秒仿真时间
            # 这样在1倍速时，用户可以看到真实的时间流逝
            if self.speed == 1:
                update_interval = 1.0  # 1秒（仿真时间）
            else:
                update_interval = 10.0  # 其他速度下，每10秒（仿真时间）更新一次
            
            yield self.env.timeout(update_interval)
            
            # 如果GUI没有设置回调，跳过
            if self.state_callback is None:
                continue
            
            # 收集当前状态
            state = self._collect_state()
            
            # 调用回调函数，通知GUI更新
            # 注意：这里在SimPy线程中，需要切换到GUI线程
            # 实际实现中，应该使用队列传递状态
            if self.state_callback:
                try:
                    self.state_callback(state)
                except Exception as e:
                    # 捕获异常，避免影响仿真运行
                    print(f"回调函数执行错误：{e}")
    
    def _collect_state(self) -> SimulationState:
        """
        收集当前仿真状态
        
        将SimPy的仿真状态转换为SimulationState对象，用于GUI显示
        
        Returns:
            SimulationState: 当前仿真状态快照
        """
        # 构建各工序状态字典
        station_states = {}
        for station in self.line.stations:
            station_states[station.id] = {
                'status': station.current_status,
                'output': self.station_outputs.get(station.id, 0),
                'wip': self.station_wips.get(station.id, 0),
                'capacity': station.get_capacity()
            }
        
        # 找出瓶颈
        bottleneck = self.line.find_bottleneck()
        bottleneck_id = bottleneck.id if bottleneck else None
        
        # 创建状态对象
        state = SimulationState(
            current_time=self.env.now,
            station_states=station_states,
            total_output=self.total_output,
            bottleneck_id=bottleneck_id
        )
        
        return state
    
    def _run_simulation_thread(self, duration_seconds: float, speed: int = 1) -> None:
        """
        在单独线程中运行仿真
        
        这是为了避免阻塞GUI主线程
        根据仿真速度控制时间推进：
        - 1倍速：1秒真实时间 = 1秒仿真时间
        - 2倍速：1秒真实时间 = 2秒仿真时间
        - 8倍速：1秒真实时间 = 8秒仿真时间
        - 16倍速：1秒真实时间 = 16秒仿真时间
        
        Args:
            duration_seconds: 仿真时长（秒）
            speed: 仿真速度倍数（1/2/8/16）
        """
        try:
            # 运行SimPy仿真
            # 根据速度倍数控制时间推进
            if speed == 1:
                # 1倍速：1秒真实时间 = 1秒仿真时间
                start_time = time.time()
                last_sim_time = 0.0
                
                while self.env.now < duration_seconds and self.is_running:
                    if self.is_paused:
                        # 如果暂停，等待恢复
                        time.sleep(0.1)
                        start_time = time.time() - self.env.now  # 调整起始时间，保持同步
                        continue
                    
                    # 计算已经过的真实时间
                    elapsed_real_time = time.time() - start_time
                    
                    # 如果仿真时间落后于真实时间，需要推进
                    if elapsed_real_time > self.env.now:
                        # 每次推进1秒仿真时间
                        target_time = min(self.env.now + 1.0, duration_seconds)
                        
                        # 推进仿真到目标时间
                        if target_time > self.env.now:
                            try:
                                self.env.run(until=target_time)
                            except:
                                pass  # 忽略中断错误
                        
                        # 如果推进了1秒仿真时间，sleep 1秒真实时间
                        if self.env.now - last_sim_time >= 1.0:
                            time.sleep(1.0)  # sleep 1秒真实时间
                            last_sim_time = self.env.now
                    else:
                        # 如果仿真时间已经达到或超过真实时间，等待真实时间追上
                        time.sleep(0.1)
            else:
                # 加速模式：根据速度倍数控制时间推进
                # 例如：2倍速 = 1秒真实时间 = 2秒仿真时间
                #       8倍速 = 1秒真实时间 = 8秒仿真时间
                #       16倍速 = 1秒真实时间 = 16秒仿真时间
                start_time = time.time()
                last_update_time = 0.0
                
                while self.env.now < duration_seconds and self.is_running:
                    if self.is_paused:
                        # 如果暂停，等待恢复
                        time.sleep(0.1)
                        start_time = time.time() - self.env.now / speed  # 调整起始时间
                        continue
                    
                    # 计算已经过的真实时间
                    elapsed_real_time = time.time() - start_time
                    
                    # 计算应该推进到的仿真时间（基于真实时间和速度倍数）
                    # 例如：2倍速时，1秒真实时间 = 2秒仿真时间
                    target_sim_time = elapsed_real_time * speed
                    
                    # 如果仿真时间落后于目标时间，需要推进
                    if target_sim_time > self.env.now:
                        # 每次推进一个小步长（避免一次性推进太多）
                        step_size = 1.0  # 每次推进1秒仿真时间
                        target_time = min(self.env.now + step_size, duration_seconds, target_sim_time)
                        
                        # 推进仿真到目标时间
                        if target_time > self.env.now:
                            try:
                                self.env.run(until=target_time)
                            except:
                                pass  # 忽略中断错误
                        
                        # 控制更新频率：每推进step_size秒仿真时间，sleep step_size/speed秒真实时间
                        # 例如：2倍速时，推进2秒仿真时间，sleep 1秒真实时间
                        if self.env.now - last_update_time >= step_size:
                            sleep_time = step_size / speed  # 根据速度计算需要sleep的真实时间
                            time.sleep(sleep_time)
                            last_update_time = self.env.now
                    else:
                        # 如果仿真时间已经达到或超过目标时间，等待真实时间追上
                        time.sleep(0.1)
        except Exception as e:
            print(f"仿真运行错误：{e}")
        finally:
            # 仿真结束，更新状态
            self.is_running = False
    
    def pause(self) -> None:
        """
        暂停仿真
        
        暂停时，is_paused设为True，但is_running保持True
        这样可以通过resume()恢复仿真，而不需要重新创建引擎
        """
        self.is_paused = True
    
    def resume(self) -> None:
        """
        恢复仿真
        
        从暂停状态恢复，is_paused设为False
        仿真线程会继续运行
        """
        self.is_paused = False
    
    def stop(self) -> None:
        """
        停止仿真

        仿真循环按小步长推进（≤1 秒仿真时间），设置 is_running=False 后
        线程会在下一个循环检查时退出；SimPy Environment 本身没有
        interrupt 方法，因此无需也不能直接中断环境。
        """
        self.is_running = False
    
    def get_results(self) -> Dict[str, Any]:
        """
        获取仿真结果
        
        Returns:
            Dict: 包含仿真结果的字典
        """
        return {
            'total_output': self.total_output,
            'station_outputs': self.station_outputs.copy(),
            'station_wips': self.station_wips.copy(),
            'bottleneck': self.line.find_bottleneck()
        }

    def run_sync(self, duration_hours: float = 8.0) -> SimulationResult:
        """
        同步（headless）运行仿真

        不启动独立线程，直接运行 SimPy 环境到结束，返回聚合结果。
        用于自动化测试与报告导出，不依赖 GUI。

        Args:
            duration_hours: 仿真时长（小时）

        Returns:
            SimulationResult: 仿真结果聚合对象
        """
        self.is_running = True
        self.is_paused = False
        self.speed = 1

        self.station_outputs = {station.id: 0 for station in self.line.stations}
        self.station_wips = {station.id: 0 for station in self.line.stations}
        self.total_output = 0
        self.batch_results = []
        self.quality_results = []
        self.cleaning_events = []
        self._rng = random.Random(self.random_seed)

        self.env = simpy.Environment()
        self._init_resources()
        if self.line.production_type == ProductionType.LIQUID_FILLING:
            # 烟油：批量过程驱动
            for batch in self.line.batches:
                self.env.process(self._batch_process(batch))
        else:
            # 组装 / 尼古丁袋：工序进程驱动（袋装使用机台节拍）
            self._spawn_station_processes()
        self.env.process(self._monitor_bottleneck())
        self.env.process(self._monitor_wip())
        self.env.process(self._update_state_periodically())

        self.duration_seconds = duration_hours * 3600
        self.env.run(until=self.duration_seconds)
        self.is_running = False
        return self.build_result()

    def build_result(self) -> SimulationResult:
        """构建仿真结果聚合对象（用于报告导出与测试）"""
        return SimulationResult(
            line_name=self.line.name,
            duration_seconds=self.duration_seconds,
            total_output=self.total_output,
            station_outputs=self.station_outputs.copy(),
            station_wips=self.station_wips.copy(),
            kpis={
                'bottleneck_capacity': self.line.get_bottleneck_capacity(),
                'daily_output': self.line.calculate_daily_output(),
                'total_cost': self.line.calculate_total_cost(),
                'unit_cost': self.line.calculate_unit_cost(),
                'balance_rate': self.line.calculate_line_balance_rate(),
                'upph': self.line.calculate_upph(),
            },
            alerts=list(self.alert_log),
            wip_samples=list(self.wip_samples),
            changeover_events=list(self.changeover_events),
            batch_results=list(self.batch_results),
            quality_results=list(self.quality_results),
            cleaning_events=list(self.cleaning_events),
            labor_summary=dict(self.line.labor_config),
        )





def detect_waste(stations: List[Station], bottleneck_capacity: float, threshold: float = 1.2) -> List[Alert]:
    """
    检测资源浪费（产能过剩的工序）
    
    算法思路：
    1. 计算每个工序的实际产能
    2. 找出产能超过瓶颈产能 × threshold 的工序
    3. 对于并联工序，计算可以减少的工人数
    4. 生成浪费警报
    
    Args:
        stations: 工序列表
        bottleneck_capacity: 瓶颈产能（颗/小时）
        threshold: 阈值，默认1.2（超过瓶颈20%算浪费）
        
    Returns:
        List[Alert]: 浪费警报列表
    """
    alerts = []
    
    for station in stations:
        actual_capacity = station.get_capacity()
        
        # 如果产能超过阈值，判定为浪费
        if actual_capacity > bottleneck_capacity * threshold:
            # 计算最优人数（对于并联工序）
            if station.collaboration_type == CollaborationType.PARALLEL:
                # 计算满足瓶颈产能所需的最少人数
                theoretical_per_worker = 3600 / station.process_time * station.oee * station.efficiency
                optimal_workers = int(bottleneck_capacity / theoretical_per_worker) + 1
                
                # 如果可以减少人数
                if station.worker_count > optimal_workers:
                    reducible = station.worker_count - optimal_workers
                    daily_savings = reducible * 20.0 * 8  # 节省成本（元/天）
                    
                    alert = Alert(
                        alert_type="waste",
                        severity="warning",
                        station_id=station.id,
                        message=f"{station.name}产能过剩{(actual_capacity/bottleneck_capacity-1)*100:.0f}%",
                        suggestion=f"建议减少{reducible}人，可节约成本{daily_savings:.0f}元/天"
                    )
                    alerts.append(alert)
    
    return alerts
