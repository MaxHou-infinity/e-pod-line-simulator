# WIP（在制品）设置、单位和逻辑说明

## 1. WIP 单位

**WIP的单位是"颗"（物料数量）**

- WIP表示**在制品数量**，即等待在某工序前加工的物料数量
- 例如：WIP = 50，表示有50颗物料在等待加工
- 在GUI上显示为：`WIP: 50`（显示在连接线上）

---

## 2. WIP 设置

### 2.1 缓冲区容量（buffer_capacity）

**位置**：`Station`类的`buffer_capacity`字段

**默认值**：100颗

**含义**：每个工序的缓冲区可以暂存的最大物料数量

**代码位置**：
```python
# src/models.py
@dataclass
class Station:
    buffer_capacity: int = 100  # WIP缓冲区容量，工序间可以暂存的最大物料数
```

**作用**：
- 防止物料无限堆积
- 当缓冲区满时，上游工序会被阻塞（进入`blocked`状态）
- 模拟真实产线的缓冲区限制

### 2.2 当前WIP数量（wip_count）

**位置**：`Station`类的`wip_count`字段

**默认值**：0颗

**含义**：当前等待在该工序前加工的物料数量

**代码位置**：
```python
# src/models.py
@dataclass
class Station:
    wip_count: int = 0  # 当前WIP数量，等待在该工序前加工的物料数
```

**注意**：这个字段主要用于显示，实际WIP统计来自SimPy的Store缓冲区

---

## 3. WIP 逻辑

### 3.1 缓冲区创建

**位置**：`src/simulation.py` - `_init_resources()`方法

**逻辑**：
```python
# 为每个工序创建WIP缓冲区
self.buffers[station.id] = simpy.Store(
    self.env, 
    capacity=station.buffer_capacity  # 容量 = buffer_capacity
)
```

**说明**：
- 每个工序都有一个独立的缓冲区
- 缓冲区容量 = `station.buffer_capacity`（默认100颗）
- 使用SimPy的`Store`实现，自动管理物料存储

---

### 3.2 WIP 统计逻辑

**位置**：`src/simulation.py` - `_station_process()`方法

#### 3.2.1 从上游取物料

**代码**：
```python
# 如果不是第一个工序，从上游缓冲区取物料
if station_index > 0:
    yield input_buffer.get()  # 从缓冲区取一个物料
    # 更新WIP统计（取走一个物料，WIP-1）
    self.station_wips[station.id] = len(input_buffer.items)
```

**逻辑**：
1. 工序从自己的缓冲区（`input_buffer`）取物料
2. 取走一个物料后，更新WIP统计
3. WIP = `len(buffer.items)`（缓冲区中剩余的物料数）

**注意**：
- WIP统计的是**当前工序缓冲区中的物料数**
- 取走物料后，WIP减少
- 如果缓冲区为空，`get()`会阻塞，直到有物料

---

#### 3.2.2 向下游放物料

**代码**：
```python
# 将物料放入下游缓冲区
if downstream_buffer is not None:
    yield downstream_buffer.put("material")  # 放入一个物料
    # 更新下游WIP统计
    downstream_station = self.line.stations[station_index + 1]
    self.station_wips[downstream_station.id] = len(downstream_buffer.items)
```

**逻辑**：
1. 工序加工完成后，将物料放入下游工序的缓冲区
2. 放入物料后，更新下游工序的WIP统计
3. 下游WIP = `len(downstream_buffer.items)`（下游缓冲区中的物料数）

**注意**：
- 如果下游缓冲区满了，`put()`会阻塞，工序进入`blocked`状态
- 这模拟了真实产线中的堵塞情况

---

### 3.3 WIP 显示位置

**位置**：`src/gui_canvas.py` - `_draw_connection_curved()`方法

**代码**：
```python
# 在连接线中间显示WIP数量
wip_x = (start_x + end_x) // 2
wip_y = (start_y + end_y) // 2 - 20
wip_id = self.create_text(
    wip_x, wip_y,
    text="WIP: 0",
    font=('Arial', 9),
    fill='blue',
    tags=(f"wip_{from_station_id}_{to_station_id}", "wip")
)
```

**说明**：
- WIP显示在**连接线的中间位置**
- 显示格式：`WIP: X`（X为数字）
- 显示的是**下游工序的WIP数量**（即从上游工序到下游工序之间等待的物料数）

---

### 3.4 WIP 更新逻辑

**位置**：`src/gui_canvas.py` - `update_simulation_state()`方法

**代码**：
```python
# 更新WIP显示
for i in range(len(self.production_line.stations) - 1):
    from_station = self.production_line.stations[i]
    to_station = self.production_line.stations[i + 1]
    key = f"{from_station.id}_{to_station.id}"
    
    if key in self.wip_labels:
        wip = state.station_states.get(to_station.id, {}).get('wip', 0)
        self.itemconfig(self.wip_labels[key], text=f"WIP: {wip}")
```

**逻辑**：
- 从`SimulationState`中获取每个工序的WIP数据
- 更新连接线上的WIP显示
- 显示的是下游工序的WIP（即连接线终点工序的WIP）

