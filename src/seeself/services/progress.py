"""进度计算：时间流逝进度。

所有计算集中在此，保证 Web 页面与 MCP 工具口径一致、可单测。
"""
from __future__ import annotations

import calendar
from datetime import datetime

from ..schemas import TimeProgress


def time_progress(now: datetime | None = None) -> TimeProgress:
    now = now or datetime.now()
    today = now.date()

    year_days = 366 if calendar.isleap(today.year) else 365
    year_progress = round(today.timetuple().tm_yday / year_days * 100, 2)

    month_days = calendar.monthrange(today.year, today.month)[1]
    month_progress = round(today.day / month_days * 100, 2)

    week_progress = round(today.isoweekday() / 7 * 100, 2)

    return TimeProgress(
        now=now,
        year_progress=year_progress,
        month_progress=month_progress,
        week_progress=week_progress,
        year_label=f"{today.year} 年",
        month_label=f"{today.month} 月",
        week_label=f"第 {today.isocalendar().week} 周",
    )
