import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app(version="test-commit")
    app.config["TESTING"] = True
    return app.test_client()


def test_health_contract(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.json == {"status": "ok"}


def test_who_is_plain_text(client):
    response = client.get("/who")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"
    assert response.get_data(as_text=True) == "Thomas Soubirou-Pouey"


def test_home_links_to_the_api(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for route in ("/health", "/who", "/version"):
        assert f'href="{route}"' in html
    assert "Thomas Soubirou-Pouey" in html


def test_version_identifies_the_release(client):
    assert client.get("/version").json == {"version": "test-commit"}


def test_version_comes_from_environment(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "abc123")
    assert create_app().test_client().get("/version").json == {"version": "abc123"}


def test_version_is_escaped_in_html():
    response = create_app(version="<script>alert(1)</script>").test_client().get("/")
    html = response.get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


@pytest.mark.parametrize("route", ["/", "/health", "/who", "/version"])
def test_read_only_routes_reject_post(client, route):
    assert client.post(route).status_code == 405


def test_unknown_route_is_not_a_success(client):
    assert client.get("/inconnue").status_code == 404


def test_head_has_no_body(client):
    response = client.head("/health")
    assert response.status_code == 200
    assert response.data == b""
