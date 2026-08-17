"""系统托盘：图标、双击恢复主窗口、右键菜单（显示/退出）。"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush, QFont
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app import APP_NAME

__all__ = ["create_tray", "app_icon"]


def app_icon() -> QIcon:
    """优先加载 resources/icon.ico，否则程序化生成绿色 ¥ 图标。"""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ico_path = os.path.join(here, "resources", "icon.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)

    pix = QPixmap(64, 64)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor("#5dd97f")))
    p.setPen(Qt.NoPen)
    p.drawEllipse(6, 6, 52, 52)
    p.setPen(QColor("#10221a"))
    p.setFont(QFont("Arial", 28, QFont.Bold))
    p.drawText(pix.rect(), Qt.AlignCenter, "¥")
    p.end()
    return QIcon(pix)


def create_tray(main_window) -> QSystemTrayIcon:
    tray = QSystemTrayIcon(app_icon())
    tray.setToolTip(f"{APP_NAME}")

    menu = QMenu()
    act_show = QAction("显示主窗口", menu)
    act_show.triggered.connect(main_window.restore)
    menu.addAction(act_show)

    menu.addSeparator()

    act_quit = QAction("退出", menu)
    act_quit.triggered.connect(main_window._truly_quit)
    menu.addAction(act_quit)

    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda reason: main_window.restore()
        if reason == QSystemTrayIcon.DoubleClick else None
    )
    return tray
