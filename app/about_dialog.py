"""关于：对话框 + 可复用的内容 widget（供主窗口「关于」页内嵌）。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QWidget,
)

from app import APP_NAME, APP_VERSION, AUTHOR

__all__ = ["AboutDialog", "about_content_widget"]


def about_content_widget() -> QWidget:
    """返回包含应用信息的 widget，可嵌入主窗口页面或对话框。"""
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setSpacing(8)
    lay.setContentsMargins(20, 20, 20, 20)

    title = QLabel("秒薪浮窗")
    title.setObjectName("heading")
    title.setAlignment(Qt.AlignCenter)
    lay.addWidget(title)

    ver = QLabel(f"版本  v{APP_VERSION}")
    ver.setAlignment(Qt.AlignCenter)
    lay.addWidget(ver)

    desc = QLabel(
        "实时显示你的每秒薪水，让时间变得可见。\n\n"
        "按日历与法定节假日精确计算日薪/秒薪，\n"
        "桌面浮窗随时提醒：每一秒都在赚钱。"
    )
    desc.setWordWrap(True)
    desc.setAlignment(Qt.AlignCenter)
    lay.addWidget(desc)

    lay.addStretch()

    author = QLabel(f"作者：{AUTHOR}")
    author.setObjectName("resultBig")
    author.setAlignment(Qt.AlignCenter)
    lay.addWidget(author)
    return w


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(380, 320)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        content = about_content_widget()
        lay.addWidget(content)

        btn = QPushButton("确定")
        btn.setObjectName("primary")
        btn.clicked.connect(self.accept)
        lay.addWidget(btn)
