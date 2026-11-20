from datetime import date

import pytest

from spotify_pipeline import api


class Connection:
    def __init__(self, rows=(), dates=(date(2026, 11, 12),)):
        self.rows = rows
        self.dates = dates
        self.closed = False
        self.calls = []

    def run(self, sql, **params):
        self.calls.append((sql, params))
        if "DISTINCT chart_date" in sql:
            return [(day,) for day in self.dates]
        if "LEFT JOIN" in sql:
            return self.rows
        return []

    def close(self):
        self.closed = True


@pytest.fixture
def client():
    app = api.create_app()
    app.testing = True
    return app.test_client()


def test_health_without_database(client):
    assert client.get('/api/health').json['status'] == 'ok'


@pytest.mark.parametrize('week', ['nope', '2026-02-30', '20261112', "2026-11-12' OR 1=1"])
def test_invalid_week(client, week, monkeypatch):
    monkeypatch.setattr(api, 'connect_postgres', lambda: pytest.fail('must validate before DB'))
    assert client.get('/api/charts', query_string={'week': week}).status_code == 400


def test_chart_preserves_missing_features_and_collaborating_artists(client, monkeypatch):
    members = [{'id': 'a', 'name': 'A'}, {'id': 'b', 'name': 'B'}]
    conn = Connection([
        ('one', 'One', 1, None, False, .9, .8, .7, 100, members),
        ('two', 'Two', 2, 3, True, .0, .8, None, 100, members[:1]),
    ])
    monkeypatch.setattr(api, 'connect_postgres', lambda: conn)
    response = client.get('/api/charts')
    assert response.status_code == 200
    data = response.json
    assert data['week'] == '2026-11-12'
    assert len(data['tracks']) == 2
    assert data['tracks'][0]['energy'] is None
    assert data['tracks'][0]['featuresFound'] is False
    assert data['tracks'][0]['previousRank'] is None
    assert data['tracks'][1]['energy'] == 0
    assert data['artists'] == [
        {'artist': 'A', 'tracks': 2, 'bestRank': 1},
        {'artist': 'B', 'tracks': 1, 'bestRank': 1},
    ]
    assert 'READ ONLY' in conn.calls[0][0]
    assert conn.calls[-1][1] == {'week': '2026-11-12'}
    assert conn.closed


def test_empty_database(client, monkeypatch):
    conn = Connection(dates=())
    monkeypatch.setattr(api, 'connect_postgres', lambda: conn)
    assert client.get('/api/charts').json == {'week': None, 'weeks': [], 'tracks': [], 'artists': []}
    assert conn.closed


def test_unavailable_week(client, monkeypatch):
    conn = Connection()
    monkeypatch.setattr(api, 'connect_postgres', lambda: conn)
    assert client.get('/api/charts?week=2026-11-05').status_code == 404
    assert conn.closed


def test_database_error_does_not_leak_details(client, monkeypatch):
    def fail(_):
        raise RuntimeError('secret database password')
    monkeypatch.setattr(api, 'read_chart', fail)
    response = client.get('/api/charts')
    assert response.status_code == 503
    assert b'secret' not in response.data


def test_query_failure_closes_connection(client, monkeypatch):
    conn = Connection()

    def fail_query(*args, **kwargs):
        raise RuntimeError("private connection details")

    monkeypatch.setattr(conn, "run", fail_query)
    monkeypatch.setattr(api, "connect_postgres", lambda: conn)
    response = client.get("/api/charts")
    assert response.status_code == 503
    assert b"private connection details" not in response.data
    assert conn.closed


def test_selected_week_is_bound_to_query(client, monkeypatch):
    conn = Connection(dates=(date(2026, 11, 12), date(2026, 11, 5)))
    monkeypatch.setattr(api, "connect_postgres", lambda: conn)
    response = client.get("/api/charts?week=2026-11-05")
    assert response.status_code == 200
    assert response.json["week"] == "2026-11-05"
    assert conn.calls[-1][1] == {"week": "2026-11-05"}
    assert conn.closed
