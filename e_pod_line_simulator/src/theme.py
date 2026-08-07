"""
设计令牌与主题 - V1.2.0 视觉体系唯一来源

所有颜色、字体、间距、状态色、报警图标集中定义在这里，
GUI 组件通过引用令牌保持视觉一致，避免散落硬编码。
"""

import platform


# ==================== 设计令牌 ====================

COLORS = {
    'bg': '#F5F6F8',          # 应用背景
    'surface': '#FFFFFF',     # 卡片/面板表面
    'border': '#E2E5EA',      # 边框
    'text': '#1F2329',        # 主文本
    'text_secondary': '#6B7280',  # 次要文本
    'primary': '#2F6FED',     # 主色
    'primary_hover': '#1F5FD8',
    'primary_soft': '#EAF1FE',
    'success': '#34C759',
    'danger': '#FF3B30',
    'warning': '#FF9F0A',
    'info': '#0A84FF',
    'idle': '#E5E5EA',
}

# 工序状态色（V1.2：柔和、语义清晰）
STATUS_COLORS = {
    'idle': COLORS['idle'],
    'running': COLORS['success'],
    'blocked': COLORS['danger'],
    'waiting': COLORS['warning'],
    'changeover': COLORS['info'],
}

# 工序状态浅色填充（节点卡片底色，避免整块高饱和）
STATUS_SOFT = {
    'idle': '#F0F1F3',
    'running': '#E7F8EE',
    'blocked': '#FDEBEA',
    'waiting': '#FFF3E0',
    'changeover': '#E6F2FE',
}

# 报警级别图标
ALERT_ICONS = {
    'critical': '⛔',
    'warning': '⚠️',
    'info': 'ℹ️',
}

ALERT_COLORS = {
    'critical': COLORS['danger'],
    'warning': COLORS['warning'],
    'info': COLORS['info'],
}

# 间距刻度（4/8/12/16/24）
SPACING = {
    'xs': 4,
    'sm': 8,
    'md': 12,
    'lg': 16,
    'xl': 24,
}


def resolve_font_family() -> str:
    """
    按平台解析中文字体族

    Returns:
        str: 优先 PingFang SC（macOS）/ 微软雅黑（Windows），回退 Arial
    """
    system = platform.system()
    if system == 'Darwin':
        return 'PingFang SC'
    if system == 'Windows':
        return 'Microsoft YaHei'
    return 'Arial'


def apply_theme(root) -> None:
    """
    将设计令牌应用到 Tk 根窗口

    - 切换到 clam 主题以获得跨平台一致的 ttk 样式
    - 配置字体/颜色/间距/按钮/Treeview 等基础组件

    Args:
        root: tk.Tk 根窗口
    """
    import tkinter as tk
    from tkinter import ttk

    family = resolve_font_family()
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass

    style.configure(
        '.',
        font=(family, 11),
        background=COLORS['bg'],
        foreground=COLORS['text'],
    )
    style.configure('TFrame', background=COLORS['bg'])
    style.configure('TLabel', background=COLORS['bg'], foreground=COLORS['text'])
    style.configure('TLabelframe', background=COLORS['bg'], bordercolor=COLORS['border'])
    style.configure(
        'TLabelframe.Label',
        background=COLORS['bg'],
        foreground=COLORS['text'],
        font=(family, 11, 'bold'),
    )
    style.configure('TButton', font=(family, 11), padding=(10, 5))
    style.configure('Accent.TButton', background=COLORS['primary'], foreground='white')
    style.map(
        'Accent.TButton',
        background=[('active', COLORS['primary_hover'])],
        foreground=[('disabled', '#B9C4D4')],
    )
    style.configure(
        'Treeview',
        background=COLORS['surface'],
        fieldbackground=COLORS['surface'],
        foreground=COLORS['text'],
        rowheight=26,
        font=(family, 10),
    )
    style.configure(
        'Treeview.Heading',
        font=(family, 10, 'bold'),
        background=COLORS['surface'],
        foreground=COLORS['text'],
    )
    style.configure('TEntry', fieldbackground=COLORS['surface'])
    style.configure('TCombobox', fieldbackground=COLORS['surface'])

    root.configure(bg=COLORS['bg'])
    root.option_add('*Font', (family, 11))
