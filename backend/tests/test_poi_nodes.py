import asyncio
import json
from typing import Any

from app.graph.nodes.attraction import (
    build_attraction_keywords,
    parse_attractions,
    run_attraction_search,
)
from app.graph.nodes.hotel import (
    build_hotel_keywords,
    parse_hotels,
    run_hotel_search,
)
from app.graph.nodes.restaurant import (
    build_restaurant_keywords,
    parse_restaurants,
    run_restaurant_search,
)
from app.models import TripPlanRequest


def make_request() -> TripPlanRequest:
    return TripPlanRequest(
        city="成都",
        start_date="2026-09-01",
        end_date="2026-09-03",
        preferences=["历史文化", "美食"],
        accommodation="economy",
    )


def poi_payload() -> dict[str, Any]:
    return {
        "suggestion": {"keywords": [], "cities": []},
        "pois": [
            {
                "id": "B001",
                "name": "武侯祠",
                "address": "武侯祠大街231号",
                "typecode": "110200",
            },
            {
                "id": "B002",
                "name": "成都博物馆",
                "address": "小河街1号",
                "typecode": "140100",
            },
        ],
    }


class FakePOIRegistry:
    def __init__(
        self,
        result: Any = None,
        error: Exception | None = None,
        results_by_keyword: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        detail_error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.results_by_keyword = results_by_keyword or {}
        self.details = details or {}
        self.detail_error = detail_error
        self.calls: list[tuple[str, str]] = []
        self.detail_calls: list[str] = []

    async def search_poi(self, city: str, keywords: str) -> Any:
        self.calls.append((city, keywords))
        if self.error is not None:
            raise self.error
        return self.results_by_keyword.get(keywords, self.result)

    async def get_poi_detail(self, poi_id: str) -> Any:
        self.detail_calls.append(poi_id)
        if self.detail_error is not None:
            raise self.detail_error
        return self.details.get(poi_id, {})


def test_build_attraction_keywords_uses_preferences() -> None:
    assert build_attraction_keywords(["历史文化", "美食", "自然风光"]) == [
        "历史文化景点",
        "自然风光景区",
    ]
    assert build_attraction_keywords(["美食"]) == ["热门景点"]
    assert build_attraction_keywords([]) == ["热门景点"]


def test_build_hotel_keywords_maps_canonical_type() -> None:
    assert build_hotel_keywords("economy") == "经济型酒店"
    assert build_hotel_keywords("精品") == "精品酒店"
    assert build_hotel_keywords("青年旅舍") == "青年旅舍"


def test_build_restaurant_keywords_uses_food_preference() -> None:
    assert build_restaurant_keywords(["美食"]) == "特色餐厅"
    assert build_restaurant_keywords(["历史文化"]) == "餐厅"


def test_parse_poi_text_block_into_local_models() -> None:
    result = [{"type": "text", "text": json.dumps(poi_payload())}]

    attractions = parse_attractions(result)
    hotels = parse_hotels(result, "economy")
    restaurants = parse_restaurants(result)

    assert attractions[0].poi_id == "B001"
    assert attractions[0].name == "武侯祠"
    assert attractions[0].type_code == "110200"
    assert hotels[0].poi_id == "B001"
    assert hotels[0].hotel_type == "economy"
    assert restaurants[0].poi_id == "B001"
    assert restaurants[0].meal_type == "restaurant"


def test_parse_attractions_filters_non_attraction_pois() -> None:
    result = {
        "pois": [
            {"id": "A1", "name": "武侯祠", "typecode": "110200"},
            {"id": "A2", "name": "成都博物馆", "typecode": "140100"},
            {"id": "A3", "name": "太古里美食街", "typecode": "050000"},
            {"id": "A4", "name": "某酒店", "typecode": "100100"},
            {"id": "A5", "name": "某公交站", "typecode": "150700"},
            {"id": "A6", "name": "某购物中心", "typecode": "060100"},
        ]
    }

    attractions = parse_attractions(result)
    shopping_attractions = parse_attractions(result, include_shopping=True)

    assert [item.name for item in attractions] == ["武侯祠", "成都博物馆"]
    assert [item.name for item in shopping_attractions] == [
        "武侯祠",
        "成都博物馆",
        "某购物中心",
    ]


def test_attraction_node_queries_real_registry_contract() -> None:
    request = make_request()
    registry = FakePOIRegistry(result=poi_payload())

    result = asyncio.run(
        run_attraction_search({"request": request}, registry)  # type: ignore[arg-type]
    )

    assert registry.calls == [("成都", "历史文化景点")]
    assert registry.detail_calls == []
    assert [item.name for item in result["attractions"]] == ["武侯祠", "成都博物馆"]
    assert "errors" not in result


def test_attraction_node_searches_separately_and_merges_evenly() -> None:
    request = make_request().model_copy(
        update={"preferences": ["历史文化", "自然风光", "美食"]}
    )
    registry = FakePOIRegistry(
        results_by_keyword={
            "历史文化景点": {
                "pois": [
                    {"id": "H1", "name": "武侯祠", "typecode": "110200"},
                    {"id": "S1", "name": "人民公园", "typecode": "110101"},
                ]
            },
            "自然风光景区": {
                "pois": [
                    {"id": "N1", "name": "青城山", "typecode": "110202"},
                    {"id": "S1", "name": "人民公园", "typecode": "110101"},
                ]
            },
        }
    )

    result = asyncio.run(
        run_attraction_search(
            {"request": request}, registry  # type: ignore[arg-type]
        )
    )

    assert registry.calls == [
        ("成都", "历史文化景点"),
        ("成都", "自然风光景区"),
    ]
    assert [item.name for item in result["attractions"]] == [
        "武侯祠",
        "青城山",
        "人民公园",
    ]
    assert "errors" not in result


def test_hotel_node_queries_real_registry_contract() -> None:
    request = make_request()
    registry = FakePOIRegistry(result=poi_payload())

    result = asyncio.run(
        run_hotel_search({"request": request}, registry)  # type: ignore[arg-type]
    )

    assert registry.calls == [("成都", "经济型酒店")]
    assert registry.detail_calls == []
    assert len(result["hotels"]) == 2
    assert result["hotels"][0].hotel_type == "economy"
    assert "errors" not in result


def test_search_nodes_leave_detail_loading_until_after_planner() -> None:
    request = make_request()
    registry = FakePOIRegistry(
        result=poi_payload(),
        details={
            "B001": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "id": "B001",
                            "address": "更新后的地址",
                            "location": "104.047,30.647",
                            "rating": "4.8",
                            "cost": "88.00",
                            "lowest_price": "320.00",
                        }
                    ),
                }
            ],
            "B002": {
                "id": "B002",
                "location": "104.072,30.663",
                "rating": [],
            },
        },
    )

    attraction_result = asyncio.run(
        run_attraction_search(
            {"request": request}, registry  # type: ignore[arg-type]
        )
    )
    hotel_result = asyncio.run(
        run_hotel_search(
            {"request": request}, registry  # type: ignore[arg-type]
        )
    )

    assert attraction_result["attractions"][0].location is None
    assert hotel_result["hotels"][0].location is None
    assert registry.detail_calls == []


