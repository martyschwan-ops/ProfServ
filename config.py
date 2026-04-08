from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to the project root (the directory containing this file)
BASE_DIR = Path(__file__).parent.resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")

    # Paths (resolved to absolute at startup via properties)
    data_dir: Path = BASE_DIR / "data"
    receipts_dir: Path = BASE_DIR / "receipts"
    workbook_name: str = "expenses.xlsx"

    # AI extraction provider
    extraction_provider: str = "mock"  # mock | anthropic | openai
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # FX provider
    fx_provider: str = "frankfurter"

    # Per-diem amounts (CAD)
    breakfast_amount: float = 20.0
    lunch_amount: float = 25.0
    dinner_amount: float = 45.0
    base_currency: str = "CAD"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def workbook_path(self) -> Path:
        return self.data_dir / self.workbook_name

    @property
    def fx_cache_file(self) -> Path:
        return self.data_dir / "fx_cache.json"

    @property
    def templates_dir(self) -> Path:
        return BASE_DIR / "app" / "templates"

    @property
    def static_dir(self) -> Path:
        return BASE_DIR / "app" / "static"


settings = Settings()
