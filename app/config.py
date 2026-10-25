"""Application settings, read from environment variables (and an optional .env file)."""
import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.split("#")[0].strip())


_load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DEV_SECRET = "dev-only-insecure-secret-key-change-me-before-deploying"


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./homefind.db")
    secret_key: str = os.getenv("SECRET_KEY", DEV_SECRET)
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7)))
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:8443,http://localhost:5173").split(",")
            if o.strip()
        ]
    )
    seed_on_startup: bool = _bool("SEED_ON_STARTUP", True)
    # Illustrative rates, in percent. Swap for a real provider in production.
    rates: dict[str, float] = field(
        default_factory=lambda: {
            "30-year fixed": float(os.getenv("RATE_30Y_FIXED", "6.38")),
            "15-year fixed": float(os.getenv("RATE_15Y_FIXED", "5.62")),
            "5/1 ARM": float(os.getenv("RATE_5_1_ARM", "5.95")),
            "FHA 30-year fixed": float(os.getenv("RATE_FHA_30Y", "6.10")),
        }
    )
    jwt_algorithm: str = "HS256"


settings = Settings()
