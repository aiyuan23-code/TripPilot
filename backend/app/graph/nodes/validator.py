"""Deterministic validation for a completed trip plan."""

from datetime import timedelta

from app.graph.state import TripState


def _attraction_identity(poi_id: str | None, name: str) -> str:
    """Build a stable identity for duplicate-attraction checks."""
    return poi_id or name.strip().casefold()


def validate_plan(state: TripState) -> TripState:
    """Check whether the final plan satisfies TripPilot's basic rules."""
    trip_plan = state.get("trip_plan")
    if trip_plan is None:
        return {"validation_errors": ["未生成旅行计划。"]}

    request = state["request"]
    validation_errors: list[str] = []

    if len(trip_plan.days) != request.days:
        validation_errors.append(
            f"行程应包含 {request.days} 天，实际为 {len(trip_plan.days)} 天。"
        )

    expected_dates = {
        request.start_date + timedelta(days=offset)
        for offset in range(request.days)
    }
    actual_dates = {day.date for day in trip_plan.days}
    missing_dates = sorted(expected_dates - actual_dates)
    if missing_dates:
        text = "、".join(item.isoformat() for item in missing_dates)
        validation_errors.append(f"行程缺少日期：{text}。")

    seen_attractions: set[str] = set()
    hotel_nights = max(request.days - 1, 0)
    has_hotel_candidates = bool(state.get("hotels"))

    for position, day in enumerate(trip_plan.days):
        expected_index = position + 1
        if day.day_index != expected_index:
            validation_errors.append(
                f"第 {expected_index} 个行程的 day_index 应为 {expected_index}，"
                f"实际为 {day.day_index}。"
            )

        attraction_count = len(day.attractions)
        if not 1 <= attraction_count <= 4:
            validation_errors.append(
                f"第 {day.day_index} 天应安排 1 至 4 个景点，"
                f"实际为 {attraction_count} 个。"
            )

        for attraction in day.attractions:
            identity = _attraction_identity(attraction.poi_id, attraction.name)
            if identity in seen_attractions:
                validation_errors.append(f"景点重复安排：{attraction.name}。")
            else:
                seen_attractions.add(identity)

        if has_hotel_candidates and position < hotel_nights and day.hotel is None:
            validation_errors.append(f"第 {day.day_index} 天缺少住宿酒店。")

    available_weather = state.get("weather_info", [])
    if available_weather:
        weather_dates = {item.date for item in available_weather}
        missing_weather_dates = sorted(expected_dates - weather_dates)
        if missing_weather_dates:
            text = "、".join(item.isoformat() for item in missing_weather_dates)
            validation_errors.append(f"天气信息未覆盖日期：{text}。")

    budget = state.get("budget") or trip_plan.budget
    if budget is None:
        validation_errors.append("行程缺少预算信息。")
    else:
        component_total = (
            budget.attraction_cost
            + budget.hotel_cost
            + budget.meal_cost
            + budget.transportation_cost
        )
        if abs(component_total - budget.total) > 0.01:
            validation_errors.append("预算总额与各项费用之和不一致。")

    return {"validation_errors": validation_errors}
