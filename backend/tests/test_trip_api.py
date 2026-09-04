import asyncio

from fastapi.testclient import TestClient
import pytest

import app.api.routes.trips as trips_module
from app.main import app
from app.models import Budget, DayPlan, TripPlan, TripPlanRequest
from app.services.trip_planner import TripPlanningError, plan_trip


def make_plan() -> TripPlan:
    return TripPlan(
        city="成都",
        start_date="2026-09-03",
        end_date="2026-09-03",
        days=[
            DayPlan(
                date="2026-09-03",
                day_index=1,
                title="成都历史文化一日游",
            )
        ],
        weather_info=[],
        overall_suggestions="乘坐公共交通出行。",
        budget=Budget(total=100),
    )


class FakeGraph:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.inputs = []

    async def ainvoke(self, value):
        self.inputs.append(value)
        if self.error is not None:
            raise self.error
        return self.result


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_local_vue_app() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/trips/plan",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )


def test_create_trip_plan_returns_graph_plan(monkeypatch) -> None:
    async def fake_plan_trip(request):
        assert request.city == "成都"
        assert request.preferences == ["历史文化", "美食"]
        return make_plan()

    monkeypatch.setattr(trips_module, "plan_trip", fake_plan_trip)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trips/plan",
            json={
                "city": "成都",
                "start_date": "2026-09-03",
                "end_date": "2026-09-03",
                "preferences": ["历史文化", "美食"],
                "budget_level": "medium",
                "transportation": "public_transport",
                "accommodation": "economy",
            },
        )

    assert response.status_code == 200
    assert response.json()["city"] == "成都"
    assert response.json()["budget"]["total"] == 100


def test_create_trip_plan_rejects_invalid_request() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trips/plan",
            json={
                "city": "成都",
                "start_date": "2026-09-05",
                "end_date": "2026-09-03",
            },
        )

    assert response.status_code == 422


def test_trip_planning_error_becomes_502(monkeypatch) -> None:
    async def fake_plan_trip(request):
        raise TripPlanningError(["天气查询失败。"])

    monkeypatch.setattr(trips_module, "plan_trip", fake_plan_trip)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trips/plan",
            json={
                "city": "成都",
                "start_date": "2026-09-03",
                "end_date": "2026-09-03",
            },
        )

    assert response.status_code == 502
    assert response.json() == {"detail": ["天气查询失败。"]}


def test_plan_trip_calls_graph_and_returns_validated_model() -> None:
    plan = make_plan()
    graph = FakeGraph(result={"trip_plan": plan.model_dump(mode="json")})

    result = asyncio.run(
        plan_trip(
            TripPlanRequest(
                city="成都",
                start_date="2026-09-03",
                end_date="2026-09-03",
            ),
            graph=graph,
        )
    )

    assert isinstance(result, TripPlan)
    assert graph.inputs[0]["request"].city == "成都"


def test_plan_trip_rejects_graph_errors() -> None:
    graph = FakeGraph(result={"errors": ["AMap failed"]})
    request = TripPlanRequest(
        city="成都",
        start_date="2026-09-03",
        end_date="2026-09-03",
    )

    with pytest.raises(TripPlanningError) as error:
        asyncio.run(plan_trip(request, graph=graph))

    assert error.value.messages == ["AMap failed"]
