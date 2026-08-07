# 电子烟产线仿真优化工具

**版本：v1.2.0（可交付版）**

基于 SimPy + Tkinter 的电子烟产线设计与优化工具：通过离散事件仿真，
在投入实际资源前找到最优人力配置，让产线优化从"2 周试错"变成"2 小时仿真"。

## 快速开始（压缩包用户）

1. 解压本压缩包；
2. 进入 `e_pod_line_simulator` 目录；
3. 启动方式二选一：
   - **普通用户**：macOS 双击 `启动.command`，Windows 双击 `启动.bat`
     （首次运行会自动安装依赖）；
   - **开发者**：`pip install -r requirements.txt` 后执行 `python run.py`。

## 主要功能

- 产线配置（手动 / Excel 导入 / 快速配置向导）
- SimPy 离散事件仿真（并联/协同、WIP、切换事件）
- 2D 蛇形画布：节点卡片、状态条、瓶颈徽标、拖拽排序
- 瓶颈识别与报警（支持一键复制报警文本）
- KPI 实时监控（含 UPPH）与方案对比（最多 5 个，自动持久化）
- 报告导出（Excel / PDF）
- 供应链术语速查

## 详细文档

- 安装、使用、配置说明：[e_pod_line_simulator/README.md](e_pod_line_simulator/README.md)
- 开发与测试规范：[AGENTS.md](AGENTS.md)
- 产品需求：[电子烟产线仿真优化.md](电子烟产线仿真优化.md)
- 版本路线图：[e_pod_line_simulator/docs/v1.2/开发路线图.md](e_pod_line_simulator/docs/v1.2/开发路线图.md)

## 环境要求

- Python 3.8+
- 依赖：simpy、pandas、openpyxl、reportlab
- macOS / Windows / Linux（Tkinter 桌面环境）
