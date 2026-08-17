"""节假日数据 Provider。

数据源: holiday-cn (NateScarlet/holiday-cn) —— 开源、免费、含调休标记，按年更新。
拉取策略:
  1. 先查本地缓存（holidays_cache.json），命中则直接返回。
  2. 未命中则联网拉取该年 JSON，解析后写入缓存。
  3. 联网失败返回空 dict，调用方降级为「仅周末判断」并提示用户。

数据格式 (holiday-cn):
  days: [ { "name": "元旦", "date": "2026-01-01", "isOffDay": true }, ... ]
  isOffDay=true  -> 法定节假日
  isOffDay=false -> 调休上班（周末补班）
"""
import json
import os

import requests

from app.core.config import CACHE_PATH

HOLIDAY_CN_URL = (
    "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json"
)
# 国内镜像兜底（raw.githubusercontent.com 偶尔不稳定）
HOLIDAY_CN_MIRROR_URL = (
    "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json"
)


class HolidayProvider:
    def __init__(self, cache_path: str = CACHE_PATH):
        self.cache_path = cache_path
        self._cache = self._load_cache()

    # ---- 缓存读写 ----
    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_cache(self) -> None:
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, ensure_ascii=False, indent=2)

    # ---- 对外接口 ----
    def get_holidays(self, year: int) -> dict:
        """获取某年节假日映射，优先缓存。返回 {'YYYY-MM-DD': {'name','isOffDay'}}。"""
        key = str(year)
        if key in self._cache:
            return self._cache[key]
        return self.fetch(year)

    def has_cache(self, year: int) -> bool:
        return str(year) in self._cache

    def fetch(self, year: int) -> dict:
        """联网拉取某年节假日，成功写入缓存并返回；失败返回 {}。"""
        for url in (HOLIDAY_CN_URL, HOLIDAY_CN_MIRROR_URL):
            mapping = self._fetch_from(year, url)
            if mapping:
                self._cache[str(year)] = mapping
                self._save_cache()
                return mapping
        return {}

    def fetch_with_status(self, year: int):
        """返回 (mapping, ok, message)，供 UI 提示。"""
        mapping = self.fetch(year)
        if mapping:
            return mapping, True, f"已更新 {year} 年节假日（共 {len(mapping)} 条）"
        return {}, False, f"联网更新失败：无法获取 {year} 年节假日数据，请检查网络后重试"

    # ---- 内部 ----
    def _fetch_from(self, year: int, url: str) -> dict:
        try:
            resp = requests.get(url.format(year=year), timeout=12)
            resp.raise_for_status()
            data = resp.json()
            mapping = {}
            for d in data.get("days", []):
                mapping[d["date"]] = {
                    "name": d.get("name", ""),
                    "isOffDay": d.get("isOffDay", True),
                }
            return mapping
        except (requests.RequestException, ValueError, KeyError, TypeError):
            return {}
