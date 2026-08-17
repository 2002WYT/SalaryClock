"""主窗口：左侧栏目导航 + 右侧内容页 + 底部常驻结果栏。

栏目：薪资 / 日期 / 工作时间 / 基本设置 / 浮窗 / 关于
计算结果实时更新；主题可切换；节假日联网走后台线程不阻塞。
"""
import datetime as dt

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QGroupBox, QFormLayout, QMessageBox, QSplitter,
    QApplication, QListWidget, QListWidgetItem, QStackedWidget,
    QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox as _QDSB, QFrame,
    QSlider, QButtonGroup, QRadioButton,
)

from app.core.config import load_config, save_config
from app.core.holiday_provider import HolidayProvider
from app.core.holiday_worker import HolidayFetchWorker
from app.core.calendar_model import count_legal_workdays
from app.core import calculator
from app.ui.calendar_widget import WorkCalendarWidget
from app.ui.time_group_editor import TimeGroupEditor
from app.ui.styles import build_qss, THEMES, FLOAT_THEMES, window_title, DEFAULT_THEME

__all__ = ["MainWindow"]

NAV = ["薪资", "日期", "工作时间", "基本设置", "浮窗", "关于"]


class MainWindow(QMainWindow):
    launchRequested = Signal(dict)

    def __init__(self, tray=None):
        super().__init__()
        self.tray = tray
        self.config = load_config()
        self.holidays_provider = HolidayProvider()
        self._holiday_thread = None
        self._holiday_worker = None
        # 待拉取队列：拉取期间又请求了别的年份时，记下最后一个，等当前线程
        # 真正结束后再补拉（避免并发拉取互相打架，也避免 quit 后 isRunning 仍为真的竞态）。
        self._pending_fetch = None  # (year, silent) 或 None
        self._holiday_fetch_silent = False  # 当前/最近一次拉取是否静默（不弹框/不碰按钮）
        # 运行中浮窗的引用（由 main.py 在启动/关闭时设置）；用于双向同步
        self.float_window = None
        # 同步互斥：避免主窗口↔浮窗相互回写控件值造成信号递归
        self._syncing = False

        self.setWindowTitle(window_title())
        self.setMinimumSize(960, 640)

        self._build_menu()
        self._build_ui()
        self._apply_theme_to_self()
        self._load_config_into_ui()
        self._refresh_holidays_silent()
        self._recompute()

    # ---------------- 主题 ----------------
    @property
    def theme_key(self) -> str:
        return self.config.get("theme") or DEFAULT_THEME

    def _apply_theme_to_self(self):
        QApplication.instance().setStyleSheet(build_qss(self.theme_key))

    def _change_theme(self, key: str):
        self._patch_config(theme=key)
        self._apply_theme_to_self()

    def _patch_config(self, **patches) -> None:
        """写回主窗口负责的配置字段，同时保留磁盘上浮窗运行时写入的状态
        （位置 / 不透明度 / 锁定 / 尺寸 / 浮窗主题等）。

        主窗口的内存 config 是启动时的快照，若直接整段写回会覆盖浮窗在
        本次运行中保存的位置等字段。这里先读取磁盘最新配置，只按键合并
        主窗口拥有的字段，避免「过期副本」冲掉浮窗位置。
        """
        cfg = load_config()
        for k, v in patches.items():
            if k in ("float", "settings") and isinstance(v, dict):
                cfg.setdefault(k, {}).update(v)  # 键级合并，保留段内其余字段
            else:
                cfg[k] = v
        save_config(cfg)
        self.config = cfg  # 同步内存副本，后续读取不再过期

    # ---------------- 菜单栏 ----------------
    def _build_menu(self):
        mb = self.menuBar()
        m_file = mb.addMenu("文件(&F)")
        a = QAction("启动浮窗", self); a.setShortcut("Ctrl+S"); a.triggered.connect(self._on_launch)
        m_file.addAction(a); m_file.addSeparator()
        q = QAction("退出", self); q.triggered.connect(self._truly_quit); m_file.addAction(q)

        m_help = mb.addMenu("帮助(&H)")
        a = QAction("关于", self); a.triggered.connect(lambda: self._goto("关于"))
        m_help.addAction(a)

    # ---------------- UI ----------------
    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左侧栏
        sidebar = QWidget()
        sidebar.setObjectName("sidebarWrap")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)
        title = QLabel(" 秒薪浮窗")
        title.setObjectName("navTitle")
        sb_lay.addWidget(title)

        self.nav = QListWidget()
        self.nav.setObjectName("sidebar")
        self.nav.setFixedWidth(168)
        for name in NAV:
            QListWidgetItem(name, self.nav)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self._on_nav_changed)
        sb_lay.addWidget(self.nav, 1)
        root.addWidget(sidebar)

        # 右侧内容栈
        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_salary())
        self.stack.addWidget(self._page_date())
        self.stack.addWidget(self._page_worktime())
        self.stack.addWidget(self._page_settings())
        self.stack.addWidget(self._page_float())
        self.stack.addWidget(self._page_about())
        root.addWidget(self.stack, 1)

        # 底部常驻：结果 + 启动
        self.bottom = self._build_bottom()
        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)
        right_col.addWidget(self.stack, 1)
        right_col.addWidget(self.bottom)
        right_wrap = QWidget(); right_wrap.setLayout(right_col)
        root.addWidget(right_wrap, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("就绪")

    # ---- 各页 ----
    def _page_salary(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(12)
        lay.addWidget(self._heading("薪资"))

        # ---- 薪资参数 ----
        box = QGroupBox("薪资参数")
        form = QFormLayout()
        form.setSpacing(8)
        self.spin_salary = QDoubleSpinBox()
        self.spin_salary.setRange(0, 10_000_000)
        self.spin_salary.setDecimals(2)
        self.spin_salary.setSingleStep(100)
        self.spin_salary.setSuffix(" 元")
        self.spin_salary.setGroupSeparatorShown(True)
        self.spin_salary.setMinimumWidth(240)
        self.spin_salary.valueChanged.connect(self._recompute)
        form.addRow("月薪：", self.spin_salary)
        # 折合年薪（派生只读显示）
        self.lbl_yearly = QLabel("¥0.00")
        self.lbl_yearly.setObjectName("resultLabel")
        form.addRow("折合年薪：", self.lbl_yearly)
        box.setLayout(form)
        lay.addWidget(box)

        # ---- 快捷档位 ----
        quick = QGroupBox("快捷档位（点击套用）")
        ql = QHBoxLayout()
        for amount, lab in (
            (3000, "3K"), (5000, "5K"), (8000, "8K"), (10000, "1W"),
            (15000, "1.5W"), (20000, "2W"), (30000, "3W"), (50000, "5W"),
        ):
            b = QPushButton(lab)
            b.clicked.connect(lambda *_, a=amount: self.spin_salary.setValue(a))
            ql.addWidget(b)
        ql.addStretch()
        quick.setLayout(ql)
        lay.addWidget(quick)

        # ---- 秒薪速览卡 ----
        card = QGroupBox("秒薪速览")
        cl = QVBoxLayout()
        cl.setSpacing(10)
        self.lbl_preview_second = QLabel("¥0.0000 / 秒")
        self.lbl_preview_second.setObjectName("resultBig")
        self.lbl_preview_second.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.lbl_preview_second)
        # 派生统计网格
        grid = QHBoxLayout()
        grid.setSpacing(8)
        cells = [
            ("日薪", "¥0.00"),
            ("时薪", "¥0.00"),
            ("法定工作日", "0 天"),
            ("每日工时", "0 小时"),
        ]
        self._preview_value_labels = []
        for title, initial in cells:
            f, v = self._stat_cell(title, initial)
            grid.addWidget(f)
            self._preview_value_labels.append(v)
        # 便于语义化更新
        (self.lbl_preview_daily, self.lbl_preview_hourly,
         self.lbl_preview_legal, self.lbl_preview_hours) = self._preview_value_labels
        cl.addLayout(grid)
        card.setLayout(cl)
        lay.addWidget(card, 1)

        # ---- 公式说明 ----
        hint = QLabel(
            "计算方式：日薪 = 月薪 ÷ 当月法定工作日；秒薪 = 日薪 ÷ 每日总工时（秒）。\n"
            "法定工作日固定按「今天所在月」统计（含国庆等法定节假日与调休），"
            "翻看日历其他月份不影响秒薪；工时由「工作时间」页填写。"
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        lay.addStretch()
        return w

    def _page_date(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self._heading("工作日历"))
        self.calendar = WorkCalendarWidget()
        self.calendar.currentPageChanged.connect(self._on_calendar_page_changed)
        lay.addWidget(self.calendar, 1)
        self.lbl_legend = QLabel("色块：默认=工作日 · 灰色=周末 · 红色=节假日 · 橙色=调休上班")
        self.lbl_legend.setObjectName("hint")
        lay.addWidget(self.lbl_legend)
        row = QHBoxLayout()
        self.btn_update_holidays = QPushButton("联网更新节假日")
        self.btn_update_holidays.clicked.connect(self._on_update_holidays)
        row.addWidget(self.btn_update_holidays)
        self.lbl_workdays = QLabel("当页法定工作日：--")
        self.lbl_workdays.setObjectName("resultLabel")
        row.addWidget(self.lbl_workdays)
        row.addStretch()
        lay.addLayout(row)
        return w

    def _page_worktime(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self._heading("工作时间"))
        self.editor = TimeGroupEditor()
        self.editor.groupsChanged.connect(self._recompute)
        lay.addWidget(self.editor)
        return w

    def _page_settings(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self._heading("基本设置"))

        # 主题
        t_box = QGroupBox("界面主题")
        tf = QFormLayout()
        self.combo_theme = QComboBox()
        for k, t in THEMES.items():
            self.combo_theme.addItem(t["label"], k)
        self.combo_theme.currentIndexChanged.connect(self._on_theme_changed)
        tf.addRow("主窗口主题：", self.combo_theme)
        t_box.setLayout(tf)
        lay.addWidget(t_box)

        # 常规
        g = QGroupBox("常规")
        gf = QFormLayout()
        self.spin_default_workdays = _QDSB()
        self.spin_default_workdays.setRange(1, 31); self.spin_default_workdays.setDecimals(2)
        self.spin_default_workdays.setValue(float(self.config.get("settings", {}).get("default_legal_workdays", 21.75)))
        gf.addRow("法定工作日降级默认值：", self.spin_default_workdays)

        # 关闭行为：退出 / 最小化到托盘（单选）
        close_row = QWidget()
        cl = QVBoxLayout(close_row); cl.setContentsMargins(0,0,0,0); cl.setSpacing(2)
        self._close_group = QButtonGroup(self)
        self.rb_quit = QRadioButton("直接退出程序")
        self.rb_tray = QRadioButton("最小化到托盘")
        self._close_group.addButton(self.rb_quit); self._close_group.addButton(self.rb_tray)
        close_behavior = self.config.get("settings", {}).get("close_behavior")
        # 兼容旧版 minimize_to_tray：True->tray, False->quit；无则默认 tray
        if close_behavior is None:
            close_behavior = "tray" if self.config.get("settings", {}).get("minimize_to_tray", True) else "quit"
        (self.rb_tray if close_behavior == "tray" else self.rb_quit).setChecked(True)
        cl.addWidget(self.rb_quit); cl.addWidget(self.rb_tray)
        gf.addRow("关闭主窗口时：", close_row)

        self.chk_autostart = QCheckBox("开机自动启动")
        self.chk_autostart.setChecked(bool(self.config.get("settings", {}).get("auto_start", False)))
        gf.addRow(self.chk_autostart)
        g.setLayout(gf)
        lay.addWidget(g)

        bb = QPushButton("保存设置")
        bb.setObjectName("primary")
        bb.clicked.connect(self._save_settings)
        lay.addWidget(bb)
        lay.addStretch()
        return w

    def _page_float(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self._heading("浮窗"))
        box = QGroupBox("浮窗外观")
        f = QFormLayout()
        f.setSpacing(8)
        fl = self.config.get("float", {})

        # 浮窗主题
        self.combo_float_theme = QComboBox()
        for k, t in FLOAT_THEMES.items():
            self.combo_float_theme.addItem(t["label"], k)
        self.combo_float_theme.currentIndexChanged.connect(self._on_float_setting_changed)
        f.addRow("浮窗主题：", self.combo_float_theme)

        # 字号：直接选择数字 10-120
        self.spin_font = QSpinBox(); self.spin_font.setRange(10, 120)
        self.spin_font.setValue(int(fl.get("font_size", 30)))
        self.spin_font.setSuffix(" px")
        self.spin_font.valueChanged.connect(self._on_float_setting_changed)
        f.addRow("字号：", self.spin_font)

        # 不透明度：滑块 + 数值
        op_row = QWidget()
        ol = QHBoxLayout(op_row); ol.setContentsMargins(0,0,0,0)
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(20, 100)
        self.slider_opacity.setValue(int(float(fl.get("opacity", 0.92)) * 100))
        self.lbl_opacity_val = QLabel(f"{self.slider_opacity.value()}%")
        self.lbl_opacity_val.setObjectName("resultLabel")
        self.slider_opacity.valueChanged.connect(self._on_float_setting_changed)
        ol.addWidget(self.slider_opacity, 1)
        ol.addWidget(self.lbl_opacity_val)
        f.addRow("不透明度：", op_row)

        # 开关项
        self.chk_top = QCheckBox("窗口置顶")
        self.chk_top.setChecked(bool(fl.get("always_on_top", True)))
        self.chk_top.toggled.connect(self._on_float_setting_changed)
        f.addRow("置顶：", self.chk_top)

        self.chk_lock = QCheckBox("锁定窗口（不可拖动/缩放）")
        self.chk_lock.setChecked(bool(fl.get("locked", False)))
        self.chk_lock.toggled.connect(self._on_float_setting_changed)
        f.addRow("锁定：", self.chk_lock)

        self.chk_show_earn = QCheckBox("显示「今日已赚」")
        self.chk_show_earn.setChecked(bool(fl.get("show_today_earnings", True)))
        self.chk_show_earn.toggled.connect(self._on_float_setting_changed)
        f.addRow("今日已赚：", self.chk_show_earn)

        self.chk_count = QCheckBox("仅在工作时段内累计「今日已赚」")
        self.chk_count.setChecked(bool(fl.get("count_only_during_work", True)))
        self.chk_count.toggled.connect(self._on_float_setting_changed)
        f.addRow("累计方式：", self.chk_count)
        box.setLayout(f)
        lay.addWidget(box)

        tip = QLabel("提示：此处与浮窗右键菜单设置互通，改动即时生效；未运行浮窗时作为下次启动默认值。")
        tip.setObjectName("hint"); tip.setWordWrap(True)
        lay.addWidget(tip)
        lay.addStretch()
        return w

    def _page_about(self):
        from app.about_dialog import about_content_widget
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self._heading("关于"))
        lay.addWidget(about_content_widget())
        lay.addStretch()
        return w

    # ---- 底部常驻 ----
    def _build_bottom(self):
        w = QFrame()
        w.setFrameShape(QFrame.StyledPanel)
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 10, 16, 10)

        left = QVBoxLayout()
        self.lbl_daily = QLabel("日薪：--"); self.lbl_daily.setObjectName("resultLabel")
        self.lbl_hours = QLabel("每日工时：--"); self.lbl_hours.setObjectName("resultLabel")
        left.addWidget(self.lbl_daily); left.addWidget(self.lbl_hours)
        lay.addLayout(left)

        center = QVBoxLayout()
        self.lbl_second = QLabel("秒薪  ¥0.0000")
        self.lbl_second.setObjectName("resultBig")
        self.lbl_second.setAlignment(Qt.AlignCenter)
        center.addWidget(self.lbl_second)
        self.lbl_bottom_status = QLabel("就绪")
        self.lbl_bottom_status.setObjectName("hint")
        self.lbl_bottom_status.setAlignment(Qt.AlignCenter)
        center.addWidget(self.lbl_bottom_status)
        lay.addLayout(center, 1)

        self.btn_launch = QPushButton("▶  启动浮窗")
        self.btn_launch.setObjectName("primary")
        self.btn_launch.setMinimumHeight(46)
        self.btn_launch.setMinimumWidth(150)
        self.btn_launch.clicked.connect(self._on_launch)
        lay.addWidget(self.btn_launch)
        return w

    def _heading(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setObjectName("heading")
        return lbl

    def _stat_cell(self, title: str, initial: str):
        """返回 (卡片 QFrame, 数值 QLabel)：标题在上、数值在下的小统计块。"""
        f = QFrame()
        f.setObjectName("statCell")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("hint")
        t.setAlignment(Qt.AlignCenter)
        v = QLabel(initial)
        v.setObjectName("resultLabel")
        v.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)
        lay.addWidget(v)
        return f, v

    # ---------------- 导航 ----------------
    def _on_nav_changed(self, row):
        self.stack.setCurrentIndex(row)

    def _goto(self, name: str):
        if name in NAV:
            self.nav.setCurrentRow(NAV.index(name))

    # ---------------- 配置 <-> UI ----------------
    def _load_config_into_ui(self):
        self.spin_salary.setValue(float(self.config.get("monthly_salary", 0) or 0))
        self.editor.set_time_groups(self.config.get("time_groups"))
        now = dt.datetime.now()
        y = self.config.get("selected_year") or now.year
        m = self.config.get("selected_month") or now.month
        self.calendar.setCurrentPage(int(y), int(m))
        # 主题下拉
        self._set_combo(self.combo_theme, self.config.get("theme") or DEFAULT_THEME)
        fl = self.config.get("float", {})
        self._set_combo(self.combo_float_theme, fl.get("theme") or "f_dark_green")
        # 浮窗页控件从配置回填
        self._syncing = True
        try:
            self.spin_font.setValue(int(fl.get("font_size", 30)))
            self.slider_opacity.setValue(int(float(fl.get("opacity", 0.92)) * 100))
            self.chk_top.setChecked(bool(fl.get("always_on_top", True)))
            self.chk_lock.setChecked(bool(fl.get("locked", False)))
            self.chk_show_earn.setChecked(bool(fl.get("show_today_earnings", True)))
            self.chk_count.setChecked(bool(fl.get("count_only_during_work", True)))
        finally:
            self._syncing = False

    @staticmethod
    def _set_combo(combo, key):
        for i in range(combo.count()):
            if combo.itemData(i) == key:
                combo.setCurrentIndex(i); return

    def _on_theme_changed(self, _idx):
        key = self.combo_theme.currentData()
        self._change_theme(key)

    # ---------------- 浮窗设置：主窗口 ↔ 浮窗双向同步 ----------------
    def _on_float_setting_changed(self, *_):
        """浮窗页任一控件变化：更新数值标签、写盘，并实时作用到运行中浮窗。"""
        if self._syncing:
            return  # 反向回填触发的信号，忽略，避免递归
        self.lbl_opacity_val.setText(f"{self.slider_opacity.value()}%")
        # 收集当前设置并写盘（patch 方式，保留浮窗运行时写入的位置/尺寸等）
        self._patch_config(float=self._collect_float_settings())
        # 实时作用到运行中浮窗
        fw = self.float_window
        if fw is not None:
            self._apply_settings_to_float(fw)

    def _collect_float_settings(self) -> dict:
        return {
            "theme": self.combo_float_theme.currentData(),
            "font_size": self.spin_font.value(),
            "opacity": self.slider_opacity.value() / 100.0,
            "always_on_top": self.chk_top.isChecked(),
            "locked": self.chk_lock.isChecked(),
            "show_today_earnings": self.chk_show_earn.isChecked(),
            "count_only_during_work": self.chk_count.isChecked(),
        }

    def _apply_settings_to_float(self, fw):
        """把主窗口浮窗页当前控件值作用到运行中浮窗（各 setter 内部会写盘/重绘）。"""
        fw.set_theme(self.combo_float_theme.currentData())
        fw.set_font_size(self.spin_font.value())
        fw.set_opacity(self.slider_opacity.value() / 100.0)
        fw.set_always_on_top(self.chk_top.isChecked())
        fw.set_locked(self.chk_lock.isChecked())
        fw.set_show_today_earnings(self.chk_show_earn.isChecked())
        fw.set_count_only_during_work(self.chk_count.isChecked())

    def sync_float_controls_from(self, fw):
        """反向同步：浮窗右键菜单改动后，把浮窗当前状态回填到主窗口浮窗页控件。"""
        self._syncing = True
        try:
            self._set_combo(self.combo_float_theme, fw.float_theme)
            self.spin_font.setValue(fw.font_size)
            self.slider_opacity.setValue(int(fw.opacity * 100))
            self.lbl_opacity_val.setText(f"{int(fw.opacity * 100)}%")
            self.chk_top.setChecked(fw.always_on_top)
            self.chk_lock.setChecked(fw.locked)
            self.chk_show_earn.setChecked(fw.show_today_earnings)
            self.chk_count.setChecked(fw.count_only_during_work)
        finally:
            self._syncing = False

    def _save_settings(self):
        close_behavior = "tray" if self.rb_tray.isChecked() else "quit"
        self._patch_config(
            settings={
                "default_legal_workdays": self.spin_default_workdays.value(),
                "close_behavior": close_behavior,
                "minimize_to_tray": close_behavior == "tray",  # 兼容旧读取路径
                "auto_start": self.chk_autostart.isChecked(),
            },
            float=self._collect_float_settings(),
        )
        try:
            from app.settings_dialog import SettingsDialog
            SettingsDialog._apply_autostart(self.chk_autostart.isChecked())
        except Exception:
            pass
        self.statusBar().showMessage("设置已保存", 3000)

    def _persist(self):
        y, m = self.calendar.current_selection()
        self._patch_config(
            monthly_salary=self.spin_salary.value(),
            time_groups=self.editor.get_time_groups(),
            selected_year=y,
            selected_month=m,
            theme=self.theme_key,
        )

    # ---------------- 节假日 ----------------
    def _refresh_holidays_silent(self):
        """启动时静默就绪节假日数据。

        优先确保「今天所在年」可用——秒薪按今天所在月计算，必须用到今天
        所在年的节假日（国庆/调休等）。无缓存则后台静默拉取，完成后
        _on_holiday_fetched 会刷新日历并 recompute 修正秒薪。
        再尝试给日历当前显示页年份上色（有缓存即用）。"""
        today = dt.date.today()
        self._ensure_holidays(today.year, silent=True)
        shown_y = self.calendar.yearShown()
        if shown_y != today.year:
            # 显示页与今天不同年（如跨年重开）：也补一份，排入待拉队列
            self._ensure_holidays(shown_y, silent=True)
        if self.holidays_provider.has_cache(shown_y):
            self.calendar.set_holidays(self.holidays_provider.get_holidays(shown_y))
        else:
            self.calendar.set_holidays({})
        self._update_workdays_label()

    def _on_calendar_page_changed(self):
        """翻月：只为日历上色与「当页法定工作日」标签服务。

        秒薪固定按今天所在月算，这里【不】调用 _recompute——翻月绝不应
        改变秒薪（用户可随时翻看别月的工作日而不影响当前薪水显示）。"""
        y = self.calendar.yearShown()
        if self.holidays_provider.has_cache(y):
            self.calendar.set_holidays(self.holidays_provider.get_holidays(y))
        else:
            self.calendar.set_holidays({})
            self._ensure_holidays(y, silent=True)  # 无缓存则静默拉取，完成后补色
        self._update_workdays_label()

    def _ensure_holidays(self, year: int, *, silent: bool):
        """确保某年节假日可用：有缓存直接返回；无缓存则后台异步拉取。"""
        if self.holidays_provider.has_cache(year):
            return
        self._fetch_holidays_async(year, silent=silent)

    def _fetch_holidays_async(self, year: int, *, silent: bool):
        """后台拉取某年节假日。已有拉取在跑则排入待拉队列（只记最后一个）。"""
        if self._holiday_thread is not None and self._holiday_thread.isRunning():
            self._pending_fetch = (year, silent)
            return
        self._start_holiday_fetch(year, silent=silent)

    def _start_holiday_fetch(self, year: int, *, silent: bool):
        """真正创建 worker/thread 并启动一次拉取。"""
        self._holiday_fetch_silent = silent
        if not silent:
            self.btn_update_holidays.setEnabled(False)
            self.btn_update_holidays.setText("更新中…")
            self.statusBar().showMessage(f"正在联网获取 {year} 年节假日…")
            QApplication.processEvents()

        self._holiday_worker = HolidayFetchWorker(year, self.holidays_provider)
        self._holiday_thread = QThread()
        self._holiday_worker.moveToThread(self._holiday_thread)
        self._holiday_thread.started.connect(self._holiday_worker.run)
        self._holiday_worker.finished.connect(self._on_holiday_fetched)
        self._holiday_worker.finished.connect(self._holiday_thread.quit)
        # 线程真正结束后再处理待拉队列：避免 quit() 后 isRunning 仍为真的竞态
        self._holiday_thread.finished.connect(self._on_thread_finished)
        self._holiday_thread.start()

    def _on_thread_finished(self):
        """拉取线程结束：清理引用，并按需补拉队列里最后一个待拉年份。"""
        self._holiday_thread = None
        self._holiday_worker = None
        pending = self._pending_fetch
        self._pending_fetch = None
        if pending is not None:
            py, ps = pending
            if not self.holidays_provider.has_cache(py):
                self._start_holiday_fetch(py, silent=ps)

    def _on_update_holidays(self):
        """手动点击「联网更新节假日」：强制刷新当前显示页年份（即便有缓存也重拉）。"""
        y = self.calendar.yearShown()
        self._fetch_holidays_async(y, silent=False)

    def _on_holiday_fetched(self, mapping, ok, msg):
        silent = self._holiday_fetch_silent
        if not silent:
            self.btn_update_holidays.setEnabled(True)
            self.btn_update_holidays.setText("联网更新节假日")
        if ok:
            # 用「日历当前显示页年份」的缓存重新上色：刚拉取的年份若正是显示页则立即生效
            shown_y = self.calendar.yearShown()
            if self.holidays_provider.has_cache(shown_y):
                self.calendar.set_holidays(self.holidays_provider.get_holidays(shown_y))
            self._update_workdays_label()
            self._recompute()  # 今天所在年节假日已就绪，重算秒薪（按今天所在月）
            self.statusBar().showMessage(msg, 5000)
        else:
            self.statusBar().showMessage(msg, 6000)
        if not silent:
            QMessageBox.information(self, "节假日更新", msg)

    def _update_workdays_label(self):
        """日历下方的「当页法定工作日」标签——反映日历当前显示页（非今天所在月）。"""
        n = self.calendar.legal_workdays_of_current_page()
        y = self.calendar.yearShown()
        m = self.calendar.monthShown()
        self.lbl_workdays.setText(f"{y} 年 {m} 月法定工作日：{n} 天")

    # ---------------- 计算 ----------------
    def _legal_workdays_for_today(self) -> int:
        """秒薪计算用：今天所在月的法定工作日。

        固定取「今天」的年/月，与日历当前显示页【无关】——用户翻到别的月份
        不会改变秒薪。节假日用今天所在年的数据：有缓存即用；无缓存暂按
        「仅周末」判断（降级），自动拉取完成后 _on_holiday_fetched 会 recompute
        修正。这里绝不同步联网（会卡 UI）。"""
        today = dt.date.today()
        if self.holidays_provider.has_cache(today.year):
            holidays = self.holidays_provider.get_holidays(today.year)
        else:
            holidays = {}
        return count_legal_workdays(today.year, today.month, holidays)

    def _recompute(self):
        salary = self.spin_salary.value()
        groups = self.editor.get_time_groups()
        legal = self._legal_workdays_for_today()
        r = calculator.compute_all(salary, legal, groups)
        self.lbl_daily.setText(f"日薪：{calculator.format_money_short(r['daily_salary'])}")
        self.lbl_hours.setText(
            f"每日工时：{r['work_hours']} 小时  ·  法定工作日 {legal} 天"
        )
        self.lbl_second.setText(f"秒薪  {calculator.format_money(r['second_salary'])}")
        st = "当前：工作中" if r["in_work_period"] else "当前：休息中"
        self.lbl_bottom_status.setText(st)
        self.statusBar().showMessage(st, 3000)
        # 薪资页速览卡
        self.lbl_yearly.setText(calculator.format_money_short(salary * 12))
        self.lbl_preview_second.setText(f"{calculator.format_money(r['second_salary'])} / 秒")
        self.lbl_preview_daily.setText(calculator.format_money_short(r['daily_salary']))
        hourly = (r['daily_salary'] / r['work_hours']) if r['work_hours'] > 0 else 0.0
        self.lbl_preview_hourly.setText(calculator.format_money_short(hourly))
        self.lbl_preview_legal.setText(f"{legal} 天")
        self.lbl_preview_hours.setText(f"{r['work_hours']} 小时")

    # ---------------- 启动浮窗 ----------------
    def _build_payload(self):
        """校验输入并组装 payload，失败返回 None（已弹提示）。"""
        salary = self.spin_salary.value()
        groups = self.editor.get_time_groups()
        legal = self._legal_workdays_for_today()
        if salary <= 0:
            QMessageBox.warning(self, "无法启动", "请先填写月薪。"); return None
        if legal <= 0:
            QMessageBox.warning(self, "无法启动", "当月法定工作日为 0，请检查节假日数据。"); return None
        r = calculator.compute_all(salary, legal, groups)
        if r["work_seconds"] <= 0:
            QMessageBox.warning(self, "无法启动", "请至少填写一条有效的工作时间段。"); return None
        self._persist()
        return {
            "second_salary": r["second_salary"],
            "daily_salary": r["daily_salary"],
            "time_groups": groups,
        }

    def _on_launch(self):
        payload = self._build_payload()
        if payload is None:
            return
        self.launchRequested.emit(payload)

    # ---------------- 托盘 / 退出 ----------------
    @property
    def close_behavior(self) -> str:
        """'tray' 最小化到托盘 / 'quit' 直接退出。"""
        s = self.config.get("settings", {})
        cb = s.get("close_behavior")
        if cb is None:  # 兼容旧版 minimize_to_tray
            cb = "tray" if s.get("minimize_to_tray", True) else "quit"
        return cb

    def restore(self):
        self.showNormal(); self.raise_(); self.activateWindow()

    def _truly_quit(self):
        self._persist()
        # 清掉待拉队列，避免退出时 _on_thread_finished 又启动新拉取线程
        self._pending_fetch = None
        if self._holiday_thread is not None and self._holiday_thread.isRunning():
            self._holiday_thread.quit(); self._holiday_thread.wait(2000)
        QApplication.quit()

    def closeEvent(self, e):
        self._persist()
        if self.close_behavior == "tray" and self.tray is not None:
            e.ignore(); self.hide()
            if self.tray:
                self.tray.showMessage("秒薪浮窗", "已最小化到托盘，点击托盘图标可恢复。")
            return
        super().closeEvent(e)
