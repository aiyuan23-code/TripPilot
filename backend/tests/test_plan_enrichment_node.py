import asyncio
from typing import Any

from app.graph.nodes.plan_enrichment import run_plan_detail_enrichment
from app.models import Attraction, DayPlan, Hotel, Meal, TripPlan, TripPlanRequest


class FakeDetailRegistry:
    def __init__(self, details: dict[str, Any]) -> None:
        self.details = details
        self.calls: list[str] = []

    async def get_poi_details(self, poi_ids: list[str]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for poi_id in poi_ids:
            self.calls.append(poi_id)
            value = self.details[poi_id]
            if not isinstance(value, Exception):
                output[poi_id] = value
        return output


def make_state():
    request = TripPlanRequest(
        city="成都",
        start_date="2026-09-02",
        end_date="2026-09-03",
    )
    hotel = Hotel(poi_id="H1", name="真实酒店", hotel_type="economy")
    restaurant = Meal(
        poi_id="R1",
        meal_type="lunch",
        name="真实餐厅",
    )
    plan = TripPlan(
        city="成都",
        start_date=request.start_date,
        end_date=request.end_date,
        days=[
            DayPlan(
                date="2026-09-02",
                day_index=1,
                attractions=[
                    Attraction(
                        poi_id="A1",
                        name="真实景区",
                        type_code="110200",
                    )
                ],
                meals=[restaurant],
                hotel=hotel,
            ),
            DayPlan(
                date="2026-09-03",
                day_index=2,
                attractions=[Attraction(name="无 ID 景点")],
                meals=[restaurant],
                hotel=hotel,
            ),
        ],
        weather_info=[],
        overall_suggestions="测试",
    )
    return {"request": request, "trip_plan": plan}


def test_enrichment_adds_real_details_and_deduplicates_ids() -> None:
    state = make_state()
    registry = FakeDetailRegistry(
        {
            "A1": {
                "location": "104.01,30.61",
                "rating": "4.7",
                "cost": "80.00",
            },
            "H1": {
                "location": "104.02,30.62",
                "rating": "4.5",
                "lowest_price": "388.00",
            },
            "R1": {
                "location": "104.03,30.63",
                "rating": "4.8",
                "cost": "66.00",
            },
        }
    )

    result = asyncio.run(
        run_plan_detail_enrichment(
            state, registry  # type: ignore[arg-type]
        )
    )

    plan = result["trip_plan"]
    attraction = plan.days[0].attractions[0]
    hotel = plan.days[0].hotel
    meal = plan.days[0].meals[0]
    assert sorted(registry.calls) == ["A1", "H1", "R1"]
    assert attraction.location.longitude == 104.01
    assert attraction.rating == 4.7
    assert attraction.ticket_price == 80
    assert hotel.location.longitude == 104.02
    assert hotel.rating == 4.5
    assert hotel.estimated_cost_per_night == 388
    assert meal.location.longitude == 104.03
    assert meal.rating == 4.8
    assert meal.estimated_cost == 66


def test_enrichment_keeps_item_when_detail_fails() -> None:
    state = make_state()
    registry = FakeDetailRegistry(
        {
            "A1": RuntimeError("unavailable"),
            "H1": RuntimeError("unavailable"),
            "R1": RuntimeError("unavailable"),
        }
    )

    result = asyncio.run(
        run_plan_detail_enrichment(
            state, registry  # type: ignore[arg-type]
        )
    )

    plan = result["trip_plan"]
    assert plan.days[0].attractions[0].location is None
    assert plan.days[0].hotel.estimated_cost_per_night == 0
    assert plan.days[0].meals[0].estimated_cost == 0
