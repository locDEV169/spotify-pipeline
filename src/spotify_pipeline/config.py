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
SPOTIFY_AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
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

    # Authorization Code flow (only needed for /v1/me/* endpoints).
    # Must match EXACTLY one Redirect URI in the Spotify Dashboard (use 127.0.0.1, not localhost).
    spotify_redirect_uri: str = "http://127.0.0.1:5000/callback"
    # Filled once by scripts/spotify_login.py; never commit.
    spotify_refresh_token: str = ""

    # Supabase (SPEC append "Lưu trữ bằng Supabase") — server/scripts only.
    # Prefer SERVICE_ROLE for pipeline; never ship this key to a browser/FE bundle.
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    # Optional direct Postgres URL (psycopg) — not required for create_client().
    supabase_db_url: str = ""

    data_dir: Path = Path("data")
    bronze_dir: Path = Path("data/bronze")
    silver_dir: Path = Path("data/silver")
    gold_dir: Path = Path("data/gold")

    spotify_batch_size: int = 50
    reccobeats_batch_size: int = 40


def get_settings() -> Settings:
    return Settings()
