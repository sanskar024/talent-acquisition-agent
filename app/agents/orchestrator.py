"""
The orchestrator is a LangGraph state machine that routes a candidate
through the pipeline, calling one agent per node and branching on their
output (e.g. auto-reject below the screening threshold instead of wasting
an interview slot).

Each node appends to `state["trace"]`, giving a full audit trail of which
agent ran, with what inputs/outputs, for every candidate — this is what
makes the bias-mitigation story (README) actually inspectable rather than
just asserted.
"""
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from app.agents.resume_screening_agent import ResumeScreeningAgent
from app.agents.interview_scheduling_agent import InterviewSchedulingAgent
from app.agents.prescreening_agent import PrescreeningAgent
from app.agents.assessment_agent import AssessmentAgent
from app.agents.decision_support_agent import DecisionSupportAgent
from app.agents.communication_agent import CommunicationAgent
from app.services.vector_store import get_vector_store


class PipelineState(TypedDict, total=False):
    candidate_id: int
    job_id: int
    candidate_name: Optional[str]
    candidate_email: Optional[str]
    resume_text: str
    job_title: str
    job_description: str
    required_skills: List[str]

    screening: Dict[str, Any]
    interview: Dict[str, Any]
    prescreen: Dict[str, Any]
    assessment: Dict[str, Any]
    decision: Dict[str, Any]

    stage: str
    trace: List[Dict[str, Any]]


_screening_agent = ResumeScreeningAgent()
_scheduling_agent = InterviewSchedulingAgent()
_prescreening_agent = PrescreeningAgent()
_assessment_agent = AssessmentAgent()
_decision_agent = DecisionSupportAgent()
_communication_agent = CommunicationAgent()


def _screen_node(state: PipelineState) -> PipelineState:
    result = _screening_agent.run(
        resume_text=state["resume_text"],
        job_description=state["job_description"],
        required_skills=state["required_skills"],
    )
    state["screening"] = result
    state["trace"].append({"stage": "screening", **result})
    state["stage"] = "screening"

    # Index every screened candidate in the FAISS store so recruiters can
    # later run semantic search ("find someone like this") across the pool,
    # regardless of whether they pass this specific job's threshold.
    try:
        get_vector_store().add(
            candidate_id=state["candidate_id"],
            name=state.get("candidate_name"),
            job_id=state.get("job_id", 0),
            resume_text=state["resume_text"],
        )
    except Exception as exc:  # pragma: no cover - indexing must never break the pipeline
        state["trace"].append({"stage": "vector_index", "error": str(exc)})

    return state


def _route_after_screening(state: PipelineState) -> str:
    return "schedule" if state["screening"]["passed"] else "reject_after_screening"


def _reject_after_screening_node(state: PipelineState) -> PipelineState:
    _communication_agent.notify(state.get("candidate_email"), "screening_rejected", state["job_title"])
    state["stage"] = "rejected"
    state["trace"].append({"stage": "rejected", "reason": "did not clear screening threshold"})
    return state


def _schedule_node(state: PipelineState) -> PipelineState:
    result = _scheduling_agent.run(
        candidate_id=state["candidate_id"],
        candidate_email=state.get("candidate_email"),
        job_title=state["job_title"],
    )
    state["interview"] = result
    state["trace"].append({"stage": "scheduling", **result})
    state["stage"] = "scheduling"
    return state


def _prescreen_node(state: PipelineState) -> PipelineState:
    result = _prescreening_agent.run(
        candidate_id=state["candidate_id"],
        transcript=None,  # demo: synthesizes a transcript. Real flow: actual chat/call transcript.
        job_title=state["job_title"],
    )
    state["prescreen"] = result
    state["trace"].append({"stage": "prescreen", **result})
    state["stage"] = "prescreen"
    return state


def _assessment_node(state: PipelineState) -> PipelineState:
    questions = _assessment_agent.generate_assessment(state["required_skills"])
    # NOTE: for this end-to-end demo we synthesize plausible answers so the
    # full pipeline can run without a human in the loop. In production,
    # `answers` would come from a real candidate submission via a separate
    # `/assessments/{id}/submit` endpoint, and this node would instead be
    # split into "issue assessment" (here) + "grade assessment" (triggered
    # by that submission).
    demo_answers = [
        f"I used {q.split('used ')[-1].rstrip('.')} to build a production feature; "
        f"the main challenge was performance under load, which I solved by profiling and caching."
        for q in questions
    ]
    result = _assessment_agent.run(
        candidate_id=state["candidate_id"],
        questions=questions,
        answers=demo_answers,
    )
    state["assessment"] = result
    state["trace"].append({"stage": "assessment", **result})
    state["stage"] = "assessment"
    return state


def _decide_node(state: PipelineState) -> PipelineState:
    result = _decision_agent.run(
        candidate_id=state["candidate_id"],
        screening_score=state["screening"]["overall_score"],
        prescreen_signals=state["prescreen"]["signals"],
        assessment_score=state["assessment"]["overall_score"],
        bias_flags=state["screening"]["bias_flags"],
    )
    state["decision"] = result
    state["trace"].append({"stage": "decision", **result})
    state["stage"] = result["recommendation"]

    _communication_agent.notify(state.get("candidate_email"), result["recommendation"], state["job_title"])
    return state


def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("screen", _screen_node)
    graph.add_node("reject_after_screening", _reject_after_screening_node)
    graph.add_node("schedule", _schedule_node)
    graph.add_node("prescreen", _prescreen_node)
    graph.add_node("assess", _assessment_node)
    graph.add_node("decide", _decide_node)

    graph.set_entry_point("screen")
    graph.add_conditional_edges(
        "screen",
        _route_after_screening,
        {"schedule": "schedule", "reject_after_screening": "reject_after_screening"},
    )
    graph.add_edge("reject_after_screening", END)
    graph.add_edge("schedule", "prescreen")
    graph.add_edge("prescreen", "assess")
    graph.add_edge("assess", "decide")
    graph.add_edge("decide", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_pipeline(
    candidate_id: int,
    resume_text: str,
    job_title: str,
    job_description: str,
    required_skills: List[str],
    candidate_name: Optional[str] = None,
    candidate_email: Optional[str] = None,
    job_id: int = 0,
) -> PipelineState:
    initial_state: PipelineState = {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "resume_text": resume_text,
        "job_title": job_title,
        "job_description": job_description,
        "required_skills": required_skills,
        "trace": [],
    }
    return get_graph().invoke(initial_state)
