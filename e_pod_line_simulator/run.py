#!/usr/bin/env python3
"""
程序启动脚本

快速启动程序的便捷脚本
可以直接运行：python run.py
"""

import sys
import os

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 运行主程序
if __name__ == '__main__':
    from main import main
    main()

