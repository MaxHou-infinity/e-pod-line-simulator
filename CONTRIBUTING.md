# 为 PuffLine Planner 做贡献

感谢你帮助改进 PuffLine Planner。提交改动前，请先阅读本指南以及项目的 [LICENSE](LICENSE)。

## 开发环境

项目使用 Python 3.8+；持续集成使用 Python 3.12。建议在虚拟环境中开发：

```bash
git clone https://github.com/MaxHou-infinity/puffline-planner.git
cd puffline-planner/e_pod_line_simulator
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

启动桌面应用：

```bash
python run.py
```

## 测试

提交前请在 `e_pod_line_simulator` 目录运行完整测试：

```bash
python -m pytest tests -q
```

如果修改了核心模型或计算逻辑，建议同时检查覆盖率：

```bash
python -m pytest tests \
  --cov=src.models \
  --cov=src.simulation \
  --cov=src.scenario_manager \
  --cov=src.reporting \
  --cov=src.utils \
  --cov-report=term-missing
```

请为新增行为补充测试；修复 Bug 时，优先添加能够重现问题的回归测试。

## 代码与文档约定

- 遵循 PEP 8，使用 4 空格缩进；类名使用 `PascalCase`，函数和变量使用 `snake_case`。
- 公共类和函数应提供清晰的 docstring，并在有助于理解接口时补充类型标注。
- 标识符使用英文；面向用户的界面文字和说明可以使用中文。
- 不要提交凭证、真实员工信息、客户数据或未经脱敏的生产配置。
- 用户操作或配置口径变化时，同步更新 [用户指南](docs/user-guide.md)。
- 面向使用者的重要变化应记录到 [CHANGELOG](CHANGELOG.md)。

## 提交 Issue

- Bug：说明应用版本、操作系统、复现步骤、预期结果与实际结果。
- 建议：说明目标用户、使用场景和期望解决的问题。
- 上传日志、截图、配置或报告前，请先移除敏感信息。

## Pull Request

1. 从最新的 `main` 创建主题分支。
2. 保持改动聚焦，一个 Pull Request 解决一个明确问题。
3. 提交信息建议使用 Conventional Commits，例如 `fix: 修复仿真重启问题` 或 `docs: 更新用户指南`。
4. 在 Pull Request 中说明改动原因、实现范围和验证方式，并关联相关 Issue。
5. 界面变化请附修改前后截图；计算口径变化请给出示例输入和预期输出。
6. 确保完整测试通过，再请求审阅。

维护者会结合产品范围、验证证据和许可证条件评估合并。提交 Pull Request 不代表改动一定会被接受或进入发布版本。
