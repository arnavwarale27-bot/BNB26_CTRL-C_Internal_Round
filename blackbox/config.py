import os
from typing import Optional


def load_env_file(filepath: str = ".env"):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key not in os.environ:
                os.environ[key] = val


# Load .env upon module import
load_env_file()


class Settings:
    @property
    def api_url(self) -> str:
        return os.getenv("BLACKBOX_API_URL", "http://127.0.0.1:8000")

    @property
    def db_path(self) -> str:
        return os.getenv("BLACKBOX_DB_PATH", "blackbox.db")

    @property
    def host(self) -> str:
        return os.getenv("BLACKBOX_HOST", "0.0.0.0")

    @property
    def port(self) -> int:
        return int(os.getenv("BLACKBOX_PORT", "8000"))

    @property
    def log_level(self) -> str:
        return os.getenv("BLACKBOX_LOG_LEVEL", "INFO")

    @property
    def openai_api_key(self) -> Optional[str]:
        return os.getenv("OPENAI_API_KEY")

    @property
    def openai_base_url(self) -> str:
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


settings = Settings()
