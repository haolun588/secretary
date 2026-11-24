"""
ui/theme.py
深色精緻版主題 token（純資料，不 import PyQt6，方便測試）

用法範例：
    from ui.theme import qss, TOKENS

    style = qss('''
        QPushButton {
            background: {ACCENT};
            color: {TEXT_PRIMARY};
            border-radius: {RADIUS_MD}px;
            padding: {SPACE_2}px {SPACE_4}px;
            font-size: {FONT_SM}px;
        }
        QPushButton:hover { background: {ACCENT_HOVER}; }
    ''')
    widget.setStyleSheet(style)

規則：
- 只有 `{TOKEN_NAME}`（全大寫、數字、底線）會被替換，QSS 原本的 `{ }` 區塊保持不動。
- 數值 token（字級、間距、圓角）以整數字串代入，單位 `px` 由使用者自行撰寫。
- 未知 token 名稱會 raise KeyError。
- 可用關鍵字參數臨時覆寫：qss(template, ACCENT="#ff0000")。
"""

import re

# 背景與表面
BG = "#0f0f14"
SURFACE_1 = "#16161d"
SURFACE_2 = "#1d1d26"
SURFACE_3 = "#262631"

# 邊框
BORDER = "#2a2a35"
BORDER_STRONG = "#3a3a48"

# 文字
TEXT_PRIMARY = "#ececf1"
TEXT_SECONDARY = "#a1a1ae"
TEXT_MUTED = "#6b6b78"

# 主色
ACCENT = "#8b7cf6"
ACCENT_HOVER = "#7a6aef"
ACCENT_MUTED = "rgba(139,124,246,0.14)"

# 語意色
DANGER = "#e5484d"
SUCCESS = "#30a46c"
WARNING = "#f5a524"
PRIORITY = {"major": DANGER, "medium": WARNING, "minor": SUCCESS}

# 字型
FONT_FAMILY = "'Segoe UI', 'Microsoft JhengHei UI', sans-serif"
FONT_XS = 12
FONT_SM = 13
FONT_MD = 15
FONT_LG = 18
FONT_XL = 22
WEIGHT_REGULAR = 400
WEIGHT_SEMIBOLD = 600

# 間距
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 24
SPACE_6 = 32

# 圓角
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

_TOKEN_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

TOKENS = {
    _name: _value
    for _name, _value in list(globals().items())
    if _TOKEN_NAME_RE.match(_name) and isinstance(_value, (str, int))
}

_PLACEHOLDER_RE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def qss(template, **overrides):
    """將 QSS 範本中的 `{TOKEN_NAME}` 替換為 token 值；未知 token raise KeyError。"""
    values = {**TOKENS, **overrides}

    def _replace(match):
        name = match.group(1)
        if name not in values:
            raise KeyError(f"未知的主題 token: {name}")
        return str(values[name])

    return _PLACEHOLDER_RE.sub(_replace, template)
