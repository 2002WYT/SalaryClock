"""秒薪浮窗 (SalaryClock) v0.0.1 —— 程序入口。

启动主菜单窗口与系统托盘；点击「启动浮窗」后创建桌面浮窗；
浮窗运行中按钮变为「关闭浮窗」，可随时关闭；浮窗关闭后主窗口保持可见。
"""
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.float_window import FloatWindow
from app.tray import create_tray, app_icon


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SalaryClock")
    app.setApplicationDisplayName("秒薪浮窗")
    # 托盘常驻：最后一个窗口隐藏也不退出
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())

    main_window = MainWindow(tray=None)

    tray = create_tray(main_window)
    main_window.tray = tray
    tray.show()

    float_holder = {"window": None}

    def set_launch_button(running: bool) -> None:
        btn = main_window.btn_launch
        if running:
            btn.setText("■  关闭浮窗")
            btn.setStyleSheet(
                "QPushButton#primary{background-color:#e0533d;border:none;font-weight:600;color:#fff;}"
                "QPushButton#primary:hover{background-color:#ec6350;}"
                "QPushButton#primary:pressed{background-color:#d04530;}"
            )
        else:
            btn.setText("▶  启动浮窗")
            btn.setStyleSheet("")  # 恢复主题默认样式

    def on_launch_or_close(payload=None) -> None:
        """按钮点击：未启动则启动，已启动则关闭。"""
        if float_holder["window"] is not None:
            # 关闭浮窗（保留主窗口可见）
            float_holder["window"]._close()
            return
        # 启动浮窗
        main_window._persist()
        p = payload if payload is not None else main_window._build_payload()
        if p is None:
            return
        fw = FloatWindow(p)
        fw.closed.connect(on_float_closed)
        # 双向同步：浮窗右键改设置 -> 回填主窗口控件
        fw.settingsChanged.connect(lambda: main_window.sync_float_controls_from(fw))
        fw.show()
        float_holder["window"] = fw
        main_window.float_window = fw  # 主窗口改设置 -> 实时下发到浮窗
        set_launch_button(True)
        main_window.showNormal()
        main_window.raise_()

    def on_float_closed() -> None:
        float_holder["window"] = None
        main_window.float_window = None
        set_launch_button(False)
        main_window.showNormal()
        main_window.raise_()
        main_window.activateWindow()

    # 启动按钮的信号改为通用切换
    main_window.btn_launch.clicked.disconnect()
    main_window.btn_launch.clicked.connect(lambda: on_launch_or_close())
    # 菜单/快捷键「启动浮窗」仍走带 payload 的路径（仅当未运行时）
    main_window.launchRequested.connect(on_launch_or_close)

    set_launch_button(False)
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
