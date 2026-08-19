from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM (Google Gemini)
    gemini_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"
    use_mock_llm: bool = True

    # DB
    database_url: str = "postgresql://talentflow:talentflow@localhost:5432/talentflow"

    # Integration mocks
    use_mock_calendar: bool = True
    use_mock_email: bool = True

    # FAISS vector store (candidate semantic search)
    faiss_index_path: str = "data/candidates.index"

    # Thresholds
    resume_pass_threshold: float = 0.62
    assessment_pass_threshold: float = 0.70

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
