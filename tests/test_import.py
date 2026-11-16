"""Scaffold smoke: package, settings, and CLI app are importable."""

from typer.main import get_command

from spotify_pipeline import __version__
from spotify_pipeline.cli import app
from spotify_pipeline.config import (
    SPOTIFY_API_BASE,
    SPOTIFY_TOKEN_URL,
    Settings,
    get_settings,
)


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_defaults() -> None:
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.reccobeats_batch_size == 40
    assert settings.spotify_batch_size == 50
    assert settings.bronze_dir.as_posix().endswith("bronze")


def test_spotify_endpoint_constants() -> None:
    assert SPOTIFY_TOKEN_URL == "https://accounts.spotify.com/api/token"
    assert SPOTIFY_API_BASE == "https://api.spotify.com/v1"


def test_cli_app_has_expected_commands() -> None:
    command = get_command(app)
    names = set(command.commands)
    expected = {
        "run",
        "ingest-charts",
        "enrich-spotify",
        "enrich-reccobeats",
        "build-silver",
        "build-gold",
        "backfill-features",
    }
    assert expected <= names
