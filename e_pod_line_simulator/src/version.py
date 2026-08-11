"""
版本号定义 - 全项目唯一版本入口

所有显示版本号的位置（窗口标题、关于对话框、README）都应引用此文件，
避免多处维护导致版本不一致。
"""

__version__ = "3.0.0"
VERSION_STRING = f"v{__version__}"

# Bug 反馈与资助入口（可在发布前替换为个人链接）
BUG_REPORT_URL = "https://github.com/MaxHou-infinity/e-pod-line-simulator/issues"
KO_FI_URL = "https://ko-fi.com/"  # Ko-fi 主页（可同时与支付宝赞赏码并存）
ALIPAY_QR_PATH = ""  # 支付宝赞赏码图片路径（PNG/GIF），如 "assets/alipay_qr.png"
SUPPORT_URL = KO_FI_URL  # 兼容旧引用
