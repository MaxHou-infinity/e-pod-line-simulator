"""
程序入口 - 应用程序的主入口点

这个文件是程序的启动入口，负责：
1. 初始化应用程序
2. 创建主窗口
3. 启动GUI主循环

使用方式：
    python main.py

或者：
    python -m src.main
"""

import sys
import os

# 添加项目根目录到Python路径
# 这样可以直接导入src模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.gui_main import MainWindow
from src.utils import setup_logger
from src.version import PRODUCT_NAME


def main():
    """
    主函数 - 程序入口点
    
    这是程序的入口函数，负责：
    1. 设置日志
    2. 创建主窗口
    3. 启动GUI事件循环
    
    异常处理：
    - 捕获所有异常并记录日志
    - 显示友好的错误提示
    """
    try:
        # 设置日志
        logger = setup_logger()
        logger.info("=" * 50)
        logger.info("%s 启动", PRODUCT_NAME)
        logger.info("=" * 50)
        
        # 创建主窗口
        app = MainWindow()
        
        # 启动GUI主循环
        # mainloop()会阻塞，直到窗口关闭
        app.run()
        
        logger.info("程序正常退出")
        
    except KeyboardInterrupt:
        # 用户按Ctrl+C中断
        print("\n程序被用户中断")
        sys.exit(0)
        
    except Exception as e:
        # 捕获所有其他异常
        error_msg = f"程序运行错误：{e}\n\n详细日志：logs/app.log"
        print(error_msg)
        
        # 记录日志
        try:
            logger = setup_logger()
            logger.error(error_msg, exc_info=True)
        except:
            pass
        
        # 显示错误提示（如果有GUI）
        try:
            import tkinter.messagebox as msgbox
            msgbox.showerror("错误", error_msg)
        except:
            pass
        
        sys.exit(1)


if __name__ == '__main__':
    """
    程序入口
    
    当直接运行此文件时，执行main()函数
    这样设计的好处：
    1. 可以作为脚本直接运行：python main.py
    2. 也可以作为模块导入：from src import main
    3. 方便测试和调试
    """
    main()