---

### 3.5 WIP 监控和报警

**位置**：`src/simulation.py` - `_monitor_wip()`方法

**代码**：
```python
def _monitor_wip(self) -> simpy.events.Process:
    """监控WIP堆积进程"""
    while True:
        # 每30秒检查一次（仿真时间）
        yield self.env.timeout(30)
        
        # 检查每个工序的WIP
        for station in self.line.stations:
            buffer = self.buffers[station.id]
            wip_count = len(buffer.items)  # 当前WIP数量
            utilization = wip_count / station.buffer_capacity  # 利用率
            
            # 如果WIP超过80%容量，发出警报
            if utilization >= 0.8:
                alert = Alert(
                    alert_type="blockage",
                    severity="warning",
                    station_id=station.id,
                    message=f"{station.name}的WIP堆积：{wip_count}/{station.buffer_capacity}",
                    suggestion=f"建议增加{station.name}的下游产能或扩大缓冲区"
                )
```

**逻辑**：
1. **监控频率**：每30秒（仿真时间）检查一次
2. **计算方法**：
   - WIP数量 = `len(buffer.items)`（缓冲区中的物料数）
   - 利用率 = WIP数量 / 缓冲区容量
3. **报警条件**：利用率 ≥ 80%（即WIP ≥ 80% × buffer_capacity）
4. **报警内容**：
   - 显示当前WIP和容量：`WIP堆积：X/Y`
   - 提供优化建议：增加下游产能或扩大缓冲区

**示例**：
- 如果`buffer_capacity = 100`，WIP = 80，则利用率 = 80%，触发报警
- 报警消息：`注油的WIP堆积：80/100`

---

## 4. WIP 数据流

### 4.1 物料流向

```
物料源 → 工序1 → [缓冲区1] → 工序2 → [缓冲区2] → 工序3 → 成品
              WIP1          WIP2
```

**说明**：
- 每个工序加工完成后，将物料放入下游缓冲区
- WIP显示在连接线上，表示下游缓冲区中的物料数
- 例如：`WIP: 50`表示有50颗物料在等待工序2加工

---

### 4.2 WIP 统计位置

**在代码中，WIP统计存储在以下位置**：

1. **SimPy缓冲区**：`self.buffers[station.id].items`（实际存储）
2. **统计字典**：`self.station_wips[station.id]`（用于快速查询）
3. **状态对象**：`SimulationState.station_states[station_id]['wip']`（用于GUI显示）

---

## 5. WIP 相关配置

### 5.1 如何修改缓冲区容量

**方法1：通过代码修改**
```python
station.buffer_capacity = 200  # 修改为200颗
```

**方法2：通过StationDialog添加工序时设置**
- 目前StationDialog没有提供缓冲区容量设置
- 默认使用`buffer_capacity = 100`

**建议**：
- 可以根据实际需求调整`buffer_capacity`
- 容量太小：容易造成堵塞，上游工序经常被阻塞
- 容量太大：浪费空间，可能导致物料堆积过多

---

### 5.2 WIP 监控阈值

**当前设置**：80%利用率触发报警

**位置**：`src/simulation.py` - `_monitor_wip()`方法

```python
if utilization >= 0.8:  # 80%阈值
```

**可以调整的阈值**：
- 如果设置为`0.7`：更早触发报警（更敏感）
- 如果设置为`0.9`：更晚触发报警（更宽松）

---

## 6. WIP 单位总结

| 项目 | 单位 | 说明 |
|------|------|------|
| **WIP数量** | 颗 | 等待加工的物料数量 |
| **缓冲区容量** | 颗 | 缓冲区可存储的最大物料数 |
| **WIP利用率** | 百分比 | WIP数量 / 缓冲区容量 |
| **报警阈值** | 80% | 利用率超过80%时触发报警 |

---

## 7. 代码位置总结

| 功能 | 文件 | 方法/位置 |
|------|------|-----------|
| **缓冲区容量定义** | `src/models.py` | `Station.buffer_capacity` |
| **缓冲区创建** | `src/simulation.py` | `_init_resources()` |
| **WIP统计** | `src/simulation.py` | `_station_process()` |
| **WIP监控** | `src/simulation.py` | `_monitor_wip()` |
| **WIP显示** | `src/gui_canvas.py` | `_draw_connection_curved()` |
| **WIP更新** | `src/gui_canvas.py` | `update_simulation_state()` |

---

## 8. 常见问题

### Q1: WIP显示为0，但实际有物料在等待？
**A**: 检查仿真是否正在运行，WIP会在仿真过程中动态更新。

### Q2: WIP超过缓冲区容量会发生什么？
**A**: 不会超过容量。SimPy的Store会阻塞`put()`操作，直到有空间。上游工序会进入`blocked`状态。

### Q3: 如何增加缓冲区容量？
**A**: 修改`Station.buffer_capacity`字段，或扩展StationDialog添加容量设置功能。

### Q4: WIP报警阈值可以调整吗？
**A**: 可以，修改`_monitor_wip()`方法中的`utilization >= 0.8`条件。
