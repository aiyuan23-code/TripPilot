import asyncio

import app.graph.builder as builder_module
from app.models import (
    Attraction,
    DayPlan,
    Hotel,
    Meal,
    TripPlan,
    TripPlanRequest,
    WeatherInfo,
)


def make_request() -> TripPlanRequest:
    return TripPlanRequest(
        city="成都",
        start_date="2026-09-01",
        end_date="2026-09-02",
        preferences=["历史文化", "美食"],
        accommodation="economy",
    )


def test_graph_runs_research_nodes_in_parallel_and_merges_state(monkeypatch) -> None:
    started: set[str] = set()
    all_started = asyncio.Event()
    joined = False

    async def wait_for_siblings(name: str) -> None:
        started.add(name)
        if len(started) == 4:
            all_started.set()
        await asyncio.wait_for(all_started.wait(), timeout=1)

    async def attraction_node(state):
        await wait_for_siblings("attraction")
        return {"attractions": [Attraction(name="武侯祠")]}

    async def weather_node(state):
        await wait_for_siblings("weather")
        return {
            "weather_info": [
                WeatherInfo(date="2026-09-01", day_weather="晴"),
                WeatherInfo(date="2026-09-02", day_weather="多云"),
            ]
        }

    async def hotel_node(state):
        await wait_for_siblings("hotel")
        return {"hotels": [Hotel(name="示例酒店", hotel_type="economy")]}

    async def restaurant_node(state):
        await wait_for_siblings("restaurant")
        return {
            "restaurants": [
                Meal(meal_type="restaurant", name="示例餐厅", estimated_cost=80)
            ]
        }

    async def collect_node(state):
        nonlocal joined
        assert started == {"attraction", "weather", "hotel", "restaurant"}
        assert state["attractions"][0].name == "武侯祠"
        assert state["weather_info"][0].day_weather == "晴"
        assert state["hotels"][0].name == "示例酒店"
        assert state["restaurants"][0].estimated_cost == 80
        joined = True
        return {}

    async def planner_node(state):
        hotel = state["hotels"][0]
        return {
            "trip_plan": TripPlan(
                city="成都",
                start_date="2026-09-01",
                end_date="2026-09-02",
                days=[
                    DayPlan(
                        date="2026-09-01",
                        day_index=1,
                        attractions=[Attraction(name="武侯祠")],
                        hotel=hotel,
                    ),
                    DayPlan(
                        date="2026-09-02",
                        day_index=2,
                        attractions=[Attraction(name="杜甫草堂")],
                    ),
                ],
                weather_info=state["weather_info"],
                overall_suggestions="测试计划",
            )
        }

    monkeypatch.setattr(builder_module, "attraction_search", attraction_node)
    monkeypatch.setattr(builder_module, "weather_query", weather_node)
    monkeypatch.setattr(builder_module, "hotel_search", hotel_node)
    monkeypatch.setattr(builder_module, "restaurant_search", restaurant_node)
    monkeypatch.setattr(builder_module, "collect_results", collect_node)
    monkeypatch.setattr(builder_module, "planner", planner_node)

    graph = builder_module.build_trip_graph()
    result = asyncio.run(graph.ainvoke({"request": make_request()}))

    assert joined is True
    assert result["attractions"][0].name == "武侯祠"
    assert result["weather_info"][0].day_weather == "晴"
    assert result["hotels"][0].name == "示例酒店"
    assert result["restaurants"][0].name == "示例餐厅"
    assert result["trip_plan"].overall_suggestions == "测试计划"
    assert result["budget"].transportation_cost == 60
    assert result["trip_plan"].budget == result["budget"]
    assert result["validation_errors"] == []
    assert result["errors"] == []


def test_graph_error_reducer_combines_parallel_errors(monkeypatch) -> None:
    async def attraction_node(state):
        return {"attractions": [], "errors": ["attraction failed"]}

    async def weather_node(state):
        return {"weather_info": [], "errors": ["weather failed"]}

    async def hotel_node(state):
        return {"hotels": [], "errors": ["hotel failed"]}

    async def restaurant_node(state):
        return {"restaurants": [], "errors": ["restaurant failed"]}

    async def planner_node(state):
        return {}

    monkeypatch.setattr(builder_module, "attraction_search", attraction_node)
    monkeypatch.setattr(builder_module, "weather_query", weather_node)
    monkeypatch.setattr(builder_module, "hotel_search", hotel_node)
    monkeypatch.setattr(builder_module, "restaurant_search", restaurant_node)
    monkeypatch.setattr(builder_module, "planner", planner_node)

    graph = builder_module.build_trip_graph()
    result = asyncio.run(graph.ainvoke({"request": make_request()}))

    assert set(result["errors"]) == {
        "attraction failed",
        "weather failed",
        "hotel failed",
        "restaurant failed",
        "Budget skipped because no trip plan is available.",
    }
    assert result["attractions"] == []
    assert result["weather_info"] == []
    assert result["hotels"] == []
    assert result["restaurants"] == []
    assert result["validation_errors"] == ["未生成旅行计划。"]
