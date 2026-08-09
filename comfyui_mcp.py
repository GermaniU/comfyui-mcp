#!/usr/bin/env python3
"""
MCP HTTP/SSE server para generación de imágenes con ComfyUI (RTX 3060, Pop!_OS).

Corre EN Pop!_OS junto con ComfyUI (a diferencia del diseño original WSL/stdio):
cualquier gateway Hermes de la LAN (Mac mini, MacBook Air, la propia Pop!_OS) lo
consume vía HTTP en el puerto 8201, sin instalar nada localmente — mismo patrón
que vault_rw.py / agentplatform_admin.py.

Tools expuestas:
  generate_image   txt2img con preset (producto/realista/rapido/anime) o params manuales
  list_models      checkpoints y loras que ComfyUI tiene disponibles
  comfy_health     estado del server ComfyUI: versión, VRAM libre/total, cola

GPU arbiter: usa el GPU Broker (~/stack/gpu-broker/gpu-broker.sh) para
coordinar el uso de la GPU con llama-server. El broker para llama-server
gracefully si está idle, libera VRAM, y lo re-arranca al terminar.
También puede arrancar comfyui.service si no está corriendo.

Configuración:
  COMFYUI_URL         default http://127.0.0.1:8188 (loopback, corre en la misma máquina)
  COMFYUI_OUTPUT_DIR  default ~/stack/comfyui/output (las imágenes quedan EN Pop!_OS;
                       el caller recibe filename+subfolder y puede pedirlas por /view
                       de ComfyUI directo, o vía un futuro endpoint de descarga)
  MCP_PORT            default 8201
  MCP_HOST            default 0.0.0.0
"""
import asyncio
import os
import random
import subprocess
import sys
import time
from typing import Any

import httpx
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import uvicorn

COMFY_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_SERVICE = "comfyui.service"
GPU_BROKER = os.path.expanduser("~/stack/gpu-broker/gpu-broker.sh")
_WAKE_TIMEOUT_S = 90
_WAKE_POLL_S = 2

DEFAULT_TIMEOUT = 15.0
GENERATE_TIMEOUT = 600.0  # primera carga de un checkpoint SDXL (6.5GB) + sampling

DEFAULT_NEGATIVE = (
    "low quality, worst quality, blurry, jpeg artifacts, watermark, text, "
    "logo, signature, deformed, bad anatomy, extra fingers"
)

# Presets: checkpoint + sampler tuning. "rapido" usa SDXL-Lightning (4-8 steps).
# "anime" requiere animagine-xl-3.1.safetensors — NO migrado (fuera de scope
# FlowOrdr/OrdenaAhora), fallará con error claro de ComfyUI si se usa.
PRESETS: dict[str, dict[str, Any]] = {
    "producto": {
        "checkpoint": "RealVisXL_V4.0.safetensors",
        "steps": 30, "cfg": 5.5, "sampler": "dpmpp_2m", "scheduler": "karras",
        "descripcion": "fotorrealista para fotos de producto/marketing",
    },
    "realista": {
        "checkpoint": "juggernautXL_ragnarokBy.safetensors",
        "steps": 30, "cfg": 5.0, "sampler": "dpmpp_2m", "scheduler": "karras",
        "descripcion": "fotorrealista versátil (escenas, personas, ambientes)",
    },
    "rapido": {
        "checkpoint": "juggernautXL_ragnarokBy.safetensors",
        "lora": "sdxl-lightning-4step.safetensors", "lora_strength": 1.0,
        "steps": 6, "cfg": 1.5, "sampler": "euler", "scheduler": "sgm_uniform",
        "descripcion": "borradores en ~5s con SDXL-Lightning (menor calidad)",
    },
    "anime": {
        "checkpoint": "animagine-xl-3.1.safetensors",
        "steps": 28, "cfg": 7.0, "sampler": "euler_ancestral", "scheduler": "normal",
        "descripcion": "ilustración estilo anime (checkpoint NO migrado — fallará)",
    },
}

# Resoluciones SDXL-friendly (~1MP, múltiplos de 8) por aspect ratio.
ASPECTS = {
    "1:1": (1024, 1024),
    "4:5": (896, 1120),
    "5:4": (1120, 896),
    "9:16": (768, 1344),
    "16:9": (1344, 768),
    "3:2": (1216, 832),
    "2:3": (832, 1216),
}

mcp = FastMCP("comfyui-image")


# ─── GPU arbiter (local, corre en la misma máquina que comfyui.service) ──

async def _comfyui_reachable() -> bool:
    try:
        async with httpx.AsyncClient(base_url=COMFY_URL, timeout=3.0) as c:
            r = await c.get("/system_stats")
            return r.status_code == 200
    except Exception:
        return False


