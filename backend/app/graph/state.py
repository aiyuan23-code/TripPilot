"""Typed shared state passed between TripPilot graph nodes."""

import operator
from typing import Annotated, TypedDict

from app.models.request import TripPlanRequest
from app.models.trip import Attraction, Budget, Hotel, Meal, TripPlan, WeatherInfo


class TripState(TypedDict, total=False):
    """Shared state for the complete trip-planning workflow."""

    request: TripPlanRequest
    attractions: list[Attraction]
    weather_info: list[WeatherInfo]
    hotels: list[Hotel]
    restaurants: list[Meal]
    trip_plan: TripPlan
    budget: Budget
    errors: Annotated[list[str], operator.add]
    validation_errors: list[str]
    repair_count: int
