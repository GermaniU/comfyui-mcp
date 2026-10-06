"""Tests de tools: URLs de vista y resolución de presets."""

import httpx

from comfyui_mcp import comfy_client, gpu_arbiter
from comfyui_mcp.config import COMFY_PUBLIC_URL
from comfyui_mcp.tools import img2img as img2img_tool
from comfyui_mcp.tools.generate import generate_image, resolve_preset
from comfyui_mcp.tools.view import comfy_view_url


def test_view_url_usa_public_url():
    url = comfy_view_url("img.png", "sub", "output")
    assert url.startswith(COMFY_PUBLIC_URL)
    assert "filename=img.png" in url
    assert "subfolder=sub" in url


def test_view_url_codifica_el_filename():
    url = comfy_view_url("mi foto & co_00001_.png")
    assert "filename=mi+foto+%26+co_00001_.png" in url


def test_rapido_usa_la_fuerza_de_lora_del_preset():
    params = resolve_preset("rapido", None, None, None, None, None)
    assert params["lora"] == "sdxl-lightning-4step.safetensors"
    assert params["lora_strength"] == 1.0


def test_params_explicitos_pisan_al_preset():
    params = resolve_preset("rapido", "otro.safetensors", None, 0.5, 8, 2.0)
    assert params["checkpoint"] == "otro.safetensors"
    assert params["lora_strength"] == 0.5
    assert (params["steps"], params["cfg"]) == (8, 2.0)


async def _capturar_workflow(monkeypatch, tool, **kw):
    enviado = {}

    async def despierto():
        return None

    async def submit(wf):
        enviado.update(wf)
        return "pid"

    async def result(prompt_id, timeout):
        return {"outputs": {"9": {"images": [{"filename": "x_00001_.png"}]}}}

    monkeypatch.setattr(gpu_arbiter, "ensure_comfyui_running", despierto)
    monkeypatch.setattr(comfy_client, "submit_prompt", submit)
    monkeypatch.setattr(comfy_client, "wait_for_result", result)
    salida = await tool(**kw)
    return enviado, salida


async def test_generate_rapido_lleva_lora_a_fuerza_completa(monkeypatch):
    wf, salida = await _capturar_workflow(
        monkeypatch, generate_image, prompt="a cat", preset="rapido")
    assert wf["10"]["inputs"]["strength_model"] == 1.0
    assert "x_00001_.png" in salida


async def test_img2img_carga_desde_output(monkeypatch):
    wf, _ = await _capturar_workflow(
        monkeypatch, img2img_tool.img2img, image_filename="base_00001_.png")
    assert wf["12"]["inputs"]["image"] == "base_00001_.png [output]"


async def test_timeout_saca_el_prompt_de_la_cola(monkeypatch):
    posts = []

    def handler(request):
        if request.method == "POST":
            posts.append(request.url.path)
        return httpx.Response(200, json={})

    monkeypatch.setattr(comfy_client, "_client", lambda timeout=None: httpx.AsyncClient(
        base_url="http://comfy", transport=httpx.MockTransport(handler)))
    try:
        await comfy_client.wait_for_result("pid", timeout=0)
    except TimeoutError:
        pass
    else:
        raise AssertionError("debió vencer")
    assert posts == ["/queue", "/interrupt"]
