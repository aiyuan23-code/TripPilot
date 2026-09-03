import operator
from typing import get_args, get_type_hints

import asyncio

from app.graph.nodes.prepare import prepare_request
from app.graph.state import TripState
from app.models import TripPlanRequest


def make_request() -> TripPlanRequest:
    return TripPlanRequest(
        city="成都",
        start_date="2026-09-01",
        end_date="2026-09-03",
        preferences=["历史文化", "美食"],
    )


def test_trip_state_errors_use_add_reducer() -> None:
    errors_annotation = get_type_hints(TripState, include_extras=True)["errors"]

    assert get_args(errors_annotation)[1] is operator.add


def test_prepare_request_initializes_workflow_bookkeeping() -> None:
    request = make_request()

    result = asyncio.run(prepare_request({"request": request}))

    assert result == {
        "request": request,
        "errors": [],
        "validation_errors": [],
        "repair_count": 0,
    }