def test_restaurant_node_returns_basic_candidates_for_planner() -> None:
    request = make_request()
    registry = FakePOIRegistry(
        result=poi_payload(),
        details={
            "B001": {
                "id": "B001",
                "location": "104.047,30.647",
                "rating": "4.8",
                "cost": "88.00",
            },
            "B002": {},
        },
    )

    result = asyncio.run(
        run_restaurant_search(
            {"request": request}, registry  # type: ignore[arg-type]
        )
    )

    restaurant = result["restaurants"][0]
    assert registry.calls == [("成都", "特色餐厅")]
    assert restaurant.poi_id == "B001"
    assert restaurant.location is None
    assert restaurant.rating is None
    assert restaurant.estimated_cost == 0
    assert registry.detail_calls == []


def test_search_result_does_not_depend_on_detail_service() -> None:
    request = make_request()
    registry = FakePOIRegistry(
        result=poi_payload(),
        detail_error=RuntimeError("detail unavailable"),
    )

    result = asyncio.run(
        run_attraction_search(
            {"request": request}, registry  # type: ignore[arg-type]
        )
    )

    assert [item.name for item in result["attractions"]] == [
        "武侯祠",
        "成都博物馆",
    ]
    assert all(item.location is None for item in result["attractions"])
    assert "errors" not in result


def test_poi_nodes_capture_mcp_errors() -> None:
    request = make_request()
    attraction_registry = FakePOIRegistry(error=RuntimeError("connection lost"))
    hotel_registry = FakePOIRegistry(error=RuntimeError("connection lost"))

    attraction_result = asyncio.run(
        run_attraction_search(
            {"request": request}, attraction_registry  # type: ignore[arg-type]
        )
    )
    hotel_result = asyncio.run(
        run_hotel_search({"request": request}, hotel_registry)  # type: ignore[arg-type]
    )

    assert attraction_result["attractions"] == []
    assert attraction_result["errors"] == [
        "Attraction query '历史文化景点' failed: connection lost"
    ]
    assert hotel_result["hotels"] == []
    assert hotel_result["errors"] == ["Hotel search failed: connection lost"]


def test_poi_node_redacts_api_key_from_provider_error() -> None:
    request = make_request()
    registry = FakePOIRegistry(
        result={
            "error": (
                "Request failed: https://restapi.amap.com/v3/place/text"
                "?key=secret-value&keywords=hotel"
            )
        }
    )

    result = asyncio.run(
        run_hotel_search({"request": request}, registry)  # type: ignore[arg-type]
    )

    assert "secret-value" not in result["errors"][0]
    assert "key=<redacted>" in result["errors"][0]
