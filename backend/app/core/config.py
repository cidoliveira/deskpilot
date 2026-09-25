from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
API_V1_PREFIX = "/api/v1"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings, read from environment variables (and the .env file if present).

    Secrets use `SecretStr`, so they are masked if the settings object is ever logged.
    """

    # Locally the .env lives at the repository root; in Docker the variables come from Compose.
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    app_name: str = "DeskPilot API"
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str = "deskpilot"
    postgres_test_db: str = "deskpilot_test"

    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1)

    # Optional: when set, `python -m app.scripts.create_admin` creates this admin account.
    first_admin_email: EmailStr | None = None
    first_admin_password: SecretStr | None = None
    first_admin_name: str = "Administrator"

    # Optional: password of the demo accounts created by `python -m app.scripts.seed_demo`.
    demo_password: SecretStr | None = None

    def _postgres_url(self, database: str) -> URL:
        # URL.create escapes special characters in the password, unlike string formatting.
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=database,
        )

    @property
    def database_url(self) -> URL:
        return self._postgres_url(self.postgres_db)

    @property
    def test_database_url(self) -> URL:
        return self._postgres_url(self.postgres_test_db)

    @property
    def maintenance_database_url(self) -> URL:
        """Default `postgres` database, used only to create the test database."""
        return self._postgres_url("postgres")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # required fields come from the environment
