"""
Exposes TalentFlow's core capabilities as MCP (Model Context Protocol)
tools, so any MCP-compatible client (Claude Desktop, an MCP Inspector, or
your own agentic chatbot from the RAG/MCP project) can call into the
recruiting pipeline with natural language instead of hitting the REST API
directly.

Run standalone:
    python -m app.mcp_server

This mirrors the MCP tool-integration pattern from the resume's "Multi-
Utility AI Chatbot with RAG & MCP" project, applied to a recruiting domain:
stock-price/web-search tools there, candidate-search/screening tools here.
"""
from mcp.server.fastmcp import FastMCP

from app.database import SessionLocal
from app.models.job import Job
from app.models.candidate import Candidate
from app.services.vector_store import get_vector_store
from app.agents.resume_screening_agent import ResumeScreeningAgent

mcp = FastMCP("talentflow-recruiting")


@mcp.tool()
def search_candidates(query: str, top_k: int = 5) -> list[dict]:
    """
    Semantically search previously-screened candidates by free-text
    description (skills, role, experience). Returns the closest matches
    with similarity scores via the FAISS index.
    """
    results = get_vector_store().search(query, top_k=top_k)
    return [{"candidate": meta, "score": round(score, 4)} for meta, score in results]


@mcp.tool()
def get_candidate_status(candidate_id: int) -> dict:
    """Look up a candidate's current pipeline stage and screening score."""
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return {"error": f"No candidate with id {candidate_id}"}
        return {
            "id": candidate.id,
            "name": candidate.name,
            "stage": candidate.stage,
            "overall_score": candidate.screening_result.overall_score if candidate.screening_result else None,
        }
    finally:
        db.close()


@mcp.tool()
def score_resume_against_job(resume_text: str, job_id: int) -> dict:
    """
    Score a resume against a specific job's requirements without creating a
    candidate record — useful for a recruiter pasting a resume into chat
    and asking "would this person clear our bar for job 3?".
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"error": f"No job with id {job_id}"}
    finally:
        db.close()

    agent = ResumeScreeningAgent()
    return agent.run(
        resume_text=resume_text,
        job_description=job.description,
        required_skills=job.required_skills or [],
    )


@mcp.tool()
def list_open_jobs() -> list[dict]:
    """List all jobs currently open in the system."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).all()
        return [{"id": j.id, "title": j.title, "required_skills": j.required_skills} for j in jobs]
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
