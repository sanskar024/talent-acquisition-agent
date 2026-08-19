from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job import Job
from app.models.candidate import (
    Candidate,
    ScreeningResult,
    Interview,
    Assessment,
    Decision,
    PipelineStage,
)
from app.schemas.candidate import PipelineRunRequest, PipelineRunResponse
from app.agents.orchestrator import run_pipeline

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run", response_model=PipelineRunResponse)
def run(payload: PipelineRunRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = Candidate(
        job_id=job.id,
        name=payload.name,
        email=payload.email,
        resume_text=payload.resume_text,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    final_state = run_pipeline(
        candidate_id=candidate.id,
        resume_text=payload.resume_text,
        job_title=job.title,
        job_description=job.description,
        required_skills=job.required_skills or [],
        candidate_name=payload.name,
        candidate_email=payload.email,
        job_id=job.id,
    )

    # Persist every stage that actually ran.
    screening = final_state["screening"]
    db.add(ScreeningResult(candidate_id=candidate.id, **screening))

    if "interview" in final_state:
        db.add(Interview(
            candidate_id=candidate.id,
            scheduled_time=final_state["interview"]["scheduled_time"],
            status=final_state["interview"]["status"],
        ))

    if "prescreen" in final_state:
        # Prescreen results attach to the Interview row created above.
        interview_row = db.query(Interview).filter(Interview.candidate_id == candidate.id).first()
        if interview_row:
            interview_row.transcript = final_state["prescreen"]["transcript"]
            interview_row.signals = final_state["prescreen"]["signals"]
            interview_row.status = "completed"

    if "assessment" in final_state:
        db.add(Assessment(candidate_id=candidate.id, **final_state["assessment"]))

    decision_out = None
    if "decision" in final_state:
        db.add(Decision(candidate_id=candidate.id, **final_state["decision"]))
        decision_out = final_state["decision"]

    candidate.stage = _map_stage(final_state["stage"])
    db.commit()

    return PipelineRunResponse(
        candidate_id=candidate.id,
        final_stage=final_state["stage"],
        screening=screening,
        decision=decision_out,
        trace=final_state["trace"],
    )


def _map_stage(stage: str) -> PipelineStage:
    mapping = {
        "rejected": PipelineStage.REJECTED,
        "reject": PipelineStage.REJECTED,
        "hire": PipelineStage.HIRED,
        "advance": PipelineStage.DECISION,
        "screening": PipelineStage.SCREENING,
        "scheduling": PipelineStage.SCHEDULING,
        "prescreen": PipelineStage.PRESCREEN,
        "assessment": PipelineStage.ASSESSMENT,
    }
    return mapping.get(stage, PipelineStage.SCREENING)
