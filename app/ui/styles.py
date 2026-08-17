"""主题化样式层。

主窗口主题 THEMES（14 种）与浮窗主题 FLOAT_THEMES（14 种）。
build_qss(theme_key) / build_float_qss(theme_key) 按主题生成 QSS。
"""
from app import APP_NAME, APP_VERSION, AUTHOR

__all__ = [
    "THEMES", "FLOAT_THEMES", "DEFAULT_THEME", "DEFAULT_FLOAT_THEME",
    "build_qss", "build_float_qss", "window_title", "author_line",
]

DEFAULT_THEME = "midnight"
DEFAULT_FLOAT_THEME = "f_dark_green"

# ---- 主窗口主题：每条含 bg/panel/item/border/text/sub/accent 系列 ----
THEMES = {
    "midnight": {"label": "午夜蓝", "bg": "#1e1f26", "panel": "#23252e", "item": "#2d2f3a", "border": "#3a3d4a", "text": "#e6e6e6", "sub": "#888888", "accent": "#4a9eff", "accent_h": "#5aabff", "accent_p": "#3a8eee"},
    "forest":   {"label": "森林",   "bg": "#161e1a", "panel": "#1d2823", "item": "#26342c", "border": "#33443a", "text": "#e6f0ea", "sub": "#8aa090", "accent": "#5dd97f", "accent_h": "#6ee890", "accent_p": "#4cc86e"},
    "sunset":   {"label": "暖橙",   "bg": "#241d18", "panel": "#2d241d", "item": "#382c23", "border": "#4a3a2d", "text": "#f0e6dc", "sub": "#a89080", "accent": "#ffa940", "accent_h": "#ffb555", "accent_p": "#f0992e"},
    "sakura":   {"label": "樱粉",   "bg": "#241a1f", "panel": "#2d1f26", "item": "#382730", "border": "#4a3340", "text": "#f0dce2", "sub": "#a88090", "accent": "#ff6b9d", "accent_h": "#ff7ba8", "accent_p": "#f05b8d"},
    "violet":   {"label": "紫罗兰", "bg": "#1e1826", "panel": "#271f30", "item": "#322840", "border": "#42344f", "text": "#e8dcee", "sub": "#9080a0", "accent": "#b574ff", "accent_h": "#c284ff", "accent_p": "#a564ef"},
    "teal":     {"label": "青碧",   "bg": "#101e1f", "panel": "#182828", "item": "#1f3434", "border": "#2d4545", "text": "#dceeea", "sub": "#80a098", "accent": "#2dd4bf", "accent_h": "#3ae0cc", "accent_p": "#1ec8b3"},
    "crimson":  {"label": "烈红",   "bg": "#24181a", "panel": "#2d1f22", "item": "#38272b", "border": "#4a3438", "text": "#f0dcde", "sub": "#a88085", "accent": "#ff5c5c", "accent_h": "#ff6c6c", "accent_p": "#ef4c4c"},
    "gold":     {"label": "金黄",   "bg": "#242018", "panel": "#2d2820", "item": "#383228", "border": "#4a4232", "text": "#f0eadc", "sub": "#a89880", "accent": "#ffd54a", "accent_h": "#ffe05a", "accent_p": "#f0c53a"},
    "indigo":   {"label": "靛蓝",   "bg": "#181c2e", "panel": "#1f2438", "item": "#282f48", "border": "#343c57", "text": "#dce0f0", "sub": "#8088a8", "accent": "#6366f1", "accent_h": "#7376f2", "accent_p": "#5356d1"},
    "mint":     {"label": "薄荷",   "bg": "#16221d", "panel": "#1d2c25", "item": "#263830", "border": "#334a40", "text": "#dceee6", "sub": "#80a090", "accent": "#6ee7b7", "accent_h": "#7eeec0", "accent_p": "#5ee0ab"},
    "lake":     {"label": "湖蓝",   "bg": "#161e24", "panel": "#1d2730", "item": "#26333d", "border": "#33444f", "text": "#dce8f0", "sub": "#809098", "accent": "#38bdf8", "accent_h": "#48c5f9", "accent_p": "#28b0e8"},
    "graphite": {"label": "石墨",   "bg": "#1c1d20", "panel": "#23252a", "item": "#2c2e33", "border": "#3a3d44", "text": "#e0e0e0", "sub": "#888888", "accent": "#94a3b8", "accent_h": "#a4b3c8", "accent_p": "#8493a8"},
    "snow":     {"label": "素白",   "bg": "#f4f5f8", "panel": "#ffffff", "item": "#e8eaf0", "border": "#d0d4dc", "text": "#1a1c22", "sub": "#6a6e78", "accent": "#1a73e8", "accent_h": "#2a83f0", "accent_p": "#0a63d8"},
    "paper":    {"label": "米纸",   "bg": "#f5f1e8", "panel": "#fffaf0", "item": "#ece5d4", "border": "#d8cdb4", "text": "#3a3225", "sub": "#7a7060", "accent": "#b8862b", "accent_h": "#c8923a", "accent_p": "#a8761b"},
}


