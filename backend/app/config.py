from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads the repo-root .env (shared with docker compose) and backend/.env if present.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/finance"
    # SEC requires a User-Agent identifying you, with a contact email.
    sec_user_agent: str = "FinanceApp admin@example.com"
    # How long cached data is considered fresh before it's re-fetched on request.
    fundamentals_ttl_hours: float = 24
    prices_ttl_hours: float = 6
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
