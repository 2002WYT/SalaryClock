"""薪水计算引擎。

输入:
  monthly_salary   月薪（元）
  legal_workdays   当月法定工作日（由日历模型算出）
  time_groups      自定义时间段分组 [{name, periods:[{start,end}]}]，HH:MM 字符串

输出:
  daily_salary     日薪 = 月薪 / 法定工作日
  work_seconds     每日总工时（秒）
  second_salary    秒薪 = 日薪 / 每日总工时（秒）

包含除零保护与跨午夜时段处理。
"""
import datetime as dt

__all__ = [
    "parse_time", "period_seconds", "total_work_seconds",
    "compute_daily_salary", "compute_second_salary",
    "is_in_work_period", "compute_all",
]


def parse_time(s: str):
    """'HH:MM' -> 自午夜起的分钟数。非法返回 None。"""
    if not s or not isinstance(s, str):
        return None
    try:
        parts = s.strip().split(":")
        if len(parts) != 2:
            return None
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return None
        return h * 60 + m
    except (ValueError, AttributeError):
        return None


def period_seconds(start: str, end: str) -> int:
    """单个时段的秒数，支持跨午夜（如 22:00-06:00）。非法返回 0。"""
    s = parse_time(start)
    e = parse_time(end)
    if s is None or e is None:
        return 0
    diff = e - s
    if diff <= 0:
        diff += 24 * 60  # 跨午夜
    if diff > 24 * 60:
        diff = 24 * 60
    return diff * 60


def total_work_seconds(time_groups) -> int:
    """汇总所有分组的所有时段秒数。"""
    total = 0
    for g in time_groups:
        for p in g.get("periods", []):
            total += period_seconds(p.get("start"), p.get("end"))
    return total


def compute_daily_salary(monthly_salary: float, legal_workdays: int) -> float:
    """日薪。法定工作日为 0 时返回 0（除零保护）。"""
    if not legal_workdays or legal_workdays <= 0 or monthly_salary <= 0:
        return 0.0
    return float(monthly_salary) / float(legal_workdays)


def compute_second_salary(daily_salary: float, work_seconds: int) -> float:
    """秒薪。工时为 0 时返回 0（除零保护）。"""
    if not work_seconds or work_seconds <= 0 or daily_salary <= 0:
        return 0.0
    return daily_salary / float(work_seconds)


def _in_period(t_minutes: int, start: int, end: int) -> bool:
    """判断 t_minutes 是否落在 [start, end) 时段内，支持跨午夜。"""
    if end > start:
        return start <= t_minutes < end
    elif end < start:  # 跨午夜
        return t_minutes >= start or t_minutes < end
    else:  # start == end，视为全天
        return True


def is_in_work_period(now: dt.time, time_groups) -> bool:
    """当前时刻是否落在任一工作时段内。"""
    t = now.hour * 60 + now.minute
    # 含秒时更精确：把当前秒折算进分钟边界比较已足够
    for g in time_groups:
        for p in g.get("periods", []):
            s = parse_time(p.get("start"))
            e = parse_time(p.get("end"))
            if s is None or e is None:
                continue
            if _in_period(t, s, e):
                return True
    return False


def compute_all(monthly_salary: float, legal_workdays: int, time_groups):
    """一次性算出全部结果，供 UI 预览与浮窗使用。

    返回 dict:
      daily_salary, work_seconds, work_hours, second_salary,
      in_work_period(基于当前时刻), legal_workdays
    """
    work_sec = total_work_seconds(time_groups)
    daily = compute_daily_salary(monthly_salary, legal_workdays)
    second = compute_second_salary(daily, work_sec)
    return {
        "monthly_salary": float(monthly_salary),
        "legal_workdays": int(legal_workdays),
        "daily_salary": daily,
        "work_seconds": work_sec,
        "work_hours": round(work_sec / 3600.0, 2),
        "second_salary": second,
        "in_work_period": is_in_work_period(dt.datetime.now().time(), time_groups),
    }


def format_money(v: float) -> str:
    """¥0.0000 这种，秒薪一般很小，保留 4 位小数。"""
    return f"¥{v:,.4f}"


def format_money_short(v: float) -> str:
    """日薪/累计用，2 位小数。"""
    return f"¥{v:,.2f}"
