"""自定义时间段分组编辑器。

支持任意数量的命名分组，每个分组下可添加多条 [开始-结束] 时段。
数据结构: [{"name": str, "periods": [{"start":"HH:mm","end":"HH:mm"}]}]
"""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTimeEdit,
    QFrame, QScrollArea, QLabel,
)
from PySide6.QtCore import QTime, Qt

__all__ = ["TimeGroupEditor", "PeriodRow", "GroupRow"]


def _parse_hhmm(s: str) -> QTime:
    try:
        h, m = (s or "09:00").split(":")
        return QTime(int(h), int(m))
    except (ValueError, AttributeError):
        return QTime(9, 0)


class PeriodRow(QWidget):
    """单条时段行：[开始] — [结束] [删除]。"""

    removeRequested = Signal()
    changed = Signal()

    def __init__(self, start: str = "09:00", end: str = "12:00", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 2, 2, 2)

        self.start_edit = QTimeEdit()
        self.start_edit.setDisplayFormat("HH:mm")
        self.start_edit.setTime(_parse_hhmm(start))

        self.end_edit = QTimeEdit()
        self.end_edit.setDisplayFormat("HH:mm")
        self.end_edit.setTime(_parse_hhmm(end))

        dash = QLabel("—")
        dash.setStyleSheet("color:#888;")

        del_btn = QPushButton("删除")
        del_btn.setObjectName("danger")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(self.removeRequested)

        lay.addWidget(self.start_edit)
        lay.addWidget(dash)
        lay.addWidget(self.end_edit)
        lay.addWidget(del_btn)
        lay.addStretch()

        # 关键：编辑时间立即触发 changed，向上冒泡以重算
        self.start_edit.timeChanged.connect(self.changed)
        self.end_edit.timeChanged.connect(self.changed)

    def value(self) -> dict:
        return {
            "start": self.start_edit.time().toString("HH:mm"),
            "end": self.end_edit.time().toString("HH:mm"),
        }


class GroupRow(QFrame):
    """单个分组：名称 + 多条时段 + 增删。"""

    removeRequested = Signal(object)  # emits self
    changed = Signal()

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("groupRow")
        self.setFrameShape(QFrame.NoFrame)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        name_lbl = QLabel("分组名:")
        self.name_edit = QLineEdit(data.get("name", "分组") or "分组")
        self.name_edit.setMaximumWidth(140)
        self.name_edit.setPlaceholderText("分组名")
        self.name_edit.textChanged.connect(self.changed)

        del_group = QPushButton("删除分组")
        del_group.setObjectName("danger")
        del_group.clicked.connect(self._request_remove_self)

        header.addWidget(name_lbl)
        header.addWidget(self.name_edit)
        header.addStretch()
        header.addWidget(del_group)
        outer.addLayout(header)

        self._periods_layout = QVBoxLayout()
        self._periods_layout.setSpacing(2)
        outer.addLayout(self._periods_layout)

        self.period_rows = []
        periods = data.get("periods") or [{"start": "09:00", "end": "12:00"}]
        if not periods:
            periods = [{"start": "09:00", "end": "12:00"}]
        for p in periods:
            self.add_period(p.get("start", "09:00"), p.get("end", "12:00"))

        add_p = QPushButton("+ 添加时段")
        add_p.clicked.connect(lambda: self.add_period("09:00", "18:00"))
        outer.addWidget(add_p)

    removeRequested = Signal(object)  # emits self

    def _request_remove_self(self):
        self.removeRequested.emit(self)

    def add_period(self, start: str, end: str) -> None:
        row = PeriodRow(start, end, self)
        row.removeRequested.connect(lambda r=row: self._remove_period(r))
        row.changed.connect(self.changed)
        self._periods_layout.addWidget(row)
        self.period_rows.append(row)
        self.changed.emit()

    def _remove_period(self, row: PeriodRow) -> None:
        self._periods_layout.removeWidget(row)
        row.setParent(None)
        if row in self.period_rows:
            self.period_rows.remove(row)
        row.deleteLater()
        self.changed.emit()

    def value(self) -> dict:
        return {
            "name": self.name_edit.text().strip() or "分组",
            "periods": [p.value() for p in self.period_rows],
        }


class TimeGroupEditor(QWidget):
    """外层编辑器：滚动列表 + 添加分组。"""

    groupsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        title = QLabel("工作时间段")
        title.setObjectName("heading")
        top.addWidget(title)
        top.addStretch()
        add_group = QPushButton("+ 添加分组")
        add_group.setObjectName("primary")
        add_group.clicked.connect(lambda: self.add_group())
        top.addWidget(add_group)
        outer.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("groupContainer")
        self.groups_layout = QVBoxLayout(inner)
        self.groups_layout.setContentsMargins(0, 4, 0, 0)
        self.groups_layout.setSpacing(8)
        self.groups_layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        self.group_rows: list[GroupRow] = []

    def set_time_groups(self, groups: list) -> None:
        for r in self.group_rows:
            r.setParent(None)
            r.deleteLater()
        self.group_rows = []
        for g in (groups or []):
            self.add_group(g)
        if not self.group_rows:
            self.add_group()

    def add_group(self, data: dict | None = None) -> None:
        if data is None:
            data = {"name": "新分组", "periods": [{"start": "09:00", "end": "12:00"}]}
        row = GroupRow(data, self)
        row.removeRequested.connect(self._remove_group)
        row.changed.connect(self.groupsChanged)
        # 插在 stretch 之前
        self.groups_layout.insertWidget(self.groups_layout.count() - 1, row)
        self.group_rows.append(row)
        self.groupsChanged.emit()

    def _remove_group(self, row: GroupRow) -> None:
        self.groups_layout.removeWidget(row)
        row.setParent(None)
        if row in self.group_rows:
            self.group_rows.remove(row)
        row.deleteLater()
        self.groupsChanged.emit()

    def get_time_groups(self) -> list:
        return [r.value() for r in self.group_rows]
