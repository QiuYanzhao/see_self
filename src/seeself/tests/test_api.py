"""API 端到端测试：四层 CRUD、挂靠、完成状态、级联删除。"""
from datetime import date


def test_健康检查(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_四层创建与挂靠(client):
    plan = client.post(
        "/api/plans",
        json={"name": "五年计划", "start_year": 2026, "end_year": 2031},
    ).json()
    okr = client.post(
        "/api/okrs",
        json={"plan_id": plan["id"], "quarter": "2026Q3", "objective": "转型"},
    ).json()
    project = client.post(
        "/api/projects", json={"okr_id": okr["id"], "name": "学习项目"}
    ).json()
    todo = client.post(
        "/api/todos",
        json={"project_id": project["id"], "title": "学完文档"},
    ).json()
    assert todo["completed_at"] is None
    assert todo["project_id"] == project["id"]

    # 看板能看到项目
    dash = client.get("/api/dashboard").json()
    assert len(dash["projects"]) == 1


def test_完成待办记录完成时间(client):
    project = client.post("/api/projects", json={"name": "p"}).json()
    todo = client.post(
        "/api/todos",
        json={"project_id": project["id"], "title": "t"},
    ).json()
    resp = client.put(f"/api/todos/{todo['id']}/toggle", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None
    # 取消完成
    resp = client.put(f"/api/todos/{todo['id']}/toggle", json={"completed": False})
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is None


def test_结束年份必须大于开始年份(client):
    resp = client.post(
        "/api/plans", json={"name": "x", "start_year": 2030, "end_year": 2025}
    )
    assert resp.status_code == 422


def test_不存在对象返回404(client):
    assert client.get("/api/plans/999").status_code == 404
    assert client.get("/api/todos/999").status_code == 404


def test_级联删除(client):
    plan = client.post(
        "/api/plans", json={"name": "p", "start_year": 2026, "end_year": 2031}
    ).json()
    okr = client.post(
        "/api/okrs", json={"plan_id": plan["id"], "quarter": "2026Q4", "objective": "o"}
    ).json()
    project = client.post(
        "/api/projects", json={"okr_id": okr["id"], "name": "prj"}
    ).json()
    client.post(
        "/api/todos",
        json={"project_id": project["id"], "title": "t"},
    )
    # 删计划，其下全部级联
    assert client.delete(f"/api/plans/{plan['id']}").status_code == 200
    assert client.get("/api/okrs").json() == []
    assert client.get("/api/projects").json() == []


def test_设置读写(client):
    resp = client.put("/api/settings", json={"timezone": "Asia/Shanghai"})
    assert resp.status_code == 200
    assert resp.json()["timezone"] == "Asia/Shanghai"


def test_五年计划纲要结构与首年OKR(client):
    """纲要全结构（总纲/指标/领域/专项/风险/评估/待补充/首年 OKR）读写。"""
    payload = {
        "name": "规划纲要",
        "start_year": 2026,
        "end_year": 2031,
        "period_start": "2026-10-01",
        "period_end": "2031-09-30",
        "vision_positioning": "大厂 Agent 应用开发负责人",
        "vision_core_goals": ["收入稳定", "摆脱股市亏损"],
        "vision_bottom_lines": ["不背高息负债"],
        "evaluation": {"annual": "每年10月复盘", "midterm": "第3年年初", "final": "期末复盘"},
        "year1_goals": ["Agent 转型", "存款 7.4 万"],
        "year1_period": "2026-10-01至2027-09-30",
        "placeholders": [{"item": "体检结果", "note": "节后回填", "impact": "健康基线"}],
        "indicators": [
            {"kind": "binding", "name": "债务红线", "baseline": "剩13期", "target": "按期还清", "check_frequency": "月度"},
            {"kind": "expected", "name": "月总收入", "baseline": "1万", "target": "5万", "measure": "月度记账"},
        ],
        "domains": [
            {"domain": "人力资本", "status": "重点", "baseline": "SpringAiAlibaba 40%",
             "five_year_target": "大厂负责人", "year1_tasks": ["学完框架", "练手项目"]},
        ],
        "special_projects": [
            {"name": "Agent能力跃迁", "start": "2026-09", "end": "offer落地", "effort": "每周10h",
             "milestones": ["学完", "面经"], "acceptance_criteria": "拿到offer"},
        ],
        "risks": [
            {"risk_type": "职业", "trigger": "未被裁", "plan": "有offer就走", "reserve": "存款2万"},
        ],
        "okrs": [
            {"quarter": "Q1 2026.10-12", "objective": "Agent学习收尾",
             "kr_results": ["学完SpringAiAlibaba", "体检上线"]},
        ],
    }
    resp = client.post("/api/plans", json=payload)
    assert resp.status_code == 201, resp.text
    plan = resp.json()
    assert plan["period_start"] == "2026-10-01"
    assert plan["vision_positioning"] == "大厂 Agent 应用开发负责人"
    assert plan["vision_core_goals"] == ["收入稳定", "摆脱股市亏损"]
    assert plan["evaluation"]["annual"] == "每年10月复盘"
    assert len(plan["indicators"]) == 2
    assert plan["indicators"][0]["kind"] == "binding"
    assert plan["indicators"][0]["check_frequency"] == "月度"
    assert plan["indicators"][1]["measure"] == "月度记账"
    assert len(plan["domains"]) == 1
    assert plan["domains"][0]["year1_tasks"] == ["学完框架", "练手项目"]
    assert len(plan["special_projects"]) == 1
    assert plan["special_projects"][0]["milestones"] == ["学完", "面经"]
    assert plan["risks"][0]["risk_type"] == "职业"
    assert plan["placeholders"][0]["item"] == "体检结果"
    # 首年 OKR 落入 okr 表并随计划返回
    assert len(plan["okrs"]) == 1
    assert plan["okrs"][0]["quarter"] == "Q1 2026.10-12"
    assert plan["okrs"][0]["kr_results"] == ["学完SpringAiAlibaba", "体检上线"]
    # 单独读回一致
    again = client.get(f"/api/plans/{plan['id']}").json()
    assert again["vision_bottom_lines"] == ["不背高息负债"]
    assert len(again["indicators"]) == 2
