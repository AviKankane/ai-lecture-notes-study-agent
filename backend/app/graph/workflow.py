from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes import (
    classify_transcript_size,
    generate_quiz,
    index_chunks,
    load_lecture,
    mark_done,
    mark_failed,
    process_short_transcript,
    repair_outputs,
    structure_transcript,
    summarize_sections,
    transcribe_audio,
    validate_outputs,
)
from .state import LectureGraphState


def route_by_size(state: LectureGraphState) -> str:
    return "short" if state.get("word_count", 0) < 500 else "long"


def route_after_validation(state: LectureGraphState) -> str:
    if not state.get("error"):
        return "valid"
    if state.get("retry_count", 0) < 2:
        return "repair"
    return "failed"


def build_workflow():
    graph = StateGraph(LectureGraphState)
    graph.add_node("load_lecture", load_lecture)
    graph.add_node("transcribe_audio", transcribe_audio)
    graph.add_node("classify_transcript_size", classify_transcript_size)
    graph.add_node("process_short_transcript", process_short_transcript)
    graph.add_node("structure_transcript", structure_transcript)
    graph.add_node("summarize_sections", summarize_sections)
    graph.add_node("generate_quiz", generate_quiz)
    graph.add_node("validate_outputs", validate_outputs)
    graph.add_node("repair_outputs", repair_outputs)
    graph.add_node("index_chunks", index_chunks)
    graph.add_node("mark_done", mark_done)
    graph.add_node("mark_failed", mark_failed)

    graph.add_edge(START, "load_lecture")
    graph.add_edge("load_lecture", "transcribe_audio")
    graph.add_edge("transcribe_audio", "classify_transcript_size")
    graph.add_conditional_edges(
        "classify_transcript_size",
        route_by_size,
        {
            "short": "process_short_transcript",
            "long": "structure_transcript",
        },
    )
    graph.add_edge("process_short_transcript", "validate_outputs")
    graph.add_edge("structure_transcript", "summarize_sections")
    graph.add_edge("summarize_sections", "generate_quiz")
    graph.add_edge("generate_quiz", "validate_outputs")
    graph.add_conditional_edges(
        "validate_outputs",
        route_after_validation,
        {
            "valid": "index_chunks",
            "repair": "repair_outputs",
            "failed": "mark_failed",
        },
    )
    graph.add_edge("repair_outputs", "validate_outputs")
    graph.add_edge("index_chunks", "mark_done")
    graph.add_edge("mark_done", END)
    graph.add_edge("mark_failed", END)

    return graph.compile()


workflow = build_workflow()

