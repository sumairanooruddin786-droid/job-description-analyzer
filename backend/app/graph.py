"""LangGraph workflow:  START -> extract -> classify -> skills -> report -> END
If the input is not a job description, the graph stops right after node 1."""
from langgraph.graph import END, START, StateGraph

from .nodes import (
    JobState,
    hiring_report,
    information_extraction,
    job_classification,
    skill_analysis,
)


def _after_extraction(state: JobState) -> str:
    return "stop" if state.get("error") else "continue"


def build_graph():
    graph = StateGraph(JobState)

    graph.add_node("extract", information_extraction)
    graph.add_node("classify", job_classification)
    graph.add_node("skills", skill_analysis)
    graph.add_node("report", hiring_report)

    graph.add_edge(START, "extract")
    graph.add_conditional_edges("extract", _after_extraction, {"continue": "classify", "stop": END})
    graph.add_edge("classify", "skills")
    graph.add_edge("skills", "report")
    graph.add_edge("report", END)

    return graph.compile()


workflow = build_graph()
