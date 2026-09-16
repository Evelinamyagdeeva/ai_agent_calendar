from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
    )

    polza_ai_base_url: str = "https://polza.ai/api/v1"
    polza_ai_api_key: str = ""
    polza_ai_model_name: str = "deepseek/deepseek-v4.1-flash"

    telegram_bot_token: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_credentials_path: str = "credentials.json"
    google_token_path: str = "data/google_token.json"

    database_url: str = "sqlite:///./data/app.db"
    host: str = "127.0.0.1"
    port: int = 8000
    frontend_origin: str = "http://127.0.0.1:5173"


settings = Settings()
data_dir = ROOT / "data"
data_dir.mkdir(exist_ok=True)