def build_qss(theme_key: str) -> str:
    t = THEMES.get(theme_key, THEMES[DEFAULT_THEME])
    bg, panel, item, border = t["bg"], t["panel"], t["item"], t["border"]
    text, sub = t["text"], t["sub"]
    acc, acc_h, acc_p = t["accent"], t["accent_h"], t["accent_p"]
    is_light = theme_key in ("snow", "paper")
    tooltip_bg = "#2a2c35" if is_light else panel
    return f"""
QWidget {{ background-color: {bg}; color: {text}; font-family: "Microsoft YaHei","Segoe UI",sans-serif; font-size: 13px; }}
QDialog {{ background-color: {bg}; }}
QPushButton {{ background-color: {item}; border: 1px solid {border}; border-radius: 5px; padding: 6px 14px; color: {text}; }}
QPushButton:hover {{ background-color: {border}; }}
QPushButton:pressed {{ background-color: {panel}; }}
QPushButton:disabled {{ color: {sub}; background-color: {panel}; }}
QPushButton#primary {{ background-color: {acc}; border: none; font-weight: 600; color: #ffffff; }}
QPushButton#primary:hover {{ background-color: {acc_h}; }}
QPushButton#primary:pressed {{ background-color: {acc_p}; }}
QPushButton#danger {{ color: #ff6b6b; }}
QLineEdit,QSpinBox,QDoubleSpinBox,QTimeEdit,QComboBox {{
    background-color: {panel}; border: 1px solid {border}; border-radius: 4px; padding: 4px 6px;
    color: {text}; selection-background-color: {acc};
}}
QLineEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus,QTimeEdit:focus,QComboBox:focus {{ border-color: {acc}; }}
/* 纯文本输入框：内边距均匀 */
QLineEdit {{ padding: 5px 8px; }}
/* 带上下箭头的数字/时间框：右侧留出按钮空间，避免文字盖住箭头 */
QSpinBox,QDoubleSpinBox,QTimeEdit {{ padding: 5px 22px 5px 8px; }}
/* 箭头按钮：加宽加底色，提升可点击区域。
   注意：一旦给主体加了 border，Qt 就进入 QSS 样式化模式，原生箭头会消失，
   所以必须用 ::up-arrow/::down-arrow 的 border 技巧显式画三角形箭头。 */
QSpinBox::up-button,QDoubleSpinBox::up-button,QTimeEdit::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    width: 18px; border-left: 1px solid {border}; border-bottom: 1px solid {border};
    background: {item}; border-top-right-radius: 4px;
}}
QSpinBox::down-button,QDoubleSpinBox::down-button,QTimeEdit::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 18px; border-left: 1px solid {border};
    background: {item}; border-bottom-right-radius: 4px;
}}
QSpinBox::up-button:hover,QDoubleSpinBox::up-button:hover,QTimeEdit::up-button:hover,
QSpinBox::down-button:hover,QDoubleSpinBox::down-button:hover,QTimeEdit::down-button:hover {{
    background: {border}; }}
QSpinBox::up-button:pressed,QDoubleSpinBox::up-button:pressed,QTimeEdit::up-button:pressed,
QSpinBox::down-button:pressed,QDoubleSpinBox::down-button:pressed,QTimeEdit::down-button:pressed {{
    background: {acc}; }}
/* 用 border 技巧画实心三角箭头，颜色随主题文字色，深浅主题都可见 */
QSpinBox::up-arrow,QDoubleSpinBox::up-arrow,QTimeEdit::up-arrow {{
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 5px solid {text}; width: 0; height: 0;
}}
QSpinBox::down-arrow,QDoubleSpinBox::down-arrow,QTimeEdit::down-arrow {{
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {text}; width: 0; height: 0;
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background-color: {panel}; border: 1px solid {border}; selection-background-color: {acc}; color: {text}; }}
QGroupBox {{ border: 1px solid {border}; border-radius: 6px; margin-top: 14px; padding-top: 10px; font-weight: 600; color: {text}; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
QFrame#groupRow {{ background-color: {panel}; border: 1px solid {border}; border-radius: 6px; }}
QFrame#statCell {{ background-color: {panel}; border: 1px solid {border}; border-radius: 8px; }}
QLabel#heading {{ font-size: 16px; font-weight: 700; }}
QLabel#resultLabel {{ font-size: 15px; font-weight: 600; color: {acc}; }}
QLabel#resultBig {{ font-size: 22px; font-weight: 700; color: {acc}; }}
QLabel#hint {{ color: {sub}; font-size: 12px; }}
QLabel#navTitle {{ font-size: 15px; font-weight: 700; color: {text}; padding: 8px; }}
QMenu {{ background-color: {panel}; border: 1px solid {border}; color: {text}; }}
QMenu::item {{ padding: 6px 22px; }}
QMenu::item:selected {{ background-color: {acc}; color: #ffffff; }}
QMenu::separator {{ height: 1px; background: {border}; }}
QListWidget#sidebar {{ background-color: {panel}; border: none; outline: none; }}
QListWidget#sidebar::item {{ padding: 14px 18px; color: {sub}; border-left: 3px solid transparent; }}
QListWidget#sidebar::item:selected {{ background-color: {bg}; color: {acc}; border-left: 3px solid {acc}; font-weight: 600; }}
QListWidget#sidebar::item:hover {{ background-color: {item}; }}
QScrollBar:vertical {{ background: {bg}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height: 0; }}
QCalendarWidget {{ background-color: {panel}; }}
QCalendarWidget QAbstractItemView {{
    alternate-background-color: {panel}; background-color: {bg};
    selection-background-color: {acc}; selection-color: #ffffff;
    border: 1px solid {border}; border-radius: 4px;
}}
QCalendarWidget QAbstractItemView::item {{ padding: 6px 0px; margin: 0px; }}
QCalendarWidget QAbstractItemView::item:hover {{ background-color: {item}; }}
QCalendarWidget QWidget#navigationWidget {{ background-color: {panel}; color: {text}; }}
QCalendarWidget QToolButton {{
    background-color: transparent; border: none; border-radius: 4px;
    color: {text}; padding: 4px 8px; margin: 2px;
}}
QCalendarWidget QToolButton:hover {{ background-color: {item}; color: {acc}; }}
QCalendarWidget QToolButton:pressed {{ background-color: {border}; }}
#qt_calendar_prevmonth {{ qproperty-icon: none; }}
#qt_calendar_nextmonth {{ qproperty-icon: none; }}
QCalendarWidget QSpinBox {{ background-color: {panel}; border: none; color: {text}; }}
QCalendarWidget QSpinBox::up-button,QCalendarWidget QSpinBox::down-button {{ width: 0px; height: 0px; }}
QCalendarWidget QSpinBox::up-arrow,QCalendarWidget QSpinBox::down-arrow {{ width: 0px; height: 0px; }}
QToolTip {{ background-color: {tooltip_bg}; color: {text}; border: 1px solid {border}; }}
QStatusBar {{ background-color: {panel}; color: {sub}; }}
"""


