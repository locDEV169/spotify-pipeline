"""C1 — Config / secrets (SPEC). Load Spotify creds, paths, batch sizes."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict  # pyright: ignore[reportMissingImports]

# src/spotify_pipeline/config.py → repo root (so scripts work even if cwd differs)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILES = (
    _REPO_ROOT / ".env",
    Path(".env"),
)

# Fixed Spotify endpoints (SPEC / official docs — not env-overridable)
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"


class Settings(BaseSettings):
    """Local settings. Open ⚠️ product flags (auth/v0, BI, etc.) are intentionally absent."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    data_dir: Path = Path("data")
    bronze_dir: Path = Path("data/bronze")
    silver_dir: Path = Path("data/silver")
    gold_dir: Path = Path("data/gold")

    spotify_batch_size: int = 50
    reccobeats_batch_size: int = 40


def get_settings() -> Settings:
    return Settings()
