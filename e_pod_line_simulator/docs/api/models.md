# 数据模型API文档

## 1. 概述

数据模型层定义了产线仿真系统中的所有核心数据结构，包括工序、产线、报警等。这些模型类负责存储数据，提供基本的数据操作方法，并支持JSON序列化和反序列化。

## 2. 核心类

### 2.1 CollaborationType（枚举）

协作模式枚举类，定义工序的两种工作模式：

| 枚举值 | 字符串值 | 描述 |
|--------|----------|------|
| PARALLEL | "parallel" | 并联模式，多人同时加工不同物料，产能可以叠加 |
| COLLABORATIVE | "collaborative" | 协同模式，多人共同完成一个物料，产能不叠加 |

### 2.2 Station（工序模型）

代表产线上的一个加工工序，包含工序的所有信息。

#### 构造函数

```python
Station(id: str, name: str, process_time: float, worker_count: int, collaboration_type: CollaborationType = CollaborationType.PARALLEL, oee: float = 0.85, efficiency: float = 0.95, changeover_time: int = 45, buffer_capacity: int = 100, current_status: str = "idle", wip_count: int = 0, total_output: int = 0)
```

#### 主要属性

| 属性名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| id | str | 必填 | 工序唯一标识符 |
| name | str | 必填 | 工序名称 |
| process_time | float | 必填 | 单颗耗时（秒） |
| worker_count | int | 必填 | 工人数量 |
| collaboration_type | CollaborationType | PARALLEL | 协作模式 |
| oee | float | 0.85 | 设备综合效率（0-1） |
| efficiency | float | 0.95 | 人员效率（0-1） |
| changeover_time | int | 45 | 切换时间（分钟） |
| buffer_capacity | int | 100 | 缓冲区容量 |
| current_status | str | "idle" | 当前状态 |
| wip_count | int | 0 | 当前WIP数量 |
| total_output | int | 0 | 累计产出 |

#### 主要方法

##### get_capacity()

```python
def get_capacity(self) -> float:
    """
    计算工序的实际产能（颗/小时）
    
    Returns:
        float: 实际产能，单位：颗/小时
    """
```

##### get_utilization(bottleneck_capacity: float)

```python
def get_utilization(self, bottleneck_capacity: float) -> float:
    """
    计算工序的负荷率（利用率）
    
    Args:
        bottleneck_capacity: 瓶颈产能（颗/小时）
        
    Returns:
        float: 负荷率，0-1之间的值
    """
```

##### to_dict()

```python
def to_dict(self) -> Dict[str, Any]:
    """
    将工序对象转换为字典格式（用于JSON序列化）
    
    Returns:
        Dict: 包含工序所有字段的字典
    """
```

##### from_dict(data: Dict[str, Any])

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Station':
    """
    从字典创建工序对象（反序列化）
    
    Args:
        data: 包含工序数据的字典
        
    Returns:
        Station: 新创建的工序对象
    """
```

### 2.3 ProductionLine（产线模型）

代表一条完整的产线，包含多个工序。

#### 构造函数

```python
ProductionLine(name: str, stations: List[Station] = [], shift_hours: int = 8, break_minutes: int = 60, worker_hourly_wage: float = 20.0)
```

#### 主要属性

| 属性名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| name | str | 必填 | 产线名称 |
| stations | List[Station] | [] | 工序列表 |
| shift_hours | int | 8 | 班次时长（小时） |
| break_minutes | int | 60 | 休息时间（分钟） |
| worker_hourly_wage | float | 20.0 | 工人时薪（元/小时） |

#### 主要方法

##### add_station(station: Station)

```python
def add_station(self, station: Station) -> None:
    """
    添加一个工序到产线
    
    Args:
        station: 要添加的工序对象
    """
```

##### remove_station(station_id: str)

```python
def remove_station(self, station_id: str) -> bool:
    """
    从产线中删除一个工序
    
    Args:
        station_id: 要删除的工序ID
        
    Returns:
        bool: 是否成功删除
    """
```

##### find_bottleneck()

```python
def find_bottleneck(self) -> Optional[Station]:
    """
    找出瓶颈工序（产能最低的工序）
    
    Returns:
        Optional[Station]: 瓶颈工序对象，如果产线为空返回None
    """
```

##### get_bottleneck_capacity()

```python
def get_bottleneck_capacity(self) -> float:
    """
    获取瓶颈产能（产线的最大产能）
    
    Returns:
        float: 瓶颈产能（颗/小时）
    """
```

##### calculate_daily_output()

```python
def calculate_daily_output(self) -> float:
    """
    计算预计日产量（颗/天）
    
    Returns:
        float: 预计日产量（颗）
    """
```

##### calculate_total_cost()

```python
def calculate_total_cost(self) -> float:
    """
    计算总人力成本（元/天）
    
    Returns:
        float: 总人力成本（元/天）
    """
```

##### calculate_unit_cost()

```python
def calculate_unit_cost(self) -> float:
    """
    计算单颗成本（元/颗）
    
    Returns:
        float: 单颗成本（元/颗）
    """
