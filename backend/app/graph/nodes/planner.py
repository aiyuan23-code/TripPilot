"""Structured-output LLM planner node."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import get_settings
from app.core.llm import get_llm
from app.core.security import redact_sensitive_text
from app.graph.state import TripState
from app.models.trip import Attraction, DayPlan, Hotel, Meal, TripPlan
from app.prompts.planner import PLANNER_SYSTEM_PROMPT


def build_planner_messages(state: TripState) -> list[SystemMessage | HumanMessage]:
    """Build planner context exclusively from request and researched candidates."""
    request = state["request"]
    payload = {
        "request": request.model_dump(mode="json"),
        "calculated_trip_days": request.days,
        "output_schema": TripPlan.model_json_schema(),
        "attractions": [
            item.model_dump(mode="json") for item in state.get("attractions", [])
        ],
        "weather_info": [
            item.model_dump(mode="json") for item in state.get("weather_info", [])
        ],
        "hotels": [item.model_dump(mode="json") for item in state.get("hotels", [])],
        "restaurants": [
            item.model_dump(mode="json") for item in state.get("restaurants", [])
        ],
        "upstream_errors": state.get("errors", []),
    }
    return [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "请根据以下真实数据生成旅行计划：\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
            )
        ),
    ]


def _item_key(poi_id: str | None, name: str) -> str:
    """Prefer AMap's stable ID and fall back to a normalized name."""
    return poi_id or name.strip().casefold()


def _canonicalize_trip_plan(trip_plan: TripPlan, state: TripState) -> TripPlan:
    """Restore provider-owned POI fields after LLM itinerary generation."""
    attractions = {
        _item_key(item.poi_id, item.name): item
        for item in state.get("attractions", [])
    }
    hotels = {
        _item_key(item.poi_id, item.name): item for item in state.get("hotels", [])
    }
    restaurants = {
        _item_key(item.poi_id, item.name): item
        for item in state.get("restaurants", [])
    }

    updated_days: list[DayPlan] = []
    for day in trip_plan.days:
        updated_attractions: list[Attraction] = []
        for attraction in day.attractions:
            candidate = attractions.get(
                _item_key(attraction.poi_id, attraction.name)
            )
            if candidate is None:
                updated_attractions.append(attraction)
                continue
            updated_attractions.append(
                candidate.model_copy(
                    update={
                        "description": attraction.description,
                        "visit_duration": attraction.visit_duration,
                        "image_url": attraction.image_url or candidate.image_url,
                    }
                )
            )

        updated_hotel: Hotel | None = day.hotel
        if day.hotel is not None:
            candidate_hotel = hotels.get(
                _item_key(day.hotel.poi_id, day.hotel.name)
            )
            if candidate_hotel is not None:
                updated_hotel = candidate_hotel

        updated_meals: list[Meal] = []
        for meal in day.meals:
            candidate_meal = restaurants.get(_item_key(meal.poi_id, meal.name))
            if candidate_meal is None:
                updated_meals.append(meal)
                continue
            updated_meals.append(
                candidate_meal.model_copy(
                    update={
                        "meal_type": meal.meal_type,
                        "description": meal.description,
                    }
                )
            )

        updated_days.append(
            day.model_copy(
                update={
                    "attractions": updated_attractions,
                    "hotel": updated_hotel,
                    "meals": updated_meals,
                }
            )
        )

    return trip_plan.model_copy(update={"days": updated_days})


async def run_planner(
    state: TripState,
    llm: Any,
    *,
    structured_output_method: str = "function_calling",
) -> TripState:
    """Generate a TripPlan with an injectable LLM for deterministic tests."""
    request = state["request"]
    if not state.get("attractions"):
        return {
            "errors": ["Planner skipped because no attraction candidates are available."]
        }

    try:
        structured_llm = llm.with_structured_output(
            TripPlan,
            method=structured_output_method,
        )
        output = await structured_llm.ainvoke(build_planner_messages(state))
        trip_plan = TripPlan.model_validate(output)
        trip_plan = _canonicalize_trip_plan(trip_plan, state)
        trip_plan = trip_plan.model_copy(
            update={
                "city": request.city,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "weather_info": list(state.get("weather_info", [])),
                "budget": None,
            }
        )
        return {"trip_plan": trip_plan}
    except Exception as exc:
        return {
            "errors": [f"Planner failed: {redact_sensitive_text(exc)}"],
        }


async def planner(state: TripState) -> TripState:
    """LangGraph entry point using the configured provider and model."""
    try:
        settings = get_settings()
        llm = get_llm()
        return await run_planner(
            state,
            llm,
            structured_output_method=settings.llm_structured_output_method,
        )
    except Exception as exc:
        return {"errors": [f"Planner setup failed: {redact_sensitive_text(exc)}"]}
