import asyncio

from app.graph.nodes.planner import build_planner_messages, run_planner
from app.models import (
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Meal,
    TripPlan,
    TripPlanRequest,
    WeatherInfo,
)


def make_state():
    request = TripPlanRequest(
        city="成都",
        start_date="2026-09-01",
        end_date="2026-09-02",
        preferences=["历史文化"],
    )
    weather = [WeatherInfo(date="2026-09-01", day_weather="晴")]
    return {
        "request": request,
        "attractions": [Attraction(poi_id="A1", name="武侯祠")],
        "weather_info": weather,
        "hotels": [Hotel(poi_id="H1", name="示例酒店")],
        "restaurants": [
            Meal(
                poi_id="R1",
                type_code="050100",
                meal_type="restaurant",
                name="真实餐厅",
                address="真实地址",
                rating=4.8,
                estimated_cost=88,
            )
        ],
        "errors": [],
    }


class FakeStructuredModel:
    def __init__(self, output) -> None:
        self.output = output
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return self.output


class FakeLLM:
    def __init__(self, output) -> None:
        self.structured = FakeStructuredModel(output)
        self.schema = None
        self.method = None

    def with_structured_output(self, schema, *, method):
        self.schema = schema
        self.method = method
        return self.structured


def test_planner_uses_structured_output_and_preserves_deterministic_fields() -> None:
    state = make_state()
    llm_output = TripPlan(
        city="错误城市",
        start_date="2026-01-01",
        end_date="2026-01-01",
        days=[
            DayPlan(
                date="2026-09-01",
                day_index=1,
                attractions=state["attractions"],
                hotel=state["hotels"][0],
                meals=[
                    Meal(
                        poi_id="R1",
                        meal_type="lunch",
                        name="真实餐厅",
                        address="错误地址",
                        estimated_cost=1,
                    )
                ],
            )
        ],
        weather_info=[],
        overall_suggestions="提前预约。",
        budget=Budget(total=999),
    )
    llm = FakeLLM(llm_output)

    result = asyncio.run(
        run_planner(
            state,  # type: ignore[arg-type]
            llm,
            structured_output_method="function_calling",
        )
    )

    plan = result["trip_plan"]
    assert llm.schema is TripPlan
    assert llm.method == "function_calling"
    assert plan.city == "成都"
    assert plan.start_date.isoformat() == "2026-09-01"
    assert plan.end_date.isoformat() == "2026-09-02"
    assert plan.weather_info == state["weather_info"]
    assert plan.budget is None
    assert plan.days[0].meals[0].meal_type == "lunch"
    assert plan.days[0].meals[0].address == "真实地址"
    assert plan.days[0].meals[0].rating == 4.8
    assert plan.days[0].meals[0].estimated_cost == 88


def test_planner_messages_include_real_candidates() -> None:
    messages = build_planner_messages(make_state())  # type: ignore[arg-type]

    assert "武侯祠" in messages[1].content
    assert "示例酒店" in messages[1].content
    assert "真实餐厅" in messages[1].content
    assert "calculated_trip_days" in messages[1].content
    assert "output_schema" in messages[1].content


def test_planner_skips_llm_when_no_attractions_are_available() -> None:
    state = make_state()
    state["attractions"] = []
    llm = FakeLLM(output=None)

    result = asyncio.run(run_planner(state, llm))  # type: ignore[arg-type]

    assert "trip_plan" not in result
    assert result["errors"] == [
        "Planner skipped because no attraction candidates are available."
    ]
    assert llm.schema is None