# ---- 浮窗主题：14 种（12 暗 + 2 亮），每条含 bg(number)/number/sub/status/border ----
_FLOAT_DARK = [
    ("green",   "暗夜翠", "#5dd97f", "18,28,22"),
    ("blue",    "暗夜蓝", "#4a9eff", "18,22,30"),
    ("orange",  "暗夜橙", "#ffa940", "28,22,16"),
    ("pink",    "暗夜粉", "#ff6b9d", "28,18,24"),
    ("violet",  "暗夜紫", "#b574ff", "22,18,30"),
    ("teal",    "暗夜青", "#2dd4bf", "14,26,26"),
    ("red",     "暗夜红", "#ff5c5c", "28,18,20"),
    ("gold",    "暗夜金", "#ffd54a", "28,24,16"),
    ("indigo",  "暗夜靛", "#818cf8", "18,20,32"),
    ("mint",    "暗夜薄荷","#6ee7b7", "16,26,21"),
    ("lake",    "暗夜湖", "#38bdf8", "16,22,28"),
    ("graphite","暗夜墨", "#94a3b8", "26,26,28"),
]
FLOAT_THEMES = {}
for _k, _label, _color, _rgb in _FLOAT_DARK:
    FLOAT_THEMES[f"f_dark_{_k}"] = {
        "label": _label,
        "bg": f"rgba({_rgb},235)",
        "number": _color,
        "sub": "#b0b3c0",
        "status": "#888888",
        "border": f"rgba(80,84,100,180)",
    }
