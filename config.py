from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Paths
    data_dir: Path = Path("data")
    receipts_dir: Path = Path("receipts")
    workbook_name: str = "expenses.xlsx"
    fx_cache_file: str = "data/fx_cache.json"

    # AI extraction provider
    extraction_provider: str = "mock"  # mock | anthropic | openai
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # FX provider
    fx_provider: str = "frankfurter"  # frankfurter | manual

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


settings = Settings()
