from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://deploydock:deploydock@localhost:5432/deploydock"
    GITHUB_WEBHOOK_SECRET: str = "changeme"
    SECRET_KEY: str = "changeme-secret-key"
    DOCKER_HOST: str | None = None
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    APP_NAME: str = "DeployDock"
    REPOS_BASE_PATH: str = "/app/repos"
    HEALTH_CHECK_TIMEOUT: int = 30
    HEALTH_CHECK_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
