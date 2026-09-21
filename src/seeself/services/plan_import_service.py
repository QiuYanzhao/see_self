"""从 personal-five-year-plan 技能导出的 JSON 纲要转换并导入五年计划。

供 API 端点（POST /api/plans/import）与 MCP 工具（seeself_import_plan）复用。
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import FiveYearPlan
from ..schemas import OkrInput, PlanCreate
from . import plan_service


def _normalize_quarter(q: str) -> str:
    """把 json 中的季度标识统一为日历年季度格式。

    "Q1 2026.10-12"（五年计划内编号）→ "2026 Q4"
    已是 "2026 Q4" 格式则原样返回。
    """
    m = re.match(r"Q\d+\s+(\d{4})\.(\d{2})-\d{2}", q.strip())
    if m:
        year = int(m.group(1))
        start_month = int(m.group(2))
        q_num = (start_month - 1) // 3 + 1
        return f"{year} Q{q_num}"
    return q


def outline_json_to_plan_create(data: dict[str, Any], source: str | None = None) -> PlanCreate:
    """把纲要 JSON 转换为 PlanCreate（含首年 OKR）。

    source: 导入来源描述（文件路径或"页面导入"），写入 description。
    """
    period = data.get("period", {}) or {}
    start = date.fromisoformat(period["start"]) if period.get("start") else None
    end = date.fromisoformat(period["end"]) if period.get("end") else None
    if start is None or end is None:
        raise ValueError("纲要 JSON 缺少 period.start / period.end")

    vision = data.get("vision", {}) or {}
    indicators_raw = data.get("indicators", {}) or {}
    year1 = data.get("year1", {}) or {}
    name = f"{data.get('plan_name', '个人五年规划纲要')}（{start.year}-{end.year}）"

    indicators: list[dict[str, Any]] = []
    for item in indicators_raw.get("binding", []) or []:
        indicators.append({
            "kind": "binding", "name": item["name"],
            "baseline": item.get("baseline"), "target": item.get("target"),
            "check_frequency": item.get("check_frequency"), "measure": None,
        })
    for item in indicators_raw.get("expected", []) or []:
        indicators.append({
            "kind": "expected", "name": item["name"],
            "baseline": item.get("baseline"), "target": item.get("target"),
            "check_frequency": None, "measure": item.get("measure"),
        })

    domains = [
        {
            "domain": d["domain"], "status": d.get("status", "重点"),
            "baseline": d.get("baseline"), "five_year_target": d.get("five_year_target"),
            "year1_tasks": d.get("year1_tasks") or [],
        }
        for d in (data.get("domains") or [])
    ]

    special_projects = [
        {
            "name": sp["name"], "start": sp.get("start"), "end": sp.get("end"),
            "effort": sp.get("effort"), "milestones": sp.get("milestones") or [],
            "acceptance_criteria": sp.get("acceptance_criteria"),
        }
        for sp in (data.get("special_projects") or [])
    ]

    risks = [
        {
            "risk_type": r.get("type", r.get("risk_type", "")),
            "trigger": r.get("trigger"), "plan": r.get("plan"), "reserve": r.get("reserve"),
        }
        for r in (data.get("risks") or [])
    ]

    okrs: list[OkrInput] = []
    for q in (year1.get("okrs") or []):
        quarter = _normalize_quarter(q["quarter"])
        # 新结构：一个季度含多个 objective，每个 objective 有若干 key_results
        objectives = q.get("objectives")
        if objectives:
            for obj in objectives:
                okrs.append(OkrInput(
                    quarter=quarter, objective=obj["objective"],
                    kr_note=obj.get("kr_note"), kr_results=obj.get("key_results") or [],
                ))
        else:
            # 兼容旧结构：一个季度一个 objective
            okrs.append(OkrInput(
                quarter=quarter, objective=q["objective"],
                kr_note=q.get("kr_note"), kr_results=q.get("key_results") or [],
            ))

    description = f"《{name}》自动导入" + (f"，来源: {source}" if source else "")

    return PlanCreate(
        name=name,
        start_year=start.year,
        end_year=end.year,
        description=description,
        period_start=start,
        period_end=end,
        vision_positioning=vision.get("positioning"),
        vision_core_goals=vision.get("core_goals") or [],
        vision_bottom_lines=vision.get("bottom_lines") or [],
        evaluation=data.get("evaluation"),
        year1_goals=year1.get("goals") or [],
        year1_period=year1.get("period"),
        placeholders=data.get("placeholders") or [],
        indicators=indicators,
        domains=domains,
        special_projects=special_projects,
        risks=risks,
        okrs=okrs,
    )


def import_outline(db: Session, data: dict[str, Any], source: str | None = None):
    """导入纲要：系统只保留一份五年计划，已存在则整体覆盖（级联删除旧计划及其 OKR/项目/待办）。

    返回新创建的 PlanRead。
    """
    payload = outline_json_to_plan_create(data, source=source)
    # 删除全部现有计划（个人工具只保留一份）
    # 显式级联删除旧计划及其 OKR/项目/待办(不依赖数据库外键级联)
    existing = db.execute(select(FiveYearPlan)).scalars().all()
    for p in existing:
        plan_service._delete_plan_records(db, p.id)
        db.delete(p)
    db.flush()
    return plan_service.create_plan(db, payload)
