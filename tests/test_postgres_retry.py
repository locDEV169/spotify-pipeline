"""Unit tests for prepare/bind mismatch retry helper (no live DB)."""

from __future__ import annotations

import pytest

from spotify_pipeline.db import postgres as pg


class _Boom(Exception):
    pass


def test_is_prepare_bind_mismatch() -> None:
    assert pg.is_prepare_bind_mismatch(
        Exception(
            "{'C': '08P01', 'M': 'bind message supplies 5 parameters, "
            "but prepared statement \"\" requires 0'}"
        )
    )
    assert pg.is_prepare_bind_mismatch(
        Exception(
            "{'C': '26000', 'M': 'unnamed prepared statement does not exist'}"
        )
    )
    assert not pg.is_prepare_bind_mismatch(Exception("other error"))


def test_call_with_db_retry_reconnects_once_on_26000(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0, "reconnects": 0}
    conn1 = object()
    conn2 = object()

    def fake_reconnect(db_url: str, old_conn=None):
        calls["reconnects"] += 1
        return conn2

    monkeypatch.setattr(pg, "reconnect_postgres", fake_reconnect)

    def write_fn(conn) -> None:
        calls["n"] += 1
        if calls["n"] == 1:
            assert conn is conn1
            raise _Boom(
                "{'C': '26000', 'M': 'unnamed prepared statement does not exist'}"
            )
        assert conn is conn2

    out = pg.call_with_db_retry("postgresql://x:6543/postgres", conn1, write_fn)
    assert out is conn2
    assert calls["n"] == 2
    assert calls["reconnects"] == 1


def test_call_with_db_retry_raises_hint_when_retry_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pg, "reconnect_postgres", lambda db_url, old_conn=None: object())

    def write_fn(conn) -> None:
        raise _Boom(
            "{'C': '26000', 'M': 'unnamed prepared statement does not exist'}"
        )

    with pytest.raises(pg.PostgresConfigError, match="5432"):
        pg.call_with_db_retry("postgresql://x:6543/postgres", object(), write_fn)
