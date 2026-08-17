"""设置对话框：常规选项 + 浮窗默认参数 + 开机自启。"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox,
    QCheckBox, QDialogButtonBox, QGroupBox, QWidget, QVBoxLayout as _QVBL,
    QButtonGroup, QRadioButton,
)

from app.core.config import save_config

__all__ = ["SettingsDialog"]


class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setMinimumWidth(440)

        outer = QVBoxLayout(self)

        # 常规
        g1 = QGroupBox("常规")
        f1 = QFormLayout()
        self.spin_default_workdays = QDoubleSpinBox()
        self.spin_default_workdays.setRange(1, 31)
        self.spin_default_workdays.setDecimals(2)
        self.spin_default_workdays.setValue(
            float(config.get("settings", {}).get("default_legal_workdays", 21.75))
        )
        f1.addRow("法定工作日降级默认值：", self.spin_default_workdays)

        # 关闭行为：退出 / 最小化到托盘（单选，与主窗口设置页一致）
        s = config.get("settings", {})
        close_row = QWidget()
        cl = _QVBL(close_row); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(2)
        self._close_group = QButtonGroup(self)
        self.rb_quit = QRadioButton("直接退出程序")
        self.rb_tray = QRadioButton("最小化到托盘")
        self._close_group.addButton(self.rb_quit)
        self._close_group.addButton(self.rb_tray)
        cb = s.get("close_behavior")
        if cb is None:  # 兼容旧版 minimize_to_tray
            cb = "tray" if s.get("minimize_to_tray", True) else "quit"
        (self.rb_tray if cb == "tray" else self.rb_quit).setChecked(True)
        cl.addWidget(self.rb_quit); cl.addWidget(self.rb_tray)
        f1.addRow("关闭主窗口时：", close_row)

        self.chk_autostart = QCheckBox("开机自动启动")
        self.chk_autostart.setChecked(bool(config.get("settings", {}).get("auto_start", False)))
        f1.addRow(self.chk_autostart)
        g1.setLayout(f1)
        outer.addWidget(g1)

        # 浮窗默认
        g2 = QGroupBox("浮窗默认")
        f2 = QFormLayout()
        fl = config.get("float", {})

        self.spin_font = QSpinBox()
        self.spin_font.setRange(10, 120)
        self.spin_font.setValue(int(fl.get("font_size", 30)))
        f2.addRow("默认字号：", self.spin_font)

        self.chk_top = QCheckBox("默认置顶")
        self.chk_top.setChecked(bool(fl.get("always_on_top", True)))
        f2.addRow(self.chk_top)

        self.chk_count = QCheckBox("仅在工作时段内累计「今日已赚」")
        self.chk_count.setChecked(bool(fl.get("count_only_during_work", True)))
        f2.addRow(self.chk_count)

        self.chk_show_earn = QCheckBox("显示「今日已赚」")
        self.chk_show_earn.setChecked(bool(fl.get("show_today_earnings", True)))
        f2.addRow(self.chk_show_earn)
        g2.setLayout(f2)
        outer.addWidget(g2)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._on_accept)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)

    def _on_accept(self):
        self.config.setdefault("settings", {})
        self.config["settings"]["default_legal_workdays"] = self.spin_default_workdays.value()
        close_behavior = "tray" if self.rb_tray.isChecked() else "quit"
        self.config["settings"]["close_behavior"] = close_behavior
        self.config["settings"]["minimize_to_tray"] = close_behavior == "tray"  # 兼容旧读取路径
        self.config["settings"]["auto_start"] = self.chk_autostart.isChecked()

        self.config.setdefault("float", {})
        self.config["float"]["font_size"] = self.spin_font.value()
        self.config["float"]["always_on_top"] = self.chk_top.isChecked()
        self.config["float"]["count_only_during_work"] = self.chk_count.isChecked()
        self.config["float"]["show_today_earnings"] = self.chk_show_earn.isChecked()

        self._apply_autostart(self.chk_autostart.isChecked())
        save_config(self.config)
        self.accept()

    @staticmethod
    def _apply_autostart(enable: bool) -> None:
        """通过注册表 HKCU\\...\\Run 注册/取消开机自启（仅 Windows）。"""
        try:
            import sys
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            if enable:
                if getattr(sys, "frozen", False):
                    path = f'"{sys.executable}"'
                else:
                    import os
                    path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                winreg.SetValueEx(key, "SalaryClock", 0, winreg.REG_SZ, path)
            else:
                try:
                    winreg.DeleteValue(key, "SalaryClock")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except OSError:
            pass  # 非 Windows 或权限不足，静默跳过
