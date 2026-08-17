# 秒薪浮窗 (SalaryClock)

> 让每一秒的劳动都看得见。实时计算并桌面浮窗展示你的「每秒薪水」与「今日已赚」。

按日历与法定节假日精确算出日薪 / 秒薪，桌面浮窗每秒刷新，随时提醒：时间在变钱。

作者：**2002WYT**

---

## 功能一览

### 薪水计算
- **精确秒薪**：日薪 = 月薪 ÷ 当月法定工作日；秒薪 = 日薪 ÷ 每日总工时（秒），含除零保护
- **自定义时间段**：不限于上午 / 下午 / 晚上，可任意增删命名分组，每组多条 `[开始-结束]` 时段，支持跨午夜班次
- **今日已赚**：浮窗实时累计，可选择「仅在工作时段内累计」或全天累计

### 日历
- **四状态上色**：按国务院节假日数据自动区分——普通工作日 / 周末 / 法定节假日（红）/ 调休上班（橙），并统计当月法定工作日数
- **今日高亮**：今天的单元格用独立醒目蓝色底 + 白字 + 加粗放大字号标注，翻到任意月份都能一眼看到「今天在哪一天」
- **联网节假日**：数据源 [holiday-cn](https://github.com/NateScarred/holiday-cn)（开源、含调休、年度更新），本地缓存，离线自动降级为周末判断；后台异步拉取，不卡界面

### 桌面浮窗
- 无边框半透明、可置顶；每秒刷新秒薪与「今日已赚」
- 右键菜单：锁定 / 置顶 / 不透明度滑块 / 浮窗主题（14 种）/ 字号（10–120 px 直接选）/ 返回主菜单 / 关闭
- **可拖动、可缩放**，位置与大小自动记忆
- **锁定模式**：锁定后窗口轮廓随手柄隐藏而缩小（文字内容不变、不被拉伸），且**鼠标点击完全穿透**浮窗直达下方窗口/桌面——既占位又不挡操作
- **三行文字统一字号**，仅靠颜色区分（秒薪 / 今日已赚 / 状态）

### 主窗口与设置
- 左日历 + 右参数的清晰布局；14 种深色 / 浅色主题
- **浮窗设置实时双向同步**：主窗口与浮窗任一处调整，另一处立即跟随
- **关闭行为可选**：关闭主窗口时「直接退出」或「最小化到托盘」
- 法定工作日降级默认值、浮窗默认参数、**开机自启**
- 系统托盘常驻：双击恢复主窗口，右键退出
- 关于对话框：版本信息与作者署名 2002WYT

---

## 技术栈

- **PySide6 (Qt6)** — GUI 框架
- **requests** — 节假日数据联网
- **Win32 API (ctypes)** — 浮窗锁定后的鼠标点击穿透
- Windows 10 / 11，Python 3.10+（开发运行用）

---

## 开发运行

```bash
# 1. 克隆仓库
git clone https://github.com/2002WYT/SalaryClock.git
cd SalaryClock

# 2. （推荐）创建虚拟环境
python -m venv .venv
.venv\Scripts\activate        # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python main.py
```

> 首次运行会联网拉取本年节假日数据并缓存到 `%APPDATA%\SalaryClock\`，之后离线可用。

---

## 打包为 EXE

本项目用 **PyInstaller** 打包为单文件 EXE，打包后无需安装 Python 即可运行。

### 步骤

```bash
# 1. 安装打包工具
pip install pyinstaller

# 2. 执行打包（使用仓库内置的 build.spec 配置）
pyinstaller build.spec
```

打包完成后：

- 产物：**`dist\SalaryClock.exe`**（单文件，可直接双击运行）
- 中间产物：`build\` 目录、`SalaryClock.spec`（可忽略，配置以 `build.spec` 为准）

### 常见问题

| 现象 | 原因与处理 |
|------|-----------|
| 杀毒软件误报 | 单文件 EXE 启动时解压到临时目录，易被误报。可加入信任，或改用 `onedir` 模式打包（见下）。 |
| 首次启动较慢 | 单文件模式需先自解压到临时目录，属正常现象。 |
| 体积偏大 | PySide6 本身较大，单文件约 60–80 MB。如需更小可裁剪未用模块。 |
| 缺少 UPX 压缩 | `build.spec` 默认 `upx=True`；若系统未装 UPX，PyInstaller 会自动跳过压缩，不影响运行。需压缩可[安装 UPX](https://upx.github.io/) 后将其加入 `PATH`。 |

### 自定义图标

程序默认使用程序化生成的占位图标。如需自定义：

1. 准备一张 `.ico` 图标文件（建议包含 16/32/48/256 多尺寸）
2. 命名为 `resources/icon.ico`
3. 重新执行 `pyinstaller build.spec`

### 打包为目录（onedir）模式

若想避免杀软误报、加快启动，可改为目录模式。编辑 `build.spec` 末尾，把 `EXE(...)` 拆成 `EXE + COLLECT`，或直接用命令行：

```bash
pyinstaller --noconfirm --onedir --windowed --name SalaryClock ^
  --add-data "resources/default_config.json;resources" ^
  main.py
```

产物为 `dist\SalaryClock\` 目录（含 `SalaryClock.exe` 与依赖 DLL），整体分发即可。

---

## 配置与数据位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 配置文件 | `%APPDATA%\SalaryClock\config.json` | 月薪、时间段、浮窗设置、主题等 |
| 节假日缓存 | `%APPDATA%\SalaryClock\holidays_cache.json` | 联网拉取后本地缓存，离线降级用 |

> `%APPDATA%` 一般是 `C:\Users\<用户名>\AppData\Roaming`。删除这两个文件即恢复默认状态。

---

## 项目结构

```
SalaryClock/
├── main.py                      # 程序入口：主窗口 + 托盘 + 浮窗编排
├── build.spec                   # PyInstaller 打包配置
├── requirements.txt             # 依赖：PySide6, requests
├── README.md
├── .gitignore
├── app/
│   ├── __init__.py              # 应用常量（名称 / 版本 / 作者）
│   ├── main_window.py           # 主窗口（左日历 + 右参数 + 浮窗设置）
│   ├── float_window.py          # 桌面浮窗（含锁定穿透 / 轮廓收缩）
│   ├── settings_dialog.py       # 设置对话框
│   ├── about_dialog.py          # 关于对话框
│   ├── tray.py                  # 系统托盘
│   ├── core/
│   │   ├── config.py            # 配置读写（深合并 + 旧字段迁移）
│   │   ├── calendar_model.py    # 日历四状态 / 法定工作日计数 / 今日高亮常量
│   │   ├── holiday_provider.py  # 节假日联网 / 缓存 / 降级
│   │   ├── holiday_worker.py    # 节假日异步拉取（不卡界面）
│   │   └── calculator.py        # 薪水计算引擎
│   └── ui/
│       ├── styles.py            # 全局 QSS（14 主窗口主题 + 14 浮窗主题）
│       ├── calendar_widget.py   # 带状态色块 + 今日高亮的日历控件
│       └── time_group_editor.py # 自定义时间段分组编辑器
└── resources/
    └── default_config.json      # 默认配置
```

---

## 已知限制（v0.0.1）

- 跨午夜班次的「今日已赚」初始值为近似估算，运行中累计为精确值。
- 鼠标点击穿透基于 Windows 的 `WS_EX_TRANSPARENT`，仅 Windows 平台生效；其他平台锁定后浮窗仍接收鼠标但不影响显示。
- 应用图标为程序化生成的占位图标，可替换 `resources/icon.ico`。

---

## License

本项目基于 [MIT License](LICENSE) 开源，© 2002WYT。

> 若尚未添加 LICENSE 文件，可在 GitHub 仓库页面「Add file → Create new file」命名为 `LICENSE` 并选择 MIT 模板，或本地创建后一并提交。
