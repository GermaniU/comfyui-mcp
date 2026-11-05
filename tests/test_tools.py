"""Tests de tools: URLs de vista y resolución de presets."""

import httpx
from fastmcp import Client

from comfyui_mcp import comfy_client, gpu_arbiter
from comfyui_mcp.config import COMFY_PUBLIC_URL
from comfyui_mcp.server import mcp
from comfyui_mcp.tools import img2img as img2img_tool
from comfyui_mcp.tools.generate import generate_image, resolve_preset
from comfyui_mcp.tools.models import list_models
from comfyui_mcp.tools.video import generate_video
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
    expected_timeout = kw.pop("_expected_timeout", None)

    async def despierto():
        return None

    async def submit(wf):
        enviado.update(wf)
        return "pid"

    async def result(prompt_id, timeout):
        if expected_timeout is not None:
            enviado["_timeout"] = timeout
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
    if expected_timeout is not None:
        assert enviado.pop("_timeout", None) == expected_timeout
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


async def test_video_frames_segun_segundos(monkeypatch):
    wf, salida = await _capturar_workflow(
        monkeypatch, generate_video, prompt="a cat", seconds=9)
    assert wf["7"]["inputs"]["length"] == 121, "se recorta a 5s (5*24+1 frames)"
    assert "LoadImage" not in [n["class_type"] for n in wf.values()]
    assert "txt2video" in salida


async def test_video_anima_imagen_desde_output(monkeypatch):
    wf, salida = await _capturar_workflow(
        monkeypatch, generate_video, prompt="a cat", aspect="9:16",
        image_filename="base_00001_.png", model="5b")
    assert wf["12"]["inputs"]["image"] == "base_00001_.png [output]"
    assert (wf["7"]["inputs"]["width"], wf["7"]["inputs"]["height"]) == (704, 1280)
    assert "img2video base=base_00001_.png" in salida


async def test_video_minimo_un_segundo_y_params_explicitos(monkeypatch):
    wf, salida = await _capturar_workflow(
        monkeypatch, generate_video, prompt="a cat", seconds=0, steps=8, cfg=3.0, seed=7)
    assert wf["7"]["inputs"]["length"] == 25
    ks = wf["8"]["inputs"]
    assert (ks["steps"], ks["cfg"], ks["seed"]) == (8, 3.0, 7)
    assert "seed 7" in salida and "8 steps" in salida


async def test_video_preview_por_mcp(monkeypatch):
    async def call(**kw):
        async with Client(mcp) as c:
            return await c.call_tool("generate_video", kw)

    wf, r = await _capturar_workflow(monkeypatch, call, prompt="a cat", preview=True)
    assert wf["11"]["class_type"] == "SaveVideo"
    assert [b.type for b in r.content] == ["text", "image"]
    assert "x_00001_.png" in r.content[0].text


async def test_video_borrador_mantiene_resolucion_y_recorta_duracion(monkeypatch):
    wf, salida = await _capturar_workflow(
        monkeypatch, generate_video, prompt="a cat", aspect="9:16", seconds=5, draft=True)
    assert (wf["7"]["inputs"]["width"], wf["7"]["inputs"]["height"]) == (704, 1280)
    assert wf["7"]["inputs"]["length"] == 49
    assert "(borrador)" in salida and "704x1280" in salida and "2s (49 frames" in salida

async def test_video_5b_timeout_y_preset_por_mcp(monkeypatch):
    async def call(**kw):
        async with Client(mcp) as c:
            return await c.call_tool("generate_video", kw)

    wf, result = await _capturar_workflow(
        monkeypatch, call, prompt="a cat", seconds=5, _expected_timeout=3000.0)
    assert wf["7"]["inputs"]["length"] == 121
    assert wf["10"]["inputs"]["fps"] == 24
    assert wf["8"]["inputs"]["steps"] == 30
    assert wf["1"]["inputs"]["weight_dtype"] == "fp8_e4m3fn"
    assert "5B" in result.content[0].text


async def test_video_aspect_invalido(monkeypatch):
    _, salida = await _capturar_workflow(
        monkeypatch, generate_video, prompt="a cat", aspect="4:5")
    assert salida.startswith("Aspect desconocido")


async def test_video_a14b_auto_y_frames_por_segundos(monkeypatch):
    wf, salida = await _capturar_workflow(
        monkeypatch, generate_video, prompt="motion", negative_prompt="no blur",
        image_filename="base.png", aspect="9:16", seconds=3, seed=42)
    assert wf["7"]["inputs"]["length"] == 49
    assert (wf["7"]["inputs"]["width"], wf["7"]["inputs"]["height"]) == (480, 832)
    assert wf["6"]["inputs"]["text"] == "no blur"
    assert wf["8a"]["inputs"]["noise_seed"] == 42
    assert wf["12"]["inputs"]["image"] == "base.png [output]"
    assert "A14B" in salida and "16fps" in salida


async def test_video_a14b_cinco_segundos_y_horizontal(monkeypatch):
    wf, _ = await _capturar_workflow(
        monkeypatch, generate_video, prompt="motion", image_filename="base.png", seconds=5)
    assert (wf["7"]["inputs"]["width"], wf["7"]["inputs"]["height"],
            wf["7"]["inputs"]["length"]) == (832, 480, 81)


async def test_video_a14b_rechaza_incompatibles_antes_de_despertar(monkeypatch):
    async def no_wake():
        raise AssertionError("no debe encender GPU")
    monkeypatch.setattr(gpu_arbiter, "ensure_comfyui_running", no_wake)
    for kw, expected in (
        ({"model": "a14b"}, "image_filename"),
        ({"model": "a14b", "image_filename": "base.png", "aspect": "1:1"}, "16:9"),
        ({"model": "a14b", "image_filename": "base.png", "steps": 8}, "steps=4"),
        ({"model": "a14b", "image_filename": "base.png", "cfg": 3.0}, "cfg=1"),
        ({"model": "a14b", "image_filename": "base.png", "draft": True}, "draft"),
        ({"model": "unknown"}, "Modelo desconocido"),
    ):
        result = await generate_video(prompt="motion", **kw)
        assert expected in result


async def test_video_a14b_selector_mcp(monkeypatch):
    async def call(**kw):
        async with Client(mcp) as c:
            return await c.call_tool("generate_video", kw)

    wf, result = await _capturar_workflow(
        monkeypatch, call, prompt="motion", image_filename="base.png",
        model="a14b", preview=True)
    assert wf["8a"]["class_type"] == "KSamplerAdvanced"
    assert [block.type for block in result.content] == ["text", "image"]
    assert "A14B" in result.content[0].text


async def test_video_a14b_timeout_y_error_dependencias(monkeypatch):
    async def despierto():
        return None
    async def submit(wf):
        raise RuntimeError("ComfyUI rechazó el workflow: UnetLoaderGGUF: Node not found")
    monkeypatch.setattr(gpu_arbiter, "ensure_comfyui_running", despierto)
    monkeypatch.setattr(comfy_client, "submit_prompt", submit)
    result = await generate_video(prompt="motion", image_filename="base.png")
    assert "ComfyUI-GGUF" in result

    async def submitted(wf):
        return "pid"
    async def wait(prompt_id, timeout):
        assert timeout >= 900
        return {"outputs": {"11": {"videos": []}}}
    monkeypatch.setattr(comfy_client, "submit_prompt", submitted)
    monkeypatch.setattr(comfy_client, "wait_for_result", wait)
    await generate_video(prompt="motion", image_filename="base.png")


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
