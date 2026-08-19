import logging

from fastapi import FastAPI

from app.database import init_db
from app.api.routes import jobs, candidates, pipeline

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="TalentFlow AI",
    description="Autonomous multi-agent talent acquisition system.",
    version="0.1.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(pipeline.router)
