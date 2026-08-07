# 电子烟产线仿真优化工具

## 项目简介

这是一个基于SimPy的离散事件仿真工具，用于电子烟产线的设计和优化。

**核心价值**：让产线优化从"2周试错"变成"2小时仿真"

### 主要功能

1. **产线配置管理**：创建、编辑、删除工序
2. **离散事件仿真**：基于SimPy的仿真引擎
3. **2D可视化**：直观显示产线布局和实时状态
4. **瓶颈识别**：自动识别瓶颈工序并给出优化建议
5. **KPI监控**：实时显示关键绩效指标

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行程序

```bash
cd src
python main.py
```

或者：

```bash
python -m src.main
```

### 3. 使用步骤

1. **创建产线**：点击"文件" → "新建产线"
2. **添加工序**：点击"添加"按钮，输入工序参数
3. **运行仿真**：点击"开始仿真"按钮
4. **查看结果**：观察瓶颈和KPI指标
5. **优化调整**：根据建议调整参数

## 项目结构

```
e_pod_line_simulator/
├── src/                    # 源代码
│   ├── main.py            # 程序入口
│   ├── models.py          # 数据模型
│   ├── simulation.py      # 仿真引擎
│   ├── gui_main.py        # 主窗口
│   ├── gui_canvas.py      # 画布视图
│   ├── gui_panels.py      # 面板组件
│   └── utils.py           # 工具函数
├── configs/               # 配置文件
│   └── default.json       # 默认配置
├── requirements.txt        # 依赖包
└── README.md              # 项目说明
```

## 技术栈

- **Python 3.8+**
- **SimPy 4.0+**：离散事件仿真引擎
- **Tkinter**：GUI框架（Python标准库）
- **Pandas**：数据处理（Excel导入）

## 开发指南

### 代码结构

- **models.py**：数据模型层，定义所有数据结构
- **simulation.py**：业务逻辑层，仿真引擎核心
- **gui_*.py**：界面层，GUI组件
- **utils.py**：工具函数层，通用功能
- **scenario_manager.py**：方案管理模块

### API文档

详细的API文档请查看：
- [数据模型API](docs/api/models.md)：详细说明产线、工序等数据模型
- [仿真引擎API](docs/api/simulation.md)：详细说明仿真引擎的使用方法
- [工具函数API](docs/api/utils.md)：详细说明各种工具函数

### 配置说明

#### JSON配置文件格式

配置文件采用JSON格式，包含以下主要字段：

| 字段名 | 类型 | 描述 | 示例值 |
|--------|------|------|--------|
| name | string | 产线名称 | "电子烟产线_标准版" |
| shift_hours | int | 班次时长（小时） | 8 |
| break_minutes | int | 休息时间（分钟） | 60 |
| worker_hourly_wage | float | 工人时薪（元/小时） | 20.0 |
| stations | array | 工序列表 | [{}, {}, ...] |

#### 工序配置字段

| 字段名 | 类型 | 描述 | 示例值 |
|--------|------|------|--------|
| id | string | 工序唯一ID | "s01" |
| name | string | 工序名称 | "注油" |
| process_time | float | 单颗耗时（秒） | 25 |
| worker_count | int | 工人数量 | 2 |
| collaboration_type | string | 协作模式（parallel/collaborative） | "parallel" |
| oee | float | 设备综合效率（0-1） | 0.85 |
| efficiency | float | 人员效率（0-1） | 0.95 |
| changeover_time | int | 切换时间（分钟） | 45 |
| buffer_capacity | int | 缓冲区容量 | 100 |

### 添加新功能

1. 数据模型：在`models.py`中添加新类
2. 业务逻辑：在`simulation.py`中添加函数
3. GUI界面：在`gui_*.py`中添加组件
4. 工具函数：在`utils.py`中添加辅助函数
5. 更新文档：同步更新API文档和配置说明

## 常见问题

### Q: 如何添加新工序？

A: 点击配置面板的"添加"按钮，输入工序参数即可。

### Q: 仿真速度如何调整？

A: 在控制按钮区域选择速度倍数（1x/8x/16x/32x）。

### Q: 如何保存配置？

A: 点击"文件" → "保存配置"，选择保存路径。

### Q: 如何识别瓶颈？

A: 瓶颈会自动识别并高亮显示，同时显示在报警面板中。

## 版本历史

- **v1.0** (2024-01-15)：初始版本，实现核心功能

## 许可证

本项目仅供学习和研究使用。

## 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues
- 邮箱：support@example.com
