"""Tests para el middleware de autenticación por Bearer Token."""

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from comfyui_mcp.server import BearerAuthMiddleware


async def dummy_endpoint(request):
    return PlainTextResponse("OK")


@pytest.fixture
def auth_app():
    app = Starlette(routes=[Route("/test", dummy_endpoint)])
    app.add_middleware(BearerAuthMiddleware)
    return app


def test_auth_disabled_by_default(auth_app, monkeypatch):
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    client = TestClient(auth_app)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.text == "OK"


def test_auth_enabled_unauthorized(auth_app, monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "secret123")
    client = TestClient(auth_app)
    
    # Sin header Authorization
    res1 = client.get("/test")
    assert res1.status_code == 401
    assert res1.json() == {"error": "unauthorized"}

    # Con token incorrecto
    res2 = client.get("/test", headers={"Authorization": "Bearer wrong"})
    assert res2.status_code == 401


def test_auth_enabled_authorized(auth_app, monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "secret123")
    client = TestClient(auth_app)
    
    res = client.get("/test", headers={"Authorization": "Bearer secret123"})
    assert res.status_code == 200
    assert res.text == "OK"
