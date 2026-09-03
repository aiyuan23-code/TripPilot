"""Build and compile the TripPilot LangGraph workflow."""

from langgraph.graph import END, START, StateGraph

from app.graph.nodes.attraction import attraction_search
from app.graph.nodes.budget import calculate_budget
from app.graph.nodes.collect import collect_results
from app.graph.nodes.hotel import hotel_search
from app.graph.nodes.plan_enrichment import enrich_plan_details
from app.graph.nodes.planner import planner
from app.graph.nodes.prepare import prepare_request
from app.graph.nodes.restaurant import restaurant_search
from app.graph.nodes.validator import validate_plan
from app.graph.nodes.weather import weather_query
from app.graph.state import TripState


def build_trip_graph():
    """Compile the current real-data research workflow."""
    graph = StateGraph(TripState)

    graph.add_node("prepare_request", prepare_request)
    graph.add_node("attraction_search", attraction_search)
    graph.add_node("weather_query", weather_query)
    graph.add_node("hotel_search", hotel_search)
    graph.add_node("restaurant_search", restaurant_search)
    graph.add_node("collect_results", collect_results)
    graph.add_node("planner", planner)
    graph.add_node("enrich_plan_details", enrich_plan_details)
    graph.add_node("calculate_budget", calculate_budget)
    graph.add_node("validate_plan", validate_plan)

    graph.add_edge(START, "prepare_request")

    graph.add_edge("prepare_request", "attraction_search")
    graph.add_edge("prepare_request", "weather_query")
    graph.add_edge("prepare_request", "hotel_search")
    graph.add_edge("prepare_request", "restaurant_search")

    graph.add_edge(
        [
            "attraction_search",
            "weather_query",
            "hotel_search",
            "restaurant_search",
        ],
        "collect_results",
    )
    graph.add_edge("collect_results", "planner")
    graph.add_edge("planner", "enrich_plan_details")
    graph.add_edge("enrich_plan_details", "calculate_budget")
    graph.add_edge("calculate_budget", "validate_plan")
    graph.add_edge("validate_plan", END)

    return graph.compile()
