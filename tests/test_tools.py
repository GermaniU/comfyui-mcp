"""Tests de tools: URLs de vista y validación de presets/aspects."""

import pytest

from comfyui_mcp.config import COMFY_PUBLIC_URL
from comfyui_mcp.tools.generate import _view_url
from comfyui_mcp.tools.view import comfy_view_url


def test_view_url_usa_public_url():
    url = _view_url("img.png", "", "output")
    assert COMFY_PUBLIC_URL in url
    assert "filename=img.png" in url


@pytest.mark.asyncio
async def test_comfy_view_url():
    url = await comfy_view_url("img.png", "sub", "output")
    assert "filename=img.png" in url
    assert "subfolder=sub" in url
