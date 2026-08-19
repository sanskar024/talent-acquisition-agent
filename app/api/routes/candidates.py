from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.candidate import Candidate
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("/search")
def semantic_search(query: str, top_k: int = 5):
    """
    Semantic search across every previously-screened candidate's resume,
    using the FAISS index — e.g. `?query=backend engineer with Kubernetes
    and distributed systems experience` finds the closest matches
    regardless of which job they originally applied to.
    """
    results = get_vector_store().search(query, top_k=top_k)
    return [{"candidate": meta, "score": score} for meta, score in results]


@router.get("/{candidate_id}")
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "stage": candidate.stage,
        "screening": candidate.screening_result,
        "interview": candidate.interview,
        "assessment": candidate.assessment,
        "decision": candidate.decision,
    }


@router.get("/by-job/{job_id}")
def list_candidates_for_job(job_id: int, db: Session = Depends(get_db)) -> List[dict]:
    candidates = db.query(Candidate).filter(Candidate.job_id == job_id).all()
    return [{"id": c.id, "name": c.name, "stage": c.stage} for c in candidates]