# 两个亮色浮窗
FLOAT_THEMES["f_light_snow"] = {
    "label": "素白", "bg": "rgba(245,246,250,238)", "number": "#1a73e8",
    "sub": "#555860", "status": "#9098a0", "border": "rgba(200,204,214,200)",
}
FLOAT_THEMES["f_light_paper"] = {
    "label": "米纸", "bg": "rgba(250,246,236,238)", "number": "#b8862b",
    "sub": "#5a5040", "status": "#908674", "border": "rgba(208,200,178,200)",
}


def build_float_qss(theme_key: str, font_size: int = 30) -> str:
    t = FLOAT_THEMES.get(theme_key, FLOAT_THEMES[DEFAULT_FLOAT_THEME])
    number, sub, status, border = t["number"], t["sub"], t["status"], t["border"]
    fs = max(10, int(font_size))
    # 字号必须写进 QSS：主窗口在 app 级设了 QWidget{font-size:13px}，会覆盖
    # setFont() 的 pointSize（QSS 优先级高于 QFont）。这里用 QLabel#id 选择器，
    # 比 app 级的 QWidget 更具体，才能让浮窗字号真正生效。
    # 三行文字（秒薪 / 今日已赚 / 状态）统一使用同一字号，仅靠颜色区分。
    return f"""
/* #FloatRoot 的圆角底色 + 边框由 FloatWindow.paintEvent 绘制
   （WA_TranslucentBackground 下 QSS background-color 不生效） */
QLabel#salaryLabel {{ color: {number}; font-size: {fs}px; font-weight: 700;
    font-family: "Microsoft YaHei","Segoe UI",sans-serif; }}
QLabel#subLabel {{ color: {sub}; font-size: {fs}px;
    font-family: "Microsoft YaHei","Segoe UI",sans-serif; }}
QLabel#statusLabel {{ color: {status}; font-size: {fs}px;
    font-family: "Microsoft YaHei","Segoe UI",sans-serif; }}
QToolButton {{ background: transparent; border: none; color: {sub}; padding: 2px 4px; }}
QToolButton:hover {{ color: {number}; }}
QSlider::groove:horizontal {{ height: 4px; background: {border}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {number}; width: 12px; margin: -5px 0; border-radius: 6px; }}
"""


def window_title() -> str:
    return f"秒薪浮窗 v{APP_VERSION}"


def author_line() -> str:
    return f"作者：{AUTHOR}"
