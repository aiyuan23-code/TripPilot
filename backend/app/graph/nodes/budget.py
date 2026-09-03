"""Deterministic budget calculation for a generated trip plan."""

from app.graph.state import TripState
from app.models.trip import Attraction, Budget, DayPlan, Hotel, Meal


TRANSPORT_DAILY_COST: dict[str, float] = {
    "public_transport": 30,
    "taxi": 100,
    "driving": 80,
}
DEFAULT_TRANSPORT_DAILY_COST = 30

HOTEL_NIGHTLY_ESTIMATES: dict[str, float] = {
    "hostel": 120,
    "economy": 250,
    "homestay": 300,
    "mid_range": 450,
    "boutique": 600,
    "resort": 800,
    "luxury": 900,
}

HOTEL_BUDGET_LEVEL_ESTIMATES: dict[str, float] = {
    "low": 180,
    "medium": 350,
    "high": 700,
}

MEAL_ESTIMATES: dict[str, dict[str, float]] = {
    "low": {
        "breakfast": 15,
        "lunch": 30,
        "dinner": 40,
        "snack": 15,
    },
    "medium": {
        "breakfast": 25,
        "lunch": 50,
        "dinner": 70,
        "snack": 25,
    },
    "high": {
        "breakfast": 50,
        "lunch": 100,
        "dinner": 150,
        "snack": 50,
    },
}

ATTRACTION_TICKET_ESTIMATES: dict[str, float] = {
    "low": 30,
    "medium": 60,
    "high": 120,
}

BUDGET_LEVEL_ALIASES: dict[str, str] = {
    "low": "low",
    "budget": "low",
    "economy": "low",
    "低": "low",
    "经济": "low",
    "medium": "medium",
    "mid": "medium",
    "中": "medium",
    "中等": "medium",
    "high": "high",
    "premium": "high",
    "luxury": "high",
    "高": "high",
    "豪华": "high",
}


def _round_cost(value: float) -> float:
    """Round monetary values to two decimal places."""
    return round(value, 2)


def _budget_level(value: str) -> str:
    """Normalize supported English and Chinese budget labels."""
    return BUDGET_LEVEL_ALIASES.get(value.strip().lower(), "medium")


def _estimate_hotel(
    hotel: Hotel,
    accommodation: str,
    budget_level: str,
) -> Hotel:
    """Keep a provider price or fill a deterministic nightly estimate."""
    if hotel.estimated_cost_per_night > 0:
        return hotel

    hotel_type = hotel.hotel_type or accommodation
    estimated_cost = HOTEL_NIGHTLY_ESTIMATES.get(
        hotel_type,
        HOTEL_BUDGET_LEVEL_ESTIMATES[budget_level],
    )
    return hotel.model_copy(
        update={"estimated_cost_per_night": estimated_cost}
    )


def _estimate_meal(meal: Meal, budget_level: str) -> Meal:
    """Keep a provider price or estimate one meal from its type."""
    if meal.estimated_cost > 0:
        return meal

    meal_type = meal.meal_type.strip().lower()
    estimated_cost = MEAL_ESTIMATES[budget_level].get(
        meal_type,
        MEAL_ESTIMATES[budget_level]["lunch"],
    )
    return meal.model_copy(update={"estimated_cost": estimated_cost})


def _estimate_attraction(
    attraction: Attraction,
    budget_level: str,
) -> Attraction:
    """Estimate missing tickets only for AMap scenic-spot type codes."""
    if attraction.ticket_price > 0:
        return attraction
    if not (attraction.type_code or "").startswith(("11", "14")):
        return attraction

    return attraction.model_copy(
        update={
            "ticket_price": ATTRACTION_TICKET_ESTIMATES[budget_level]
        }
    )


def calculate_budget(state: TripState) -> TripState:
    """Calculate the budget with Python and attach it to the trip plan."""
    trip_plan = state.get("trip_plan")
    if trip_plan is None:
        return {"errors": ["Budget skipped because no trip plan is available."]}

    request = state["request"]
    budget_level = _budget_level(request.budget_level)
    transport_per_day = TRANSPORT_DAILY_COST.get(
        request.transportation,
        DEFAULT_TRANSPORT_DAILY_COST,
    )
    hotel_nights = max(request.days - 1, 0)

    attraction_cost = 0.0
    hotel_cost = 0.0
    meal_cost = 0.0
    updated_days: list[DayPlan] = []

    for position, day in enumerate(trip_plan.days):
        updated_attractions = [
            _estimate_attraction(attraction, budget_level)
            for attraction in day.attractions
        ]
        updated_meals = [
            _estimate_meal(meal, budget_level) for meal in day.meals
        ]
        updated_hotel = day.hotel
        if position < hotel_nights and updated_hotel is not None:
            updated_hotel = _estimate_hotel(
                updated_hotel,
                request.accommodation,
                budget_level,
            )

        daily_attraction_cost = sum(
            attraction.ticket_price for attraction in updated_attractions
        )
        daily_meal_cost = sum(meal.estimated_cost for meal in updated_meals)
        daily_hotel_cost = 0.0
        if position < hotel_nights and updated_hotel is not None:
            daily_hotel_cost = updated_hotel.estimated_cost_per_night

        daily_cost = (
            daily_attraction_cost
            + daily_meal_cost
            + daily_hotel_cost
            + transport_per_day
        )
        updated_days.append(
            day.model_copy(
                update={
                    "attractions": updated_attractions,
                    "meals": updated_meals,
                    "hotel": updated_hotel,
                    "estimated_daily_cost": _round_cost(daily_cost),
                }
            )
        )

        attraction_cost += daily_attraction_cost
        meal_cost += daily_meal_cost
        hotel_cost += daily_hotel_cost

    transportation_cost = transport_per_day * request.days
    total = attraction_cost + hotel_cost + meal_cost + transportation_cost
    budget = Budget(
        attraction_cost=_round_cost(attraction_cost),
        hotel_cost=_round_cost(hotel_cost),
        meal_cost=_round_cost(meal_cost),
        transportation_cost=_round_cost(transportation_cost),
        total=_round_cost(total),
    )
    updated_plan = trip_plan.model_copy(
        update={"days": updated_days, "budget": budget}
    )
    return {"budget": budget, "trip_plan": updated_plan}