async def ensure_comfyui_running() -> str | None:
    """Si ComfyUI no responde, arranca comfyui.service. El GPU Broker
    (configurado en ExecStartPre del systemd service) se encarga de parar
    llama-server gracefully si está idle. Devuelve None si OK, o error."""
    if await _comfyui_reachable():
        return None
    # Arrancar comfyui.service — el ExecStartPre del drop-in llama al broker
    subprocess.run(["systemctl", "start", COMFYUI_SERVICE],
                   capture_output=True, text=True)
    deadline = time.time() + _WAKE_TIMEOUT_S
    while time.time() < deadline:
        if await _comfyui_reachable():
            return None
        await asyncio.sleep(_WAKE_POLL_S)
    return f"{COMFYUI_SERVICE} no respondió tras {_WAKE_TIMEOUT_S}s de arrancarlo."


# ─── Helpers ─────────────────────────────────────────────────────────────

def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=COMFY_URL, timeout=timeout)


def _build_workflow(
    prompt: str, negative: str, checkpoint: str, width: int, height: int,
    steps: int, cfg: float, sampler: str, scheduler: str, seed: int,
    batch: int, lora: str | None, lora_strength: float, filename_prefix: str,
    detail_face: bool = False,
) -> dict:
    """Workflow txt2img en formato API de ComfyUI. Con lora opcional entre
    el checkpoint y el sampler (model + clip)."""
    wf: dict[str, Any] = {
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": checkpoint}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": batch}},
    }
    model_ref, clip_ref = ["4", 0], ["4", 1]
    if lora:
        wf["10"] = {"class_type": "LoraLoader", "inputs": {
            "lora_name": lora, "strength_model": lora_strength,
            "strength_clip": lora_strength, "model": ["4", 0], "clip": ["4", 1]}}
        model_ref, clip_ref = ["10", 0], ["10", 1]
    wf.update({
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": clip_ref}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative, "clip": clip_ref}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler, "denoise": 1.0,
            "model": model_ref, "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}},
    })
    if detail_face:
        wf["11"] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref,
            "text": "professional portrait photography, sharp detailed realistic eyes, "
                    "natural symmetric eyes, detailed iris and pupil, natural catchlights, skin texture"}}
        wf["12"] = {"class_type": "CLIPTextEncode", "inputs": {
            "clip": clip_ref,
            "text": "crossed eyes, lazy eye, asymmetric eyes, blurry eyes, deformed iris, "
                    "extra pupils, glassy doll eyes, low quality, worst quality"}}
        wf["13"] = {"class_type": "UltralyticsDetectorProvider",
                    "inputs": {"model_name": "bbox/face_yolov8m.pt"}}
        wf["14"] = {"class_type": "FaceDetailer", "inputs": {
            "image": ["8", 0], "model": model_ref, "clip": clip_ref, "vae": ["4", 2],
            "guide_size": 768, "guide_size_for": True, "max_size": 1024,
            "seed": seed, "steps": 24, "cfg": 5.0,
            "sampler_name": sampler, "scheduler": scheduler,
            "positive": ["11", 0], "negative": ["12", 0],
            "denoise": 0.45, "feather": 5, "noise_mask": True, "force_inpaint": True,
            "bbox_threshold": 0.5, "bbox_dilation": 10, "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1", "sam_dilation": 0, "sam_threshold": 0.93,
            "sam_bbox_expansion": 0, "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False", "drop_size": 10,
            "bbox_detector": ["13", 0], "wildcard": "", "cycle": 1}}
        wf["9"]["inputs"]["images"] = ["14", 0]
    return wf


