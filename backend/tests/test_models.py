from datetime import date

import pytest
from pydantic import ValidationError

from app.models import (
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Location,
    Meal,
    TripPlan,
    TripPlanRequest,
    WeatherInfo,
)


def test_trip_request_calculates_inclusive_days() -> None:
    request = TripPlanRequest(
        city="成都",
        start_date="2026-10-01",
        end_date="2026-10-03",
        preferences=["历史文化", "美食"],
    )

    assert request.days == 3
    assert request.start_date == date(2026, 10, 1)
    assert request.budget_level == "medium"


def test_single_day_trip_has_one_day() -> None:
    request = TripPlanRequest(
        city="北京",
        start_date="2026-10-01",
        end_date="2026-10-01",
    )

    assert request.days == 1


def test_trip_request_rejects_end_date_before_start_date() -> None:
    with pytest.raises(ValidationError, match="end_date must be on or after start_date"):
        TripPlanRequest(
            city="成都",
            start_date="2026-10-03",
            end_date="2026-10-01",
        )


def test_trip_request_normalizes_text_input() -> None:
    request = TripPlanRequest(
        city="  成都  ",
        start_date="2026-10-01",
        end_date="2026-10-03",
        preferences=[" 历史文化 ", " ", "美食"],
    )

    assert request.city == "成都"
    assert request.preferences == ["历史文化", "美食"]


def test_trip_request_accepts_text_preferences_and_budget_level() -> None:
    request = TripPlanRequest(
        city="成都",
        start_date="2026-10-01",
        end_date="2026-10-03",
        preferences="历史文化，美食、自然风光，历史文化",
        budget_level="medium",
    )

    assert request.preferences == ["历史文化", "美食", "自然风光"]
    assert request.budget_level == "medium"


def test_trip_request_rejects_blank_city() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        TripPlanRequest(
            city="   ",
            start_date="2026-10-01",
            end_date="2026-10-03",
        )


@pytest.mark.parametrize(
    ("longitude", "latitude"),
    [(181, 30), (-181, 30), (104, 91), (104, -91)],
)
def test_location_rejects_out_of_range_coordinates(
    longitude: float,
    latitude: float,
) -> None:
    with pytest.raises(ValidationError):
        Location(longitude=longitude, latitude=latitude)


def test_list_defaults_are_not_shared_between_instances() -> None:
    first = DayPlan(date="2026-10-01", day_index=1)
    second = DayPlan(date="2026-10-02", day_index=2)

    first.attractions.append(Attraction(name="武侯祠"))

    assert second.attractions == []


def test_complete_trip_plan_validates_and_serializes() -> None:
    location = Location(longitude=104.047, latitude=30.647)
    attraction = Attraction(
        name="武侯祠",
        address="成都市武侯区武侯祠大街231号",
        location=location,
        rating=4.8,
        ticket_price=50,
    )
    hotel = Hotel(
        name="示例酒店",
        location=location,
        hotel_type="economy",
        estimated_cost_per_night=300,
    )
    meal = Meal(
        type="lunch",
        name="川菜",
        address="成都市武侯区",
        location=location,
        estimated_cost=80,
    )
    weather = WeatherInfo(
        date="2026-10-01",
        day_weather="晴",
        day_temp=25,
    )
    budget = Budget(
        attraction_cost=50,
        hotel_cost=600,
        meal_cost=240,
        transportation_cost=90,
        total=980,
    )

    plan = TripPlan(
        city="成都",
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[
            DayPlan(
                date="2026-10-01",
                day_index=1,
                attractions=[attraction],
                meals=[meal],
                hotel=hotel,
                transportation="public_transport",
                accommodation="经济型酒店",
                estimated_daily_cost=980,
            )
        ],
        weather_info=[weather],
        overall_suggestions="国庆期间建议提前预约景点。",
        budget=budget,
    )

    payload = plan.model_dump(mode="json")

    assert payload["city"] == "成都"
    assert payload["start_date"] == "2026-10-01"
    assert payload["days"][0]["attractions"][0]["name"] == "武侯祠"
    assert payload["days"][0]["meals"][0]["meal_type"] == "lunch"
    assert payload["budget"]["total"] == 980


def test_cost_fields_reject_negative_values() -> None:
    with pytest.raises(ValidationError):
        Budget(total=-1)


@pytest.mark.parametrize(
    ("raw_temperature", "expected"),
    [("16°C", 16), ("-2℃", -2), ("25°", 25), (" -- ", None)],
)
def test_weather_normalizes_provider_temperature_strings(
    raw_temperature: str,
    expected: int | None,
) -> None:
    weather = WeatherInfo(
        date="2026-10-01",
        day_weather="晴",
        day_temp=raw_temperature,
    )

    assert weather.day_temp == expected


def test_hotel_uses_canonical_field_names() -> None:
    hotel = Hotel(
        name="示例酒店",
        hotel_type="economy",
        estimated_cost_per_night=320,
        price_range="300-400 元",
        distance="距武侯祠 1.2 公里",
    )

    assert hotel.hotel_type == "economy"
    assert hotel.estimated_cost_per_night == 320
