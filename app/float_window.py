"""桌面浮窗。

无边框、半透明、可置顶；每秒刷新秒薪与今日已赚；右键菜单可调
不透明度 / 字体 / 置顶 / 锁定 / 关闭；可拖动、可缩放；状态自动记忆。
"""
import datetime as dt
import os

from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QAction, QMouseEvent, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMenu, QSlider,
    QWidgetAction, QSizeGrip, QApplication, QSpinBox,
)

from app.core.config import load_config, save_config
from app.core import calculator
from app.ui.styles import FLOAT_THEMES, build_float_qss, DEFAULT_FLOAT_THEME

__all__ = ["FloatWindow"]


class FloatWindow(QWidget):
    """payload: {"second_salary","daily_salary","time_groups"}"""

    closed = Signal()  # 浮窗关闭时通知控制器
    settingsChanged = Signal()  # 任一设置变化时发出，供主窗口反向同步控件

    def __init__(self, payload: dict):
        super().__init__()
        # 初始化期间resize会触发resizeEvent，但此时几何尚未恢复完，
        # 不应回写配置（否则锁定态启动会把存盘高度多加一个手柄高度）。
        self._initializing = True
        self.payload = payload
        self.config = load_config()
        f = self.config.get("float", {})

        # 状态
        self.locked = bool(f.get("locked", False))
        self.always_on_top = bool(f.get("always_on_top", True))
        self.opacity = float(f.get("opacity", 0.92))
        self.font_size = int(f.get("font_size", 30))
        self.font_family = f.get("font_family", "Microsoft YaHei")
        self.count_only_during_work = bool(f.get("count_only_during_work", True))
        self.show_today_earnings = bool(f.get("show_today_earnings", True))
        self.float_theme = f.get("theme") or DEFAULT_FLOAT_THEME

        self.second_salary = float(payload.get("second_salary", 0.0))
        self.daily_salary = float(payload.get("daily_salary", 0.0))
        self.time_groups = payload.get("time_groups", [])

        self._drag_offset = None
        self._today = dt.date.today()
        # 不透明度百分比标签（菜单复用，提前创建避免 _set_opacity 时不存在）
        self._op_value_lbl = None
        self.today_earnings = self._elapsed_work_seconds_today() * self.second_salary

        # 窗口标志：无边框 + 工具窗口(不出现在任务栏) + 置顶
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("FloatRoot")
        self.setMinimumSize(190, 96)

        self._build_ui()
        self._apply_font()
        self._apply_theme()
        self.setWindowOpacity(self.opacity)

        # 恢复几何：config 存的是「逻辑全高」（手柄可见时的高度）。
        # 若以锁定状态启动，需把窗口轮廓收起一个手柄高度，与运行中锁定表现一致。
        full_w = int(f.get("width", 260))
        full_h = int(f.get("height", 132))
        self.resize(full_w, full_h)
        self.grip.setVisible(not self.locked)
        if self.locked:
            gh = self._grip_row_height()
            if gh > 0:
                self.resize(full_w, max(self.minimumHeight(), full_h - gh))

        px, py = f.get("pos_x"), f.get("pos_y")
        if px is not None and py is not None:
            self.move(int(px), int(py))
        else:
            geo = QApplication.primaryScreen().availableGeometry()
            self.move(geo.right() - self.width() - 30, geo.bottom() - self.height() - 30)

        # 每秒刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self._tick()

        # 几何已恢复、UI 已就绪，此后用户的 resize 才回写配置
        self._initializing = False

    # ---------------- UI ----------------
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        self.lbl_salary = QLabel()
        self.lbl_salary.setObjectName("salaryLabel")
        self.lbl_salary.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_salary)

        self.lbl_today = QLabel()
        self.lbl_today.setObjectName("subLabel")
        self.lbl_today.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_today)

        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_status)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 0, 0, 0)
        grip_row.addStretch()
        self.grip = QSizeGrip(self)
        grip_row.addWidget(self.grip)
        lay.addLayout(grip_row)

    def _apply_style(self):
        """重建浮窗 QSS：主题色 + 字号都写进 QSS。

        字号不能靠 setFont(QFont(pointSize))——主窗口在 app 级设了
        QWidget{font-size:13px}，QSS 会覆盖 QFont，导致 set_font_size 无可见效果。
        这里把字号塞进 QLabel#id 规则（比 app 级 QWidget 更具体），才能生效。
        """
        self.setStyleSheet(build_float_qss(self.float_theme, self.font_size))

    def _apply_font(self):
        self._apply_style()

    def _apply_theme(self):
        self._apply_style()
        self.update()  # 触发 paintEvent 重绘底色

    def _theme_colors(self):
        """从当前浮窗主题解析出背景色与边框色（QColor）。"""
        t = FLOAT_THEMES.get(self.float_theme, FLOAT_THEMES[DEFAULT_FLOAT_THEME])
        return self._parse_rgba(t["bg"]), self._parse_rgba(t["border"])

    def _grip_row_height(self) -> int:
        """缩放手柄那一行占用的像素高度（含布局间距）。
        锁定时轮廓要收起这部分，解锁时加回来。"""
        h = self.grip.sizeHint().height()
        # grip_row 自身无 margin，但 QVBoxLayout 有 spacing(2)；取保底值，避免 0
        return max(h, 14)

    def _apply_click_through(self):
        """锁定时让鼠标点击穿透浮窗，直达下方的窗口/桌面内容。

        Qt 的 WA_TransparentForMouseEvents 只影响 Qt 内部事件派发，无法让点击
        穿到其他应用；必须叠加 Win32 的 WS_EX_TRANSPARENT——窗口管理器在命中
        测试时直接跳过本窗口，点击便落到 Z 序下方的东西上。WA_TranslucentBackground
        已保证窗口带 WS_EX_LAYERED，这是 WS_EX_TRANSPARENT 生效的前提。

        锁定后浮窗不再响应任何鼠标（不能拖、不能右键菜单），需解锁时回到主窗口
        浮窗设置页取消「锁定」（程序化调用 set_locked(False) 不受穿透影响）。"""
        on = self.locked
        self.setAttribute(Qt.WA_TransparentForMouseEvents, on)
        if os.name != "nt":
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.GetWindowLongW.restype = wintypes.LONG
            user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
            user32.SetWindowLongW.restype = wintypes.LONG
            hwnd = int(self.winId())
            if not hwnd:
                return
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex = (ex | WS_EX_TRANSPARENT) if on else (ex & ~WS_EX_TRANSPARENT)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        except Exception:
            pass  # 非窗口平台/无句柄（offscreen 测试），静默跳过

    @staticmethod
    def _parse_rgba(s: str) -> QColor:
        """'rgba(r,g,b,a)' -> QColor。解析失败回退到半透明黑。"""
        try:
            body = s[s.index("(") + 1:s.rindex(")")]
            r, g, b, a = [int(x) for x in body.split(",")]
            return QColor(r, g, b, a)
        except Exception:
            return QColor(0, 0, 0, 200)

    def paintEvent(self, _e):
        """WA_TranslucentBackground 下 QSS 的 background-color 不会绘制，
        这里手动画圆角底色 + 边框，让浮窗主题色真正显示出来；
        否则换任何主题都看不到底色（只有悬浮的文字）。"""
        bg, border = self._theme_colors()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setBrush(bg)
        p.setPen(QPen(border, 1))
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.drawRoundedRect(rect, 12, 12)
        p.end()

    def showEvent(self, e):
        super().showEvent(e)
        # 窗口首次显示，或 set_always_on_top 重建窗口标志后重新 show：
        # 原生窗口被（重新）创建，Win32 扩展样式随之丢失，需在此重应用穿透。
        # 幂等：未锁定时只是把属性/样式位清掉，无副作用。
        self._apply_click_through()

    # ---------------- 计时 ----------------
    def _elapsed_work_seconds_today(self) -> float:
        """估算今日已过去的工时秒数（用于初始累计，跨午夜为近似）。"""
        now = dt.datetime.now()
        nm = now.hour * 60 + now.minute + now.second / 60.0
        DAY = 24 * 60
        total = 0.0
        for g in self.time_groups:
            for p in g.get("periods", []):
                s = calculator.parse_time(p.get("start"))
                e = calculator.parse_time(p.get("end"))
                if s is None or e is None or e == s:
                    continue
                if e > s:  # 同日时段
                    if nm > s:
                        total += min(nm, e) - s
                else:  # 跨午夜 [s, DAY) + [0, e)
                    if nm >= s:
                        total += min(nm, DAY) - s
                    elif nm < e:
                        total += (DAY - s) + nm
                    else:  # 当日班次已结束
                        total += (DAY - s) + e
        return total * 60.0

    def _tick(self):
        now = dt.datetime.now()
        if now.date() != self._today:
            self._today = now.date()
            self.today_earnings = self._elapsed_work_seconds_today() * self.second_salary
        in_work = calculator.is_in_work_period(now.time(), self.time_groups)
        if in_work or not self.count_only_during_work:
            self.today_earnings += self.second_salary
        self._update_labels(in_work)

    def _update_labels(self, in_work: bool):
        self.lbl_salary.setText(f"每秒  {calculator.format_money(self.second_salary)}")
        if self.show_today_earnings:
            self.lbl_today.setText(f"今日已赚  {calculator.format_money_short(self.today_earnings)}")
        else:
            self.lbl_today.setText("")
        self.lbl_status.setText("● 工作中" if in_work else "○ 休息中")

    # ---------------- 拖动 ----------------
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton and not self.locked:
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_offset is not None and not self.locked:
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            e.accept()

    def mouseReleaseEvent(self, e: QMouseEvent):
        if self._drag_offset is not None:
            self._drag_offset = None
            self._save_float_config()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if getattr(self, "_initializing", False):
            return  # 构造期几何恢复，不回写
        self._save_float_config()

    # ---------------- 右键菜单 ----------------
    def _build_menu(self) -> "QMenu":
        menu = QMenu(self)
        menu.setObjectName("floatMenu")

        act_lock = QAction("锁定窗口" if not self.locked else "解锁窗口", self)
        act_lock.setCheckable(True)
        act_lock.setChecked(self.locked)
        act_lock.toggled.connect(self._toggle_lock)
        menu.addAction(act_lock)

        act_top = QAction("窗口置顶", self)
        act_top.setCheckable(True)
        act_top.setChecked(self.always_on_top)
        act_top.toggled.connect(self._toggle_top)
        menu.addAction(act_top)

        menu.addSeparator()

        # 不透明度：标题 + 滑块实时预览（拖动即生效）
        op_row = QWidget()
        op_lay = QHBoxLayout(op_row)
        op_lay.setContentsMargins(10, 4, 10, 2)
        op_lay.setSpacing(8)
        op_title = QLabel("不透明度")
        op_title.setObjectName("hint")
        if self._op_value_lbl is None:
            self._op_value_lbl = QLabel(f"{int(self.opacity * 100)}%")
            self._op_value_lbl.setObjectName("resultLabel")
        else:
            self._op_value_lbl.setParent(op_row)
            self._op_value_lbl.setText(f"{int(self.opacity * 100)}%")
        op_lay.addWidget(op_title)
        op_lay.addStretch()
        op_lay.addWidget(self._op_value_lbl)
        op_wa = QWidgetAction(menu)
        op_wa.setDefaultWidget(op_row)
        menu.addAction(op_wa)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(20, 100)
        slider.setValue(int(self.opacity * 100))
        slider.setMinimumWidth(180)
        slider.valueChanged.connect(self._set_opacity)
        wa = QWidgetAction(menu)
        wa.setDefaultWidget(slider)
        menu.addAction(wa)

        menu.addSeparator()

        # 浮窗主题：14 种
        theme_menu = menu.addMenu("浮窗主题")
        for key, t in FLOAT_THEMES.items():
            act_t = QAction(t["label"], self)
            act_t.setCheckable(True)
            act_t.setChecked(key == self.float_theme)
            act_t.triggered.connect(lambda _=False, k=key: self._set_float_theme(k))
            theme_menu.addAction(act_t)

        # 字体大小：直接选择数字（10-120），比放大/缩小更快
        fs_row = QWidget()
        fs_lay = QHBoxLayout(fs_row)
        fs_lay.setContentsMargins(10, 4, 10, 4)
        fs_lay.setSpacing(8)
        fs_title = QLabel("字号")
        fs_title.setObjectName("hint")
        fs_lay.addWidget(fs_title)
        fs_lay.addStretch()
        fs_spin = QSpinBox()
        fs_spin.setRange(10, 120)
        fs_spin.setValue(self.font_size)
        fs_spin.setSuffix(" px")
        fs_spin.setFixedWidth(96)
        fs_spin.valueChanged.connect(self.set_font_size)
        fs_lay.addWidget(fs_spin)
        fs_wa = QWidgetAction(menu)
        fs_wa.setDefaultWidget(fs_row)
        menu.addAction(fs_wa)

        menu.addSeparator()

        act_main = QAction("返回主菜单", self)
        act_main.triggered.connect(self._close_to_main)
        menu.addAction(act_main)

        act_close = QAction("关闭浮窗", self)
        act_close.triggered.connect(self._close)
        menu.addAction(act_close)
        return menu

    def contextMenuEvent(self, e):
        self._build_menu().exec(e.globalPos())

    # ---------------- 设置接口（主窗口与右键菜单共用）----------------
    # 每个 setter：更新状态 -> 应用到 UI -> 写盘 -> 发 settingsChanged 通知主窗口同步。
    # 设置相同时短路，避免无谓的重绘/信号循环。
    def set_theme(self, key: str):
        if key == self.float_theme:
            return
        self.float_theme = key
        self._apply_theme()
        self._save_float_config()
        self.settingsChanged.emit()

    def set_font_size(self, size: int):
        size = max(10, min(120, int(size)))
        if size == self.font_size:
            return
        self.font_size = size
        self._apply_font()
        self._save_float_config()
        self.settingsChanged.emit()

    def set_opacity(self, ratio: float):
        ratio = max(0.20, min(1.0, float(ratio)))
        if abs(ratio - self.opacity) < 1e-3:
            return
        self.opacity = ratio
        self.setWindowOpacity(self.opacity)
        lbl = getattr(self, "_op_value_lbl", None)
        if lbl is not None:
            lbl.setText(f"{int(round(ratio * 100))}%")
        self._save_float_config()
        self.settingsChanged.emit()

    def set_always_on_top(self, on: bool):
        if on == self.always_on_top:
            return
        self.always_on_top = on
        geo = self.geometry()  # setWindowFlags 会重建窗口，需保留几何
        flags = Qt.FramelessWindowHint | Qt.Tool
        if on:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setWindowOpacity(self.opacity)
        self.setGeometry(geo)
        self.show()
        self._save_float_config()
        self.settingsChanged.emit()

    def set_locked(self, on: bool):
        if on == self.locked:
            return
        self.locked = on
        # 锁定：隐藏右下角缩放手柄，并把窗口轮廓收起一个手柄高度——
        # 否则手柄隐去后留出的空白会被布局分给三行文字，把它们撑开（拉伸）。
        # 解锁：把手柄空间加回来，恢复原轮廓。resize 保留左上角，pos 不变。
        gh = self._grip_row_height()
        self.grip.setVisible(not self.locked)
        if gh > 0:
            cur = self.size()
            if on:
                self.resize(cur.width(), max(self.minimumHeight(), cur.height() - gh))
            else:
                self.resize(cur.width(), cur.height() + gh)
        # 锁定→鼠标穿透；解锁→恢复可交互
        self._apply_click_through()
        self._save_float_config()
        self.settingsChanged.emit()

    def set_show_today_earnings(self, on: bool):
        if on == self.show_today_earnings:
            return
        self.show_today_earnings = on
        self._save_float_config()
        self._update_labels(calculator.is_in_work_period(
            dt.datetime.now().time(), self.time_groups))
        self.settingsChanged.emit()

    def set_count_only_during_work(self, on: bool):
        if on == self.count_only_during_work:
            return
        self.count_only_during_work = on
        self._save_float_config()
        self.settingsChanged.emit()

    # ---------------- 菜单动作（委托给公共 setter）----------------
    def _toggle_lock(self, checked: bool):
        self.set_locked(checked)

    def _toggle_top(self, checked: bool):
        self.set_always_on_top(checked)

    def _set_opacity(self, val: int):
        self.set_opacity(val / 100.0)

    def _set_float_theme(self, key: str):
        self.set_theme(key)

    def _close_to_main(self):
        self._save_float_config()
        self.timer.stop()
        self.closed.emit()
        self.close()

    def _close(self):
        self._save_float_config()
        self.timer.stop()
        self.closed.emit()
        self.close()

    # ---------------- 持久化 ----------------
    def _save_float_config(self):
        # 存「逻辑全高」（手柄可见时的高度）：锁定态下窗口轮廓已收起手柄高度，
        # 这里把它加回去再落盘，避免下次以锁定状态启动时再减一次导致双收缩。
        cur_h = self.height()
        full_h = cur_h + self._grip_row_height() if self.locked else cur_h
        self.config.setdefault("float", {})
        self.config["float"].update({
            "opacity": self.opacity,
            "font_size": self.font_size,
            "always_on_top": self.always_on_top,
            "locked": self.locked,
            "pos_x": self.pos().x(),
            "pos_y": self.pos().y(),
            "width": self.width(),
            "height": full_h,
            "theme": self.float_theme,
        })
        save_config(self.config)

    def closeEvent(self, e):
        self._save_float_config()
        self.timer.stop()
        self.closed.emit()
        super().closeEvent(e)
