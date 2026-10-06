"""Tests de tools: URLs de vista y resolución de presets."""

import httpx
from fastmcp import Client

from comfyui_mcp import comfy_client, gpu_arbiter
from comfyui_mcp.config import COMFY_PUBLIC_URL
from comfyui_mcp.server import mcp
from comfyui_mcp.tools import img2img as img2img_tool
from comfyui_mcp.tools.generate import generate_image, resolve_preset
from comfyui_mcp.tools.models import list_models
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
        return {"outputs": {
            "9": {"images": [{"filename": "x_00001_.png", "subfolder": "", "type": "output"}]},
            "16": {"images": [{"filename": "p_00001_.png", "subfolder": "", "type": "temp"}]},
        }}

    async def jpeg(filename, subfolder, img_type):
        assert img_type == "temp"
        return b"\xff\xd8\xff"

    monkeypatch.setattr(gpu_arbiter, "ensure_comfyui_running", despierto)
    monkeypatch.setattr(comfy_client, "submit_prompt", submit)
    monkeypatch.setattr(comfy_client, "wait_for_result", result)
    monkeypatch.setattr(comfy_client, "view_jpeg", jpeg)
    salida = await tool(**kw)
    return enviado, salida


async def test_generate_rapido_lleva_lora_a_fuerza_completa(monkeypatch):
    wf, salida = await _capturar_workflow(
        monkeypatch, generate_image, prompt="a cat", preset="rapido")
    assert wf["10"]["inputs"]["strength_model"] == 1.0
    assert "x_00001_.png" in salida
    assert "p_00001_.png" not in salida, "la miniatura de temp/ no es descargable"


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


async def test_rechazo_nombra_nodo_y_valores_validos(monkeypatch):
    cuerpo = {
        "error": {"type": "prompt_outputs_failed_validation",
                  "message": "Prompt outputs failed validation"},
        "node_errors": {"4": {"class_type": "CheckpointLoaderSimple", "errors": [{
            "type": "value_not_in_list", "message": "Value not in list",
            "details": "ckpt_name: 'anime.safetensors' not in ['real.safetensors']"}]}},
    }
    monkeypatch.setattr(comfy_client, "_client", lambda timeout=None: httpx.AsyncClient(
        base_url="http://comfy",
        transport=httpx.MockTransport(lambda r: httpx.Response(400, json=cuerpo))))
    try:
        await comfy_client.submit_prompt({})
    except RuntimeError as e:
        msg = str(e)
    assert "CheckpointLoaderSimple: Value not in list" in msg
    assert "not in ['real.safetensors']" in msg


async def test_list_models_no_despierta_comfyui(monkeypatch):
    async def dormido():
        return False

    async def no_despertar():
        raise AssertionError("list_models no debe arrancar ComfyUI")

    monkeypatch.setattr(comfy_client, "reachable", dormido)
    monkeypatch.setattr(gpu_arbiter, "ensure_comfyui_running", no_despertar)
    salida = await list_models()
    assert "rapido" in salida
    assert "ComfyUI dormido" in salida


async def test_preview_devuelve_texto_y_miniatura_por_mcp(monkeypatch):
    async def call(**kw):
        async with Client(mcp) as c:
            return await c.call_tool("generate_image", kw)

    wf, r = await _capturar_workflow(monkeypatch, call, prompt="a cat", preview=True)
    assert wf["16"]["class_type"] == "PreviewImage"
    assert [b.type for b in r.content] == ["text", "image"]
    assert r.content[1].mimeType == "image/jpeg"
