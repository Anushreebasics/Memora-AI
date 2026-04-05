from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "llama-3.1-8b-instant"
    openai_base_url: str = "https://api.groq.com/openai/v1"

    data_dir: str = "./data"
    chroma_dir: str = "./data/chroma"
    sqlite_path: str = "./data/assistant.db"
    upload_dir: str = "./data/uploads"

    embedding_model: str = "all-MiniLM-L6-v2"
    top_k: int = 3
    max_chunk_chars: int = 1200
    chunk_overlap_chars: int = 180

    # Hallucination guard
    confidence_threshold: float = 0.45
    allow_low_confidence_answers: bool = False

    # Insights generation
    insights_window_days: int = 7


settings = Settings()
