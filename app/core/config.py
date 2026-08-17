"""配置读写管理。

配置文件存放在 %APPDATA%/SalaryClock/config.json，打包后也能正常工作。
默认配置与 resources/default_config.json 保持一致，便于查阅。
"""
import json
import os
from copy import deepcopy

from app import APP_NAME, APP_VERSION, AUTHOR

__all__ = [
    "APP_NAME", "APP_VERSION", "AUTHOR",
    "DEFAULT_CONFIG", "CONFIG_PATH", "CACHE_PATH",
    "load_config", "save_config", "reset_config",
]


def _config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


CONFIG_PATH = os.path.join(_config_dir(), "config.json")
CACHE_PATH = os.path.join(_config_dir(), "holidays_cache.json")


DEFAULT_CONFIG = {
    "version": APP_VERSION,
    "theme": "midnight",
    "monthly_salary": 0.0,
    # 自定义时间段分组：名称 + 多条 [start, end] 时段
    "time_groups": [
        {"name": "上午", "periods": [{"start": "09:00", "end": "12:00"}]},
        {"name": "下午", "periods": [{"start": "13:30", "end": "18:00"}]},
    ],
    # None 表示运行时取当前年/月
    "selected_year": None,
    "selected_month": None,
    "float": {
        "opacity": 0.92,
        "font_size": 30,
        "font_family": "Microsoft YaHei",
        "always_on_top": True,
        "locked": False,
        "pos_x": None,
        "pos_y": None,
        "width": 260,
        "height": 132,
        "theme": "f_dark_green",
        "count_only_during_work": True,
        "show_today_earnings": True,
    },
    "settings": {
        # 联网失败且无缓存时的降级默认值
        "default_legal_workdays": 21.75,
        "auto_start": False,
        "minimize_to_tray": True,
        # 关闭主窗口时的行为：tray=最小化到托盘 / quit=直接退出
        "close_behavior": "tray",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并 override 到 base，返回新 dict（override 覆盖 base）。"""
    result = deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = deepcopy(v)
    return result


def _migrate_legacy(cfg: dict) -> dict:
    """把旧版遗留的无效主题键归一为新主题键。"""
    # 旧版 float.theme 可能是 "dark"/"light" 等已废弃的值
    from app.ui.styles import FLOAT_THEMES, DEFAULT_FLOAT_THEME, THEMES, DEFAULT_THEME
    f = cfg.get("float", {})
    if f.get("theme") not in FLOAT_THEMES:
        f["theme"] = DEFAULT_FLOAT_THEME
    if cfg.get("theme") not in THEMES:
        cfg["theme"] = DEFAULT_THEME
    return cfg


def load_config() -> dict:
    """读取配置，与默认值深合并，并迁移旧版遗留字段。"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = _deep_merge(DEFAULT_CONFIG, data)
            cfg = _migrate_legacy(cfg)
            return cfg
        except (json.JSONDecodeError, OSError):
            pass
    cfg = deepcopy(DEFAULT_CONFIG)
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    os.makedirs(_config_dir(), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def reset_config() -> dict:
    """重置为默认配置并返回。"""
    cfg = deepcopy(DEFAULT_CONFIG)
    save_config(cfg)
    return cfg
