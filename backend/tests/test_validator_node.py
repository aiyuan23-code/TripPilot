from app.graph.nodes.validator import validate_plan
from app.models import (
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    TripPlan,
    TripPlanRequest,
    WeatherInfo,
)


def make_request() -> TripPlanRequest:
    return TripPlanRequest(
        city="成都",
        start_date="2026-09-01",
        end_date="2026-09-02",
    )


def test_validator_accepts_a_complete_plan() -> None:
    request = make_request()
    hotel = Hotel(name="示例酒店", estimated_cost_per_night=300)
    budget = Budget(hotel_cost=300, transportation_cost=60, total=360)
    weather = [
        WeatherInfo(date="2026-09-01", day_weather="晴"),
        WeatherInfo(date="2026-09-02", day_weather="多云"),
    ]
    plan = TripPlan(
        city="成都",
        start_date=request.start_date,
        end_date=request.end_date,
        days=[
            DayPlan(
                date="2026-09-01",
                day_index=1,
                attractions=[Attraction(poi_id="A1", name="武侯祠")],
                hotel=hotel,
            ),
            DayPlan(
                date="2026-09-02",
                day_index=2,
                attractions=[Attraction(poi_id="A2", name="杜甫草堂")],
            ),
        ],
        weather_info=weather,
        overall_suggestions="测试",
        budget=budget,
    )

    result = validate_plan(
        {
            "request": request,
            "trip_plan": plan,
            "hotels": [hotel],
            "weather_info": weather,
            "budget": budget,
        }
    )

    assert result == {"validation_errors": []}


def test_validator_reports_invalid_schedule() -> None:
    request = make_request()
    repeated = Attraction(poi_id="A1", name="武侯祠")
    hotel_candidate = Hotel(name="示例酒店")
    inconsistent_budget = Budget(attraction_cost=10, total=100)
    plan = TripPlan(
        city="成都",
        start_date=request.start_date,
        end_date=request.end_date,
        days=[
            DayPlan(
                date="2026-09-01",
                day_index=2,
                attractions=[repeated, repeated, repeated, repeated, repeated],
            )
        ],
        weather_info=[],
        overall_suggestions="测试",
        budget=inconsistent_budget,
    )

    result = validate_plan(
        {
            "request": request,
            "trip_plan": plan,
            "hotels": [hotel_candidate],
            "weather_info": [
                WeatherInfo(date="2026-09-01", day_weather="晴")
            ],
            "budget": inconsistent_budget,
        }
    )

    errors = result["validation_errors"]
    assert any("应包含 2 天" in item for item in errors)
    assert any("缺少日期：2026-09-02" in item for item in errors)
    assert any("day_index 应为 1" in item for item in errors)
    assert any("应安排 1 至 4 个景点" in item for item in errors)
    assert any("景点重复安排" in item for item in errors)
    assert any("缺少住宿酒店" in item for item in errors)
    assert any("天气信息未覆盖日期：2026-09-02" in item for item in errors)
    assert any("预算总额与各项费用之和不一致" in item for item in errors)


def test_validator_reports_missing_plan() -> None:
    result = validate_plan({"request": make_request()})

    assert result == {"validation_errors": ["未生成旅行计划。"]}
