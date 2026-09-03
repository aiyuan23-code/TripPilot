"""Run the real TripPilot research graph from the command line."""

import argparse
import asyncio
from datetime import date, timedelta
import json
from pathlib import Path
import sys
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.graph import build_trip_graph
from app.models import TripPlanRequest


def parse_args() -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(description="Run the TripPilot research graph")
    parser.add_argument("--city", default="成都")
    parser.add_argument("--start-date", default=today.isoformat())
    parser.add_argument(
        "--end-date",
        default=(today + timedelta(days=2)).isoformat(),
    )
    parser.add_argument(
        "--preferences",
        nargs="*",
        default=["历史文化", "美食"],
    )
    parser.add_argument("--budget-level", default="medium")
    parser.add_argument("--transportation", default="public_transport")
    parser.add_argument("--accommodation", default="economy")
    return parser.parse_args()


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


async def run(args: argparse.Namespace) -> None:
    request = TripPlanRequest(
        city=args.city,
        start_date=args.start_date,
        end_date=args.end_date,
        preferences=args.preferences,
        budget_level=args.budget_level,
        transportation=args.transportation,
        accommodation=args.accommodation,
    )
    graph = build_trip_graph()
    result = await graph.ainvoke({"request": request})
    print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2, default=str))



def main() -> None:
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()

