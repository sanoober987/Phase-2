import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.database_url: str = self._require("DATABASE_URL")
        self.jwt_secret_key: str = self._require("JWT_SECRET_KEY")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_seconds: int = int(os.getenv("JWT_EXPIRES_IN", "3600"))
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]

        # Groq configuration — single source of truth for the whole app
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.groq_timeout: float = float(os.getenv("GROQ_TIMEOUT", "60"))
        self.groq_max_tokens: int = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
        self.groq_max_input_tokens: int = int(os.getenv("GROQ_MAX_INPUT_TOKENS", "8000"))
        self.groq_max_retries: int = int(os.getenv("GROQ_MAX_RETRIES", "3"))
        self.groq_user_rpm: int = int(os.getenv("GROQ_USER_RPM", "20"))

        # Chat settings
        self.chat_history_depth: int = int(os.getenv("CHAT_HISTORY_DEPTH", "20"))
        self.environment: str = os.getenv("ENVIRONMENT", "development")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @staticmethod
    def _require(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise RuntimeError(
                f"Required environment variable '{key}' is not set. "
                f"Copy backend/.env.example to backend/.env and fill in the values."
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
