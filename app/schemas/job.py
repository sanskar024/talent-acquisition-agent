from typing import List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str] = []
    min_experience_years: int = 0


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    required_skills: List[str]
    min_experience_years: int
    created_at: datetime