```

##### calculate_line_balance_rate()

```python
def calculate_line_balance_rate(self) -> float:
    """
    计算产线平衡率
    
    Returns:
        float: 产线平衡率（0-1之间）
    """
```

##### calculate_upph()

```python
def calculate_upph(self) -> float:
    """
    计算UPPH（Units Per Person per Hour）
    
    Returns:
        float: UPPH值（颗/人·小时）
    """
```

##### to_dict()

```python
def to_dict(self) -> Dict[str, Any]:
    """
    将产线对象转换为字典格式（用于JSON序列化）
    
    Returns:
        Dict: 包含产线所有字段的字典
    """
```

##### from_dict(data: Dict[str, Any])

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'ProductionLine':
    """
    从字典创建产线对象（反序列化）
    
    Args:
        data: 包含产线数据的字典
        
    Returns:
        ProductionLine: 新创建的产线对象
    """
```

### 2.4 Alert（报警模型）

用于表示各种报警信息，如瓶颈、资源浪费、堵塞等。

#### 构造函数

```python
Alert(alert_type: str, severity: str, station_id: str, message: str, suggestion: str = "", timestamp_minutes: float = 0.0)
```

#### 主要属性

| 属性名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| alert_type | str | 必填 | 报警类型：bottleneck/waste/blockage |
| severity | str | 必填 | 严重程度：critical/warning/info |
| station_id | str | 必填 | 相关工序ID |
| message | str | 必填 | 报警消息 |
| suggestion | str | "" | 优化建议 |
| timestamp_minutes | float | 0.0 | 报警时间戳（从仿真开始经过的分钟数） |

### 2.5 SimulationState（仿真状态）

记录仿真过程中的状态快照，用于GUI实时显示和数据分析。

#### 构造函数

```python
SimulationState(current_time: float, station_states: Dict[str, Dict[str, Any]], total_output: int = 0, bottleneck_id: Optional[str] = None)
```

#### 主要属性

| 属性名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| current_time | float | 必填 | 当前仿真时间（秒） |
| station_states | Dict[str, Dict[str, Any]] | 必填 | 各工序状态字典 |
| total_output | int | 0 | 累计总产出（颗） |
| bottleneck_id | Optional[str] | None | 当前瓶颈工序ID |

### 2.6 Scenario（方案类）

存储产线配置的快照，用于方案对比和分析。

#### 构造函数

```python
Scenario(name: str, production_line: ProductionLine, created_at: str, description: str = "")
```

#### 主要属性

| 属性名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| name | str | 必填 | 方案名称 |
| production_line | ProductionLine | 必填 | 产线配置快照（深拷贝） |
| created_at | str | 必填 | 创建时间（格式化字符串） |
| description | str | "" | 方案描述 |

#### 主要方法

##### get_kpis()

```python
def get_kpis(self) -> Dict[str, float]:
    """
    计算并返回所有KPI指标
    
    Returns:
        Dict[str, float]: KPI字典，包含total_workers, bottleneck_capacity, daily_output等
    """
```

##### create(name: str, production_line: ProductionLine, description: str = "")

```python
@classmethod
def create(cls, name: str, production_line: ProductionLine, description: str = "") -> 'Scenario':
    """
    创建方案对象（工厂方法）
    
    Args:
        name: 方案名称
        production_line: 要保存的产线对象
        description: 方案描述（可选）
        
    Returns:
        Scenario: 新创建的方案对象
    """
```

## 3. 数据流向

数据模型在系统中的主要流向：

1. 用户通过GUI界面创建或编辑产线配置
2. 配置数据存储在`ProductionLine`和`Station`对象中
3. 仿真引擎使用这些对象运行仿真
4. 仿真过程中生成`SimulationState`和`Alert`对象
5. 结果数据通过GUI界面显示给用户
6. 用户可以保存配置为`Scenario`对象，用于后续对比分析

## 4. 序列化与反序列化

所有数据模型类都支持JSON序列化和反序列化，通过以下方法实现：

- `to_dict()`：将对象转换为字典格式
- `from_dict()`：从字典创建对象

这使得配置数据可以方便地保存到文件或从文件加载。

## 5. 使用示例

### 创建产线和工序

```python
from src.models import Station, ProductionLine, CollaborationType

# 创建产线
line = ProductionLine("测试产线")

# 创建工序
station1 = Station(
    id="s01",
    name="注油",
    process_time=25,
    worker_count=2,
    collaboration_type=CollaborationType.PARALLEL
)

station2 = Station(
    id="s02",
    name="焊接",
    process_time=30,
    worker_count=3,
    collaboration_type=CollaborationType.PARALLEL
)

# 添加工序到产线
line.add_station(station1)
line.add_station(station2)

# 计算KPI
print(f"瓶颈产能: {line.get_bottleneck_capacity():.0f} 颗/h")
print(f"日产量: {line.calculate_daily_output():.0f} 颗")
print(f"单颗成本: {line.calculate_unit_cost():.2f} 元/颗")
```

### 保存和加载配置

```python
from src.utils import save_config, load_config

# 保存配置
save_config(line, "configs/my_line.json")

# 加载配置
loaded_line = load_config("configs/my_line.json")
print(f"加载的产线名称: {loaded_line.name}")
```
