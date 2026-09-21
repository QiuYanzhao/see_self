"""时间进度与分段进度测试。"""
from datetime import date, datetime

from seeself.services import progress
from seeself.services.todo_service import project_progress, segmented_progress


def test_时间进度取值范围():
    tp = progress.time_progress(datetime(2026, 9, 11, 12, 0, 0))
    assert 0 <= tp.year_progress <= 100
    assert 0 <= tp.month_progress <= 100
    assert 0 < tp.week_progress <= 100
    # 9 月 11 日，9 月共 30 天
    assert tp.month_progress == round(11 / 30 * 100, 2)
    # 周五，isoweekday=5
    assert tp.week_progress == round(5 / 7 * 100, 2)


def test_分段进度按完成时间切分(db_session):
    from seeself.models import Project, Todo

    project = Project(name="测试项目")
    db_session.add(project)
    db_session.flush()
    today = date(2026, 9, 11)  # 周五

    # 造 10 个待办：2 个上月完成、1 个本周一前完成、1 个昨天完成、1 个今天完成、5 个未完成
    def add_todo(completed_at):
        db_session.add(
            Todo(
                project_id=project.id,
                title="t",
                completed_at=completed_at,
            )
        )

    add_todo(datetime(2026, 8, 20))
    add_todo(datetime(2026, 8, 25))
    add_todo(datetime(2026, 9, 7, 12))  # 本周一（9/7）当天
    add_todo(datetime(2026, 9, 10, 15))  # 昨天
    add_todo(datetime(2026, 9, 11, 9))   # 今天
    for _ in range(5):
        add_todo(None)
    db_session.flush()

    stats = project_progress(db_session, project.id)
    assert stats["total_leaves"] == 10 and stats["completed_leaves"] == 5 and stats["percent"] == 50.0

    result = segmented_progress(db_session, project.id, today)
    segments = result["segments"]
    # 总进度末端 = 50%
    assert segments[-1]["end"] == 50.0
    # 段之间首尾相接
    for prev, nxt in zip(segments, segments[1:]):
        assert prev["end"] == nxt["start"]
    # 口径：本月(9/1 至今) = 3 项(7/10/11 号完成) = 30%；本周(9/7 至今) = 3 项 = 30%
    assert result["month"] == 30.0
    assert result["week"] == 30.0
    # 昨日(9/10 0点 ~ 9/11 0点) = 1 项 = 10%；今日(9/11 0点 ~ 实时) = 1 项 = 10%
    assert result["yesterday"] == 10.0
    assert result["today"] == 10.0
    # 五段规则：月初前 / 月初→周初 / 周初→昨日 / 昨日 / 今日
    # 数据：8月2项、9/7一项、9/10一项、9/11一项 → 月初前20、周初→昨日10(9/7)、昨日10、今日10
    labels = [s["label"] for s in segments]
    assert labels == ["月初前", "周初→昨日", "昨日", "今日"]


def test_空项目分段为空(db_session):
    from seeself.models import Project

    project = Project(name="空项目")
    db_session.add(project)
    db_session.flush()
    result = segmented_progress(db_session, project.id)
    assert result["segments"] == []
    assert result["month"] == 0.0
    assert result["week"] == 0.0
    assert result["yesterday"] == 0.0
    assert result["today"] == 0.0
