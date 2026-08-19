import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    Float,
    Boolean,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship

from app.database import Base


class PipelineStage(str, enum.Enum):
    SCREENING = "screening"
    SCHEDULING = "scheduling"
    PRESCREEN = "prescreen"
    ASSESSMENT = "assessment"
    DECISION = "decision"
    REJECTED = "rejected"
    HIRED = "hired"


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    resume_text = Column(Text, nullable=False)
    stage = Column(Enum(PipelineStage), default=PipelineStage.SCREENING)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="candidates")
    screening_result = relationship("ScreeningResult", back_populates="candidate", uselist=False)
    interview = relationship("Interview", back_populates="candidate", uselist=False)
    assessment = relationship("Assessment", back_populates="candidate", uselist=False)
    decision = relationship("Decision", back_populates="candidate", uselist=False)


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    similarity_score = Column(Float)          # embedding cosine similarity to JD
    skill_match_score = Column(Float)         # fraction of required skills found
    overall_score = Column(Float)
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    bias_flags = Column(JSON, default=list)   # PII terms redacted before scoring
    passed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="screening_result")


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="pending")  # pending/scheduled/completed/cancelled
    transcript = Column(Text, nullable=True)
    signals = Column(JSON, default=dict)  # e.g. {"communication": 0.8, "confidence": 0.7}
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="interview")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    questions = Column(JSON, default=list)
    answers = Column(JSON, default=list)
    per_question_scores = Column(JSON, default=list)
    overall_score = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="assessment")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    recommendation = Column(String(50))  # "advance" / "reject" / "hire"
    confidence = Column(Float)
    rationale = Column(Text)
    bias_warning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="decision")
