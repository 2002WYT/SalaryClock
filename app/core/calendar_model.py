"""月份工作日模型。

根据公历 + 节假日数据判定每天的四种状态，并统计某月法定工作日数量。

状态:
  WORKDAY          普通工作日（周一~五 且 非节假日）
  WEEKEND          普通周末（非调休）
  HOLIDAY          法定节假日（放假，不计入工作日）
  ADJUSTED_WORKDAY 调休上班（周末补班，计入工作日）
"""
import calendar
import datetime as dt

__all__ = [
    "WORKDAY", "WEEKEND", "HOLIDAY", "ADJUSTED_WORKDAY",
    "STATUS_COLORS",
    "TODAY_BG", "TODAY_FG", "TODAY_POINT_SIZE",
    "status_of", "is_workday", "count_legal_workdays",
    "month_dates_with_status",
]

WORKDAY = "workday"
WEEKEND = "weekend"
HOLIDAY = "holiday"
ADJUSTED_WORKDAY = "adjusted"

# 控件上色用：状态 -> (背景色, 前景色)
STATUS_COLORS = {
    # 普通工作日：中性深灰
    WORKDAY:          ("#343A46", "#E8ECF1"),

    # 普通周末：柔和绿色
    WEEKEND:          ("#244B36", "#A7E8BD"),

    # 法定节假日：更明显的绿色
    HOLIDAY:          ("#176B45", "#D8FFE7"),

    # 调休上班：醒目的红色
    ADJUSTED_WORKDAY: ("#6B2C2C", "#FFB3B3"),
}

# 「今天」单元格的醒目样式：用独立底色覆盖状态底色（区别于灰/暗灰/红/橙），
# 白字 + 加粗 + 略放大字号，让用户翻到任意月份都能一眼看到今天在哪一天。
TODAY_BG = "#2F80ED"
TODAY_FG = "#FFFFFF"
TODAY_POINT_SIZE = 11  # 默认约 9.75pt(13px)，今日放大到 11pt 更突出且不裁切


def status_of(date: dt.date, holidays: dict) -> str:
    """判定某天状态。holidays: {'YYYY-MM-DD': {'name':str, 'isOffDay':bool}}。"""
    key = date.isoformat()
    if key in holidays:
        return HOLIDAY if holidays[key].get("isOffDay", True) else ADJUSTED_WORKDAY
    if date.weekday() >= 5:  # 周六=5, 周日=6
        return WEEKEND
    return WORKDAY


def is_workday(date: dt.date, holidays: dict) -> bool:
    """是否计入法定工作日。"""
    return status_of(date, holidays) in (WORKDAY, ADJUSTED_WORKDAY)


def count_legal_workdays(year: int, month: int, holidays: dict) -> int:
    """统计某月法定工作日天数。"""
    last_day = calendar.monthrange(year, month)[1]
    return sum(1 for day in range(1, last_day + 1)
               if is_workday(dt.date(year, month, day), holidays))


def month_dates_with_status(year: int, month: int, holidays: dict):
    """返回 [(date, status, holiday_name), ...] 供日历控件逐日上色。"""
    last_day = calendar.monthrange(year, month)[1]
    result = []
    for day in range(1, last_day + 1):
        d = dt.date(year, month, day)
        s = status_of(d, holidays)
        name = holidays.get(d.isoformat(), {}).get("name", "")
        result.append((d, s, name))
    return result
