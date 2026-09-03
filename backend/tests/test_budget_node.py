from app.graph.nodes.budget import calculate_budget
from app.models import Attraction, DayPlan, Hotel, Meal, TripPlan, TripPlanRequest


def make_request(
    *,
    transportation: str = "public_transport",
    budget_level: str = "medium",
    accommodation: str = "economy",
) -> TripPlanRequest:
    return TripPlanRequest(
        city="成都",
        start_date="2026-09-01",
        end_date="2026-09-03",
        transportation=transportation,
        budget_level=budget_level,
        accommodation=accommodation,
    )


def test_budget_calculates_components_and_two_hotel_nights() -> None:
    request = make_request()
    first_hotel = Hotel(name="酒店一", estimated_cost_per_night=300)
    second_hotel = Hotel(name="酒店二", estimated_cost_per_night=400)
    final_day_hotel = Hotel(name="酒店三", estimated_cost_per_night=500)
    plan = TripPlan(
        city="成都",
        start_date=request.start_date,
        end_date=request.end_date,
        days=[
            DayPlan(
                date="2026-09-01",
                day_index=1,
                attractions=[Attraction(name="武侯祠", ticket_price=50)],
                meals=[Meal(meal_type="lunch", name="川菜", estimated_cost=60)],
                hotel=first_hotel,
            ),
            DayPlan(
                date="2026-09-02",
                day_index=2,
                attractions=[Attraction(name="杜甫草堂", ticket_price=20)],
                meals=[Meal(meal_type="dinner", name="火锅", estimated_cost=100)],
                hotel=second_hotel,
            ),
            DayPlan(
                date="2026-09-03",
                day_index=3,
                attractions=[Attraction(name="锦里", ticket_price=0)],
                hotel=final_day_hotel,
            ),
        ],
        weather_info=[],
        overall_suggestions="测试",
    )

    result = calculate_budget({"request": request, "trip_plan": plan})

    budget = result["budget"]
    assert budget.attraction_cost == 70
    assert budget.hotel_cost == 700
    assert budget.meal_cost == 160
    assert budget.transportation_cost == 90
    assert budget.total == 1020
    assert result["trip_plan"].budget == budget
    assert [day.estimated_daily_cost for day in result["trip_plan"].days] == [
        440,
        550,
        30,
    ]


def test_budget_uses_requested_transportation_rule() -> None:
    request = make_request(transportation="taxi")
    plan = TripPlan(
        city="成都",
        start_date=request.start_date,
        end_date=request.end_date,
        days=[],
        weather_info=[],
        overall_suggestions="测试",
    )

    result = calculate_budget({"request": request, "trip_plan": plan})

    assert result["budget"].transportation_cost == 300


def test_budget_estimates_missing_hotel_meal_and_scenic_prices() -> None:
    request = make_request()
    hotel = Hotel(name="示例酒店", hotel_type="economy")
    plan = TripPlan(
        city="成都",
        start_date=request.start_date,
        end_date=request.end_date,
        days=[
            DayPlan(
                date="2026-09-01",
                day_index=1,
                attractions=[
                    Attraction(name="文化景区", type_code="110205"),
                    Attraction(name="博物馆", type_code="140100"),
                    Attraction(name="美食街", type_code="050000"),
                ],
                meals=[
                    Meal(meal_type="breakfast", name="早餐"),
                    Meal(meal_type="lunch", name="午餐"),
                    Meal(meal_type="dinner", name="晚餐"),
                ],
                hotel=hotel,
            ),
            DayPlan(
                date="2026-09-02",
                day_index=2,
                attractions=[],
                meals=[Meal(meal_type="dinner", name="晚餐")],
                hotel=hotel,
            ),
            DayPlan(
                date="2026-09-03",
                day_index=3,
                attractions=[],
                meals=[Meal(meal_type="lunch", name="午餐")],
            ),
        ],
        weather_info=[],
        overall_suggestions="测试",
        budget=None,
    )

    result = calculate_budget({"request": request, "trip_plan": plan})

    budget = result["budget"]
    assert budget.attraction_cost == 120
    assert budget.hotel_cost == 500
    assert budget.meal_cost == 265
    assert budget.transportation_cost == 90
    assert budget.total == 975

    updated_days = result["trip_plan"].days
    assert updated_days[0].attractions[0].ticket_price == 60
    assert updated_days[0].attractions[1].ticket_price == 60
    assert updated_days[0].attractions[2].ticket_price == 0
    assert updated_days[0].hotel.estimated_cost_per_night == 250
    assert [meal.estimated_cost for meal in updated_days[0].meals] == [
        25,
        50,
        70,
    ]


def test_budget_reports_missing_trip_plan() -> None:
    result = calculate_budget({"request": make_request()})

    assert result == {
        "errors": ["Budget skipped because no trip plan is available."]
    }
