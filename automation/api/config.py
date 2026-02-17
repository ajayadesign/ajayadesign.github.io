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
    gh_token: str = Field(default="", description="GitHub PAT for repo management")
    github_org: str = Field(default="ajayadesign")

    # AI — multi-provider support ("github-models" or "anthropic")
    ai_provider: str = Field(
        default="github-models",
        description="AI provider: 'github-models' (OpenAI via Azure) or 'anthropic' (Claude)",
    )
    ai_token: str = Field(default="", description="GitHub PAT for AI models (falls back to GH_TOKEN)")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude models")
    ai_api_url: str = Field(
        default="",
        description="Override AI API URL (auto-set per provider if blank)",
    )
    ai_model: str = Field(default="")

    @property
    def ai_effective_url(self) -> str:
        """Resolve API URL based on provider."""
        if self.ai_api_url:
            return self.ai_api_url
        if self.ai_provider == "anthropic":
            return "https://api.anthropic.com/v1/messages"
        return "https://models.inference.ai.azure.com/chat/completions"

    @property
    def ai_effective_model(self) -> str:
        """Resolve model name based on provider."""
        if self.ai_model:
            return self.ai_model
        if self.ai_provider == "anthropic":
            return "claude-sonnet-4-20250514"
        return "gpt-4o"

    @property
    def ai_auth_token(self) -> str:
        """Token for AI API calls — provider-specific."""
        if self.ai_provider == "anthropic":
            return self.anthropic_api_key
        return self.ai_token or self.gh_token

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

    # Email / SMTP (Gmail)
    smtp_email: str = Field(default="", description="Gmail address for sending emails")
    smtp_app_password: str = Field(default="", description="Gmail App Password (16 chars, no spaces)")

    # Host ownership fix (Docker → host)
    host_uid: int = Field(default=1000)
    host_gid: int = Field(default=1000)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
