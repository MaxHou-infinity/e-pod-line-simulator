"""
pytest 公共配置

确保测试可以从任意工作目录运行，并能够导入 src 包。
"""

import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# test_basic.py 是脚本式测试（函数间通过返回值传递数据），保持独立入口，
# 不参与 pytest 收集，避免被误当作 fixture 用例
collect_ignore = ["test_basic.py"]
