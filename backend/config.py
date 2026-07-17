from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "TraceAI Fraud Intelligence API"
    app_version: str = "2.0.0"
    debug: bool = False

    # JWT
    secret_key: str = "CHANGE_THIS_IN_PRODUCTION_USE_256BIT_RANDOM_KEY"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str = "sqlite:///./traceai.db"

    # Security
    max_login_attempts: int = 5
    lockout_minutes: int = 30
    rate_limit_per_minute: int = 60

    # Federated learning
    fl_noise_multiplier: float = 1.1  # differential privacy noise
    fl_share_only_scores: bool = True

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