async def _wait_for_result(prompt_id: str, timeout: float) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    async with _client(timeout=30.0) as c:
        while asyncio.get_event_loop().time() < deadline:
            r = await c.get(f"/history/{prompt_id}")
            r.raise_for_status()
            data = r.json()
            if prompt_id in data:
                entry = data[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    msgs = [m for m in status.get("messages", [])
                            if m[0] == "execution_error"]
                    detail = msgs[0][1].get("exception_message") if msgs else "?"
                    raise RuntimeError(f"ComfyUI reportó error: {detail}")
                if entry.get("outputs"):
                    return entry
            await asyncio.sleep(2.0)
    raise TimeoutError(f"la generación no terminó en {int(timeout)}s")


# ─── Tools ───────────────────────────────────────────────────────────────

@mcp.tool(
    name="generate_image",
    description=(
        "Genera imágenes en la RTX 3060 (SDXL vía ComfyUI). Presets: producto "
        "(fotorrealista marketing), realista (versátil), rapido (borradores ~5s), "
        "anime (checkpoint no disponible). Devuelve filename+subfolder en Pop!_OS "
        "(pedir con comfy_view_url para la URL directa de descarga). La primera "
        "generación con un checkpoint tarda ~1 min extra por carga del modelo, más "
        "~10-30s si hay que despertar el servicio (switch de GPU con el LLM). "
        "Prompt en inglés funciona mejor."
    ),
)
async def generate_image(
    prompt: str,
    preset: str = "producto",
    aspect: str = "1:1",
    negative_prompt: str | None = None,
    seed: int | None = None,
    batch: int = 1,
    checkpoint: str | None = None,
    lora: str | None = None,
    lora_strength: float = 0.8,
    steps: int | None = None,
    cfg: float | None = None,
    filename_prefix: str = "mcp",
    detail_face: bool = False,
) -> str:
    wake_err = await ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"

    if preset not in PRESETS:
        return f"Preset desconocido: '{preset}'. Válidos: {list(PRESETS.keys())}"
    p = PRESETS[preset]
    if aspect not in ASPECTS:
        return f"Aspect desconocido: '{aspect}'. Válidos: {list(ASPECTS.keys())}"
    width, height = ASPECTS[aspect]
    seed = seed if seed is not None else random.randint(0, 2**48)
    batch = min(max(int(batch), 1), 4)
    checkpoint = checkpoint or p["checkpoint"]
    lora = lora or p.get("lora")
    lora_strength = float(lora_strength if lora else p.get("lora_strength", 0.8))
    steps = int(steps if steps is not None else p["steps"])
    cfg = float(cfg if cfg is not None else p["cfg"])
    negative = negative_prompt or DEFAULT_NEGATIVE

    try:
        wf = _build_workflow(
            prompt, negative, checkpoint, width, height, steps, cfg,
            p["sampler"], p["scheduler"], seed, batch,
            lora, lora_strength, filename_prefix, detail_face=detail_face,
        )
        async with _client() as c:
            r = await c.post("/prompt", json={"prompt": wf})
            if r.status_code != 200:
                return f"ComfyUI rechazó el workflow (HTTP {r.status_code}): {r.text[:500]}"
            prompt_id = r.json()["prompt_id"]

        entry = await _wait_for_result(prompt_id, GENERATE_TIMEOUT)
    except Exception as e:
        return f"Error generando imagen: {type(e).__name__}: {e}"

    files = []
    for node_out in entry.get("outputs", {}).values():
        for img in node_out.get("images", []):
            sub = img.get("subfolder", "")
            files.append({"filename": img["filename"], "subfolder": sub, "type": img.get("type", "output")})

    if not files:
        return f"Terminó sin imágenes en la salida (prompt_id {prompt_id}) — revisar workflow."

    lines = [f"{len(files)} imagen(es) generada(s) · seed {seed} · {checkpoint} · "
             f"{width}x{height} · {steps} steps:"]
    for f in files:
        view_url = f"{COMFY_URL}/view?filename={f['filename']}&subfolder={f['subfolder']}&type={f['type']}"
        lines.append(f"  · {f['filename']} → {view_url}")
    return "\n".join(lines)


@mcp.tool(
    name="list_models",
    description="Lista checkpoints, loras y samplers disponibles en ComfyUI.",
)
async def list_models() -> str:
    wake_err = await ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"
    async with _client() as c:
        r = await c.get("/object_info/CheckpointLoaderSimple")
        r.raise_for_status()
        ckpts = r.json()["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        r = await c.get("/object_info/LoraLoader")
        r.raise_for_status()
        loras = r.json()["LoraLoader"]["input"]["required"]["lora_name"][0]
    lines = ["Checkpoints:"] + [f"  · {c}" for c in ckpts]
    lines += ["Loras:"] + [f"  · {l}" for l in loras]
    lines += ["Presets:"] + [f"  · {k}: {v['descripcion']} ({v['checkpoint']})"
                             for k, v in PRESETS.items()]
    return "\n".join(lines)


@mcp.tool(
    name="comfy_health",
    description="Estado de ComfyUI: si responde, VRAM libre/total de la GPU y tamaño de la cola.",
)
async def comfy_health() -> str:
    if not await _comfyui_reachable():
        return "ComfyUI no disponible (inactivo). Usar generate_image para arrancarlo."
    async with _client() as c:
        r = await c.get("/system_stats")
        r.raise_for_status()
        stats = r.json()
        r = await c.get("/queue")
        r.raise_for_status()
        queue = r.json()
    dev = stats["devices"][0]
    vram_free = dev["vram_free"] / 1024**3
    vram_total = dev["vram_total"] / 1024**3
    pending = len(queue.get("queue_pending", []))
    running = len(queue.get("queue_running", []))
    return (
        f"ComfyUI OK ({stats['system']['comfyui_version']}) · {dev['name']} · "
        f"VRAM {vram_free:.1f}/{vram_total:.1f} GB libres · "
        f"cola: {running} corriendo, {pending} pendientes"
    )


# ─── Entry point ──────────────────────────────────────────────────────────

def main():
    use_stdio = "--stdio" in sys.argv or os.getenv("MCP_TRANSPORT") == "stdio"
    port = int(os.getenv("MCP_PORT", "8201"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    if use_stdio:
        mcp.run(transport="stdio")
    else:
        app = mcp.http_app(stateless_http=True)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
