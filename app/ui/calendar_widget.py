"""带状态色块的日历控件。

基于 QCalendarWidget，根据节假日数据为每天上色：
  普通工作日(默认底色) / 周末(灰) / 法定节假日(红) / 调休上班(橙)
仅保留左右箭头按钮翻月，禁用滚轮翻月。翻月时自动重新上色。
"""
from PySide6.QtCore import QDate, Qt, QObject, QEvent
from PySide6.QtGui import QTextCharFormat, QColor, QFont
from PySide6.QtWidgets import QCalendarWidget, QTableView

import datetime as dt

from app.core.calendar_model import (
    month_dates_with_status, STATUS_COLORS, count_legal_workdays,
    TODAY_BG, TODAY_FG, TODAY_POINT_SIZE,
)

__all__ = ["WorkCalendarWidget"]


class _WheelEater(QObject):
    """事件过滤器：吞掉子控件（导航栏月份选择器、表格视图）的滚轮事件，
    防止鼠标滚轮误触导致快速跳到其他月份。翻月只通过左右箭头按钮。"""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True  # 拦截，不传递
        return super().eventFilter(obj, event)


class WorkCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._holidays = {}

        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setSelectionMode(QCalendarWidget.SingleSelection)
        self.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)
        # 周日放在最左面（符合国内日历习惯）
        self.setFirstDayOfWeek(Qt.Sunday)

        # 表头文字在深色背景下保持可读
        nav_fmt = QTextCharFormat()
        nav_fmt.setForeground(QColor("#e6e6e6"))
        self.setHeaderTextFormat(nav_fmt)

        # 翻月时重绘色块
        self.currentPageChanged.connect(self._on_page_changed)

        # 禁用滚轮翻月：给导航栏与表格视图装事件过滤器
        self._wheel_eater = _WheelEater(self)
        navbar = self.findChild(QObject, "qt_calendar_navigationbar")
        if navbar is not None:
            navbar.installEventFilter(self._wheel_eater)
            # 月份选择器（QComboBox）单独拦截
            for child in navbar.findChildren(QObject):
                child.installEventFilter(self._wheel_eater)
        view = self.findChild(QTableView, "qt_calendar_calendarview")
        if view is not None:
            view.installEventFilter(self._wheel_eater)
            view.viewport().installEventFilter(self._wheel_eater)

    def set_holidays(self, holidays: dict) -> None:
        self._holidays = holidays or {}
        self._apply_formats(self.yearShown(), self.monthShown())

    def current_holidays(self) -> dict:
        return self._holidays

    def legal_workdays_of_current_page(self) -> int:
        return count_legal_workdays(self.yearShown(), self.monthShown(), self._holidays)

    def current_selection(self):
        """返回 (year, month) of the displayed page（用户翻到的月份）。"""
        return self.yearShown(), self.monthShown()

    # ---- internal ----
    def _on_page_changed(self):
        self._apply_formats(self.yearShown(), self.monthShown())

    def _apply_formats(self, year: int, month: int) -> None:
        today = dt.date.today()
        for d, status, name in month_dates_with_status(year, month, self._holidays):
            qd = QDate(d.year, d.month, d.day)
            fmt = QTextCharFormat()
            bg, fg = STATUS_COLORS.get(status, STATUS_COLORS["workday"])
            if d == today:
                # 今天：用独立醒目底色（覆盖状态底色）+ 白字 + 加粗放大字号，
                # 让「今天在哪一天」在任意月份都一眼可辨，美观且突出。
                fmt.setBackground(QColor(TODAY_BG))
                fmt.setForeground(QColor(TODAY_FG))
                fmt.setFontWeight(QFont.Bold)
                fmt.setFontPointSize(TODAY_POINT_SIZE)
                fmt.setFontFamily("Microsoft YaHei")
            else:
                fmt.setBackground(QColor(bg))
                fmt.setForeground(QColor(fg))
            self.setDateTextFormat(qd, fmt)
