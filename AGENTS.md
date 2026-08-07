# Repository Guidelines

## Project Structure & Module Organization

The application lives in `e_pod_line_simulator/`:

```
src/                  # Application code
  main.py             # Entry point
  models.py           # Data models: Station, ProductionLine, Scenario
  simulation.py       # SimPy simulation engine and bottleneck logic
  scenario_manager.py # Scenario save/compare/recommend logic
  gui_main.py         # Main Tkinter window
  gui_canvas.py       # 2D production-line canvas
  gui_panels.py       # Config, KPI, and alert panels
  utils.py            # File I/O, validation, helpers
configs/              # default.json and Excel import template
docs/                 # Design, API, and maturity documents
tests/                # Test scripts
```

Top-level PRD files (`电子烟产线仿真优化*.md`) and scenario JSONs
(`方案*.json`) are part of the product spec and must stay at the root.

## Build, Test, and Development Commands

```bash
pip install -r requirements.txt        # Install SimPy, pandas, openpyxl
python run.py                          # Launch the GUI
python tests/test_basic.py             # Run the basic test suite
python -m pytest tests -q              # Run the full pytest suite
```

There is no build step; packaging (PyInstaller) is not configured yet.
Use an environment where `simpy` is installed.

## Coding Style & Naming Conventions

- Python 3.8+, PEP 8: 4-space indentation, line length ≤ 99.
- Classes: `PascalCase` (`ProductionLine`); functions/variables: `snake_case`
  (`get_capacity`); constants: `UPPER_SNAKE`.
- Add docstrings and type hints to public classes and functions.
- Identifiers stay English; comments and UI text may be Chinese.
- No formatter or linter is configured; check syntax with
  `python -m py_compile <file>`.

## Testing Guidelines

- Tests are plain Python scripts under `tests/`, named `test_*.py`, with
  functions named `test_*`.
- `tests/test_basic.py` covers models, KPI calculation, bottleneck detection,
  waste detection, and utilities.
- Add tests in the same file for small changes, or create `test_<module>.py`
  for larger features.
- Target coverage for core modules is >80% (aspirational, not yet enforced).

## Commit & Pull Request Guidelines

- Follow Conventional Commits: `type: description`, e.g.
  `feat: 增加报告导出`, `fix: 修复仿真重启问题`, `docs: 更新 README`.
- Descriptions may be Chinese; keep them short and specific.
- One logical change per commit; keep the working tree clean.
- Pull requests must state what and why, link related issues, and include
  screenshots for UI changes. Run the test suite before requesting review.
- Update `logs.md` and the relevant `docs/` files when behavior changes.

## Security & Configuration Tips

- This is a local-only tool; never store credentials in configs.
- Do not commit `__pycache__/`, `.DS_Store`, `.trae/`, or `*.log` — they are
  already covered by `.gitignore`.
- Always validate station parameters and sanitize imported Excel data.

## Agent-Specific Instructions

- Read `README.md` and the relevant `docs/` file before editing.
- Keep user-facing responses in Chinese unless the user asks otherwise.
