"""
AjayaDesign Automation — Configuration via environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """All settings read from env / .env file."""

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./ajayadesign.db",
        description="Async SQLAlchemy DB URL",
    )

    # GitHub
    gh_token: str = Field(default="", description="GitHub PAT for API + AI")
    github_org: str = Field(default="ajayadesign")

    # AI
    ai_api_url: str = Field(
        default="https://models.inference.ai.azure.com/chat/completions"
    )
    ai_model: str = Field(default="gpt-4o")

    # Telegram
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")

    # Firebase
    firebase_cred_path: str = Field(
        default="", description="Path to Firebase service account key JSON"
    )
    firebase_db_url: str = Field(
        default="https://ajayadesign-6d739-default-rtdb.firebaseio.com",
        description="Firebase RTDB URL",
    )
    firebase_poll_interval: int = Field(
        default=60, description="Seconds between Firebase polls"
    )

    # Paths
    base_dir: str = Field(default="/workspace/builds")
    main_site_dir: str = Field(default="/workspace/ajayadesign.github.io")

    # Pipeline
    max_council_rounds: int = Field(default=2)
    max_fix_attempts: int = Field(default=3)

    # Image sourcing (optional — graceful no-op without key)
    unsplash_access_key: str = Field(default="", description="Unsplash API access key for stock images")

    # Host ownership fix (Docker → host)
    host_uid: int = Field(default=1000)
    host_gid: int = Field(default=1000)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
