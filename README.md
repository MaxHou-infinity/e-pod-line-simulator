# 电子烟产线仿真优化工具（e-Pod Line Simulator）

> **Production Line Simulation & Optimization for E-cigarette Pods, E-liquid Filling and Nicotine Pouches.**
> 基于 SimPy 的离散事件产线仿真与人力配置优化工具，支持烟弹组装 / 烟油灌装 / 尼古丁袋高速包装三种生产形态。

![version](https://img.shields.io/badge/version-3.2.0-1F2329)
![python](https://img.shields.io/badge/Python-3.8%2B-2F6FED)
![CI](https://github.com/MaxHou-infinity/e-pod-line-simulator/actions/workflows/ci.yml/badge.svg)
![license](https://img.shields.io/badge/license-Attribution%20Authorization-blue)
![release](https://img.shields.io/github/v/release/MaxHou-infinity/e-pod-line-simulator?label=latest%20release&color=2F6FED)

![主界面](docs/images/screenshot_main.png)

---

## 为什么用这个工具？

**把产线设计从“2 周试错”压缩到“2 小时仿真”**。

- 传统方式依赖 IE 工程师的 Excel 静态计算、车间经验与现场试错；
- 本工具通过 **SimPy 离散事件仿真** 模拟真实产线动态（WIP、堵塞、饥饿、切换、清洗），在投入人力/设备前量化产能与成本；
- 面向 **IE 工程师、产线经理、精益顾问**，用数据支撑人力配置与瓶颈优化决策。

## 核心功能

- **三种生产类型模板**：烟弹组装（颗）/ 烟油灌装（升）/ 尼古丁袋高速包装（袋），字段与计量单位自动适配
- **SimPy 离散事件仿真**：并联/协同、WIP 缓冲区、切换事件、CIP/SIP 清洗、机台节拍、批量/配方/储罐
- **智能报警**：瓶颈、WIP 堆积、饥饿/堵塞、预测预警，并按工序类型给出正确优化建议
- **工序级评估**：运行/等待/堵塞时长、实际利用率、失衡分析（瓶颈/饥饿/堵塞/冗余）
- **敏感性试算**：瓶颈 +1 人 / OEE+5% / 节拍 -1s 的产出与成本对比
- **方案对比与报告**：最多 5 个方案持久化对比；Excel（9+ Sheet）/ PDF 报告导出
- **体验**：统一浅色主题、命令面板（Ctrl+K）、快捷键、Toast、报警筛选/折叠、快速配置向导

## 快速开始

### 方式一：压缩包（推荐普通用户）

从 [GitHub Releases 下载最新压缩包](https://github.com/MaxHou-infinity/e-pod-line-simulator/releases/latest)：

1. 解压 `E-Pod-Line-Simulator-v3.1.0.zip`；
2. 进入 `e_pod_line_simulator`；
3. macOS 双击 `启动.command`，Windows 双击 `启动.bat`（首次自动安装依赖）。

### 方式二：命令行

```bash
cd e_pod_line_simulator
pip install -r requirements.txt
python run.py
```

### 开发者/测试

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

## 文档导航

- [详细 README（安装/配置/FAQ）](e_pod_line_simulator/README.md)
- [更新日志 CHANGELOG](CHANGELOG.md)
- [产品需求文档 PRD](电子烟产线仿真优化.md)
- [开发与贡献规范](AGENTS.md)
- [V1.3 需求与开发路线图（烟油/尼古丁袋）](e_pod_line_simulator/docs/v1.3/需求与开发路线图.md)
- [V3.0 体验与视觉升级规划](e_pod_line_simulator/docs/v3.0/体验视觉升级规划.md)
- [V3.1 开发日志](e_pod_line_simulator/docs/v3.1/开发日志.md)
- [V3.2 人力规划与多业态深化路线图](e_pod_line_simulator/docs/v3.2/需求与开发路线图.md)
- [V3.2 开发日志](e_pod_line_simulator/docs/v3.2/开发日志.md)
- [项目成熟度分析](e_pod_line_simulator/docs/项目成熟度分析.md)

## 技术栈

| 组件 | 说明 |
|------|------|
| Python 3.8+ | 应用语言 |
| SimPy 4.0+ | 离散事件仿真引擎 |
| Tkinter | 桌面 GUI（标准库） |
| pandas / openpyxl / reportlab | Excel 导入导出与 PDF 报告 |
| pytest / pytest-cov | 测试与覆盖率 |

## 目录结构

```
e_pod_line_simulator/
├── src/        # 源码（models / simulation / gui / reporting / sensitivity / theme）
├── configs/    # 默认配置、Excel 模板、方案持久化
├── docs/       # PRD、设计、路线图、开发日志
├── tests/      # 95 个 pytest 用例
└── assets/     # 图标与赞赏码资源
```

## 路线图

- ✅ **V1.0-V1.3**：MVP、交互/视觉、烟油与尼古丁袋产品形态扩展
- ✅ **V3.0**：2026 桌面美学体验升级
- ✅ **V3.1**：智能报警与评估能力（已定版 v3.1.0）
- 🔄 **V3.2**：人力规划与多业态深化（开发中）
- ⏳ **V2.0**：Web 化

## 支持与反馈

- 🐛 Bug 反馈：[GitHub Issues](https://github.com/MaxHou-infinity/e-pod-line-simulator/issues)
- ☕ 资助作者：扫描 `e_pod_line_simulator/assets/wechat_qr.png`（微信赞赏码）

## 许可与免责

本项目采用 **署名-授权许可证 v1.0**（[LICENSE](LICENSE)）：允许使用与修改，
但须保留作者署名与出处；对外发布或商业使用前，须通知作者并取得明确授权。

仿真结果为产线设计与人力规划的参考，不构成产能或成本承诺；实际投产前请以现场验证为准，作者不对据此做出的决策损失承担责任。

## 关键词

电子烟、烟弹、烟油、尼古丁袋、产线仿真、离散事件仿真、SimPy、Tkinter、数字孪生、产线优化、人力配置、瓶颈分析、WIP、UPPH、OEE、快速换型、CIP/SIP、Production Line Simulation, Discrete Event Simulation, E-liquid Filling, Nicotine Pouch, Manufacturing Optimization, Bottleneck Analysis, Line Balancing, Python。
