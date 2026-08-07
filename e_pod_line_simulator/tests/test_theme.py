"""设计令牌单元测试（headless，不依赖显示环境）"""

import src.theme as theme


def test_design_tokens_exist():
    assert theme.COLORS['primary'] == '#2F6FED'
    assert theme.SPACING['md'] == 12
    assert theme.resolve_font_family()


def test_status_colors_cover_all_statuses():
    for status in ['idle', 'running', 'blocked', 'waiting', 'changeover']:
        assert status in theme.STATUS_COLORS
        assert status in theme.STATUS_SOFT


def test_alert_icons_and_colors():
    for severity in ['critical', 'warning', 'info']:
        assert severity in theme.ALERT_ICONS
        assert severity in theme.ALERT_COLORS


def test_utils_uses_theme_tokens():
    from src.utils import get_alert_color, get_status_color

    assert get_status_color('running') == theme.STATUS_COLORS['running']
    assert get_status_color('running') == '#34C759'
    assert get_alert_color('critical') == theme.ALERT_COLORS['critical']
    assert get_alert_color('unknown') == '#CCCCCC'


def test_tooltip_class_available():
    assert hasattr(theme, 'ToolTip')
