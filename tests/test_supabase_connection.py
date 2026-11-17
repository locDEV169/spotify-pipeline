"""Unit tests for Supabase client factory (no live network)."""

from unittest.mock import MagicMock, patch

import pytest

from spotify_pipeline.config import Settings
from spotify_pipeline.db.connection import SupabaseConfigError, get_supabase_client


def test_get_supabase_client_requires_url_and_key() -> None:
    settings = Settings(supabase_url="", supabase_service_role_key="")
    with pytest.raises(SupabaseConfigError, match="SUPABASE_URL"):
        get_supabase_client(settings)


def test_get_supabase_client_calls_create_client() -> None:
    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role-test-key",
    )
    fake = MagicMock(name="Client")
    with patch(
        "spotify_pipeline.db.connection.create_client",
        return_value=fake,
    ) as mocked:
        client = get_supabase_client(settings)
    assert client is fake
    mocked.assert_called_once_with(
        "https://example.supabase.co",
        "service-role-test-key",
    )
