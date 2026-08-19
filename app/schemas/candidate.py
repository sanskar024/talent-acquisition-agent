from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CandidateCreate(BaseModel):
    job_id: int
    resume_text: str
    name: Optional[str] = None
    email: Optional[str] = None


class ScreeningResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    similarity_score: float
    skill_match_score: float
    overall_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    bias_flags: List[str]
    passed: bool


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recommendation: str
    confidence: float
    rationale: str
    bias_warning: Optional[str] = None


class PipelineRunRequest(BaseModel):
    job_id: int
    resume_text: str
    name: Optional[str] = None
    email: Optional[str] = None


class PipelineRunResponse(BaseModel):
    candidate_id: int
    final_stage: str
    screening: ScreeningResultOut
    decision: Optional[DecisionOut] = None
    trace: List[Dict[str, Any]]  # step-by-step log of what each agent did
