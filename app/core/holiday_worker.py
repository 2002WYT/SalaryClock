"""节假日联网后台 Worker（QThread）。

把阻塞的 requests.get 移出 GUI 线程，避免联网更新时界面卡死。
完成/失败后通过信号回主线程，由主窗口刷新日历与提示。
"""
from PySide6.QtCore import QObject, Signal

from app.core.holiday_provider import HolidayProvider

__all__ = ["HolidayFetchWorker"]


class HolidayFetchWorker(QObject):
    finished = Signal(dict, bool, str)  # mapping, ok, message

    def __init__(self, year: int, provider: HolidayProvider, parent=None):
        super().__init__(parent)
        self.year = year
        self.provider = provider

    def run(self) -> None:
        mapping, ok, msg = self.provider.fetch_with_status(self.year)
        self.finished.emit(mapping, ok, msg)
