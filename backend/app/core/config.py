from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PRICE_ID: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    POSTGRES_USER: str = "lfc_user"
    POSTGRES_PASSWORD: str = "lfc_pass"
    POSTGRES_DB: str = "lfc_monitor"
    DATABASE_URL: str = "postgresql+asyncpg://lfc_user:lfc_pass@db:5432/lfc_monitor"
    VITE_API_URL: str = "http://localhost:8000"
    REDIRECT_URI: str = "http://localhost:5173/auth/callback"
    FRONTEND_URL: str = "http://localhost:5173"  # Default to local frontend

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
