"""
设计令牌与主题 - V1.2.0 视觉体系唯一来源

所有颜色、字体、间距、状态色、报警图标集中定义在这里，
GUI 组件通过引用令牌保持视觉一致，避免散落硬编码。
"""

import platform
import tkinter as tk


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

# V3.0 Design Tokens 2.0
RADIUS = {'sm': 8, 'md': 12, 'lg': 16}
SHADOW = {'card': (0, 1, 2), 'popup': (0, 4, 12)}
MOTION = {'fast': 120, 'normal': 180}

# 亮 / 暗双主题色板（V3.0）
THEMES = {
    'light': {
        **COLORS,
        'canvas': '#FFFFFF',
        'grid': '#EDEFF3',
        'hover': '#F0F3F8',
        'focus': '#2F6FED',
        'toast_bg': '#1F2329',
        'toast_fg': '#FFFFFF',
    },
    'dark': {
        'bg': '#17181C',
        'surface': '#23252B',
        'border': '#34373F',
        'text': '#ECEDEF',
        'text_secondary': '#9BA1AB',
        'primary': '#5B8DEF',
        'primary_hover': '#7BA2F2',
        'primary_soft': '#26344D',
        'success': '#4CD07D',
        'danger': '#FF6B5E',
        'warning': '#FFB340',
        'info': '#5BA8FF',
        'idle': '#3A3D45',
        'canvas': '#121316',
        'grid': '#23262C',
        'hover': '#2A2D34',
        'focus': '#7BA2F2',
        'toast_bg': '#ECEDEF',
        'toast_fg': '#17181C',
    },
}

STATUS_COLORS_DARK = {
    'idle': '#3A3D45',
    'running': '#4CD07D',
    'blocked': '#FF6B5E',
    'waiting': '#FFB340',
    'changeover': '#5BA8FF',
}

STATUS_SOFT_DARK = {
    'idle': '#2A2D34',
    'running': '#1E3529',
    'blocked': '#3A2220',
    'waiting': '#3A2F1C',
    'changeover': '#1E2C3D',
}

ALERT_COLORS_DARK = {
    'critical': '#FF6B5E',
    'warning': '#FFB340',
    'info': '#5BA8FF',
}

_current_dark = False


def is_dark() -> bool:
    """当前是否为深色主题"""
    return _current_dark


def get_palette(dark: bool = False) -> dict:
    """返回指定主题的完整色板"""
    return THEMES['dark' if dark else 'light']


def status_color(status: str) -> str:
    """按当前主题返回工序状态色"""
    palette = STATUS_COLORS_DARK if _current_dark else STATUS_COLORS
    return palette.get(status, palette['idle'])


def status_soft(status: str) -> str:
    """按当前主题返回工序状态浅色填充"""
    palette = STATUS_SOFT_DARK if _current_dark else STATUS_SOFT
    return palette.get(status, palette['idle'])


def alert_color(severity: str) -> str:
    """按当前主题返回报警级别色"""
    palette = ALERT_COLORS_DARK if _current_dark else ALERT_COLORS
    return palette.get(severity, '#CCCCCC')


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


def apply_theme(root, dark: bool = False) -> dict:
    """
    将设计令牌应用到 Tk 根窗口

    - 切换到 clam 主题以获得跨平台一致的 ttk 样式
    - 配置字体/颜色/间距/按钮/Treeview 等基础组件

    Args:
        root: tk.Tk 根窗口
        dark: 是否使用深色主题（默认 False）

    Returns:
        dict: 生效的主题色板
    """
    global _current_dark, COLORS
    _current_dark = bool(dark)
    palette = get_palette(_current_dark)
    COLORS.update(palette)  # 就地更新模块级 COLORS，兼容既有引用

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
    style.configure(
        'Primary.TButton',
        background=COLORS['primary'],
        foreground='#FFFFFF',
        font=(family, 11),
        padding=(12, 6),
    )
    style.map(
        'Primary.TButton',
        background=[('active', COLORS['primary_hover'])],
        foreground=[('disabled', '#B9C4D4')],
    )
    style.configure(
        'Danger.TButton',
        background=COLORS['danger'],
        foreground='#FFFFFF',
        padding=(12, 6),
    )
    style.map('Danger.TButton', background=[('active', '#D9342B')])
    style.configure(
        'Secondary.TButton',
        background=COLORS['surface'],
        foreground=COLORS['text'],
        padding=(12, 6),
    )
    style.map('Secondary.TButton', background=[('active', COLORS['hover'])])
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
        selectbackground=COLORS['primary'],
        selectforeground=COLORS['inverse_text'] if 'inverse_text' in COLORS else '#FFFFFF',
    )
    style.configure(
        'Treeview.Heading',
        font=(family, 10, 'bold'),
        background=COLORS['surface'],
        foreground=COLORS['text'],
    )
    style.configure(
        'TEntry',
        fieldbackground=COLORS['surface'],
        bordercolor=COLORS['border'],
    )
    style.map(
        'TEntry',
        bordercolor=[('focus', COLORS['focus'])],
        fieldbackground=[('disabled', COLORS['bg'])],
    )
    style.configure('TCombobox', fieldbackground=COLORS['surface'], bordercolor=COLORS['border'])
    style.map('TCombobox', bordercolor=[('focus', COLORS['focus'])])

    root.configure(bg=COLORS['bg'])
    root.option_add('*Font', (family, 11))
    return palette

    # HiDPI：按系统实际 DPI 设置 Tk 缩放，保证高分屏清晰
    try:
        root.tk.call('tk', 'scaling', root.winfo_fpixels('1i') / 72.0)
    except Exception:
        pass


class ToolTip:
    """
    轻量 Tooltip：悬停显示提示文本

    使用方式：
        ToolTip(button, "开始仿真（空格）")
    """

    def __init__(self, widget, text: str, delay_ms: int = 400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip_window = None
        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')

    def _schedule(self, event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self) -> None:
        self._after_id = None
        if self._tip_window is not None:
            return
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip_window = tk.Toplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._tip_window,
            text=self.text,
            justify='left',
            bg=COLORS['text'],
            fg=COLORS['surface'],
            padx=6,
            pady=3,
            font=(resolve_font_family(), 10),
        ).pack()

    def _hide(self, event=None) -> None:
        self._cancel()
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None


class Toast:
    """
    轻量 Toast 反馈（V3.0）

    使用方式：
        show_toast(root, "已保存")
    """

    def __init__(self, root, text: str, duration_ms: int = 2200):
        top = tk.Toplevel(root)
        top.overrideredirect(True)
        top.attributes('-topmost', True)
        label = tk.Label(
            top,
            text=text,
            bg=COLORS['toast_bg'],
            fg=COLORS['toast_fg'],
            padx=16,
            pady=10,
            font=(resolve_font_family(), 11),
        )
        label.pack()
        top.update_idletasks()
        x = root.winfo_rootx() + root.winfo_width() - top.winfo_width() - 24
        y = root.winfo_rooty() + root.winfo_height() - top.winfo_height() - 48
        top.geometry(f"+{max(0, x)}+{max(0, y)}")
        top.after(duration_ms, top.destroy)


def show_toast(root, text: str, duration_ms: int = 2200) -> None:
    """显示 Toast 反馈"""
    Toast(root, text, duration_ms)
