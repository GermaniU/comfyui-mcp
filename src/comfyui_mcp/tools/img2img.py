"""Tool img2img: variar una imagen existente con denoise controlado."""

import random

from .. import comfy_client, gpu_arbiter, workflow
from ..config import (ASPECTS, DEFAULT_NEGATIVE, GENERATE_TIMEOUT, PRESETS,
                      COMFY_PUBLIC_URL)


def _view_url(filename: str, subfolder: str, img_type: str) -> str:
    return (f"{COMFY_PUBLIC_URL}/view?filename={filename}"
            f"&subfolder={subfolder}&type={img_type}")


async def img2img(
    image_filename: str,
    prompt: str = "",
    negative_prompt: str | None = None,
    preset: str = "realista",
    denoise: float = 0.55,
    seed: int | None = None,
    checkpoint: str | None = None,
    lora: str | None = None,
    lora_strength: float = 0.8,
    steps: int | None = None,
    cfg: float | None = None,
    filename_prefix: str = "mcp-i2i",
) -> str:
    """Variar una imagen existente en el output de ComfyUI usando img2img.
    image_filename: nombre del archivo ya generado (ej: test_00001_.png).
    denoise: 0.0 = imagen idéntica, 1.0 = imagen completamente nueva. 0.3-0.7 recomendado.
    Si prompt está vacío, usa solo el prompt negativo base (variación pura visual)."""
    wake_err = await gpu_arbiter.ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"

    if preset not in PRESETS:
        return f"Preset desconocido: '{preset}'. Válidos: {list(PRESETS.keys())}"
    p = PRESETS[preset]
    seed = seed if seed is not None else random.randint(0, 2**48)
    checkpoint = checkpoint or p["checkpoint"]
    lora = lora or p.get("lora")
    lora_strength = float(lora_strength if lora else p.get("lora_strength", 0.8))
    steps = int(steps if steps is not None else p["steps"])
    cfg = float(cfg if cfg is not None else p["cfg"])
    denoise = max(0.0, min(1.0, float(denoise)))
    negative = negative_prompt or DEFAULT_NEGATIVE
    # Si no hay prompt, usar uno neutro que no distorsione
    if not prompt:
        prompt = "high quality, detailed, sharp focus"

    try:
        wf = workflow.build_img2img(
            prompt, negative, checkpoint, image_filename,
            denoise, steps, cfg, p["sampler"], p["scheduler"], seed,
            lora, lora_strength, filename_prefix,
        )
        prompt_id = await comfy_client.submit_prompt(wf)
        entry = await comfy_client.wait_for_result(prompt_id, GENERATE_TIMEOUT)
    except Exception as e:
        return f"Error en img2img: {type(e).__name__}: {e}"

    files = []
    for node_out in entry.get("outputs", {}).values():
        for img in node_out.get("images", []):
            sub = img.get("subfolder", "")
            files.append({"filename": img["filename"], "subfolder": sub,
                          "type": img.get("type", "output")})

    if not files:
        return f"Terminó sin imágenes (prompt_id {prompt_id})."

    lines = [f"{len(files)} imagen(es) generada(s) · img2img · base={image_filename} · "
             f"denoise={denoise} · seed={seed} · {checkpoint} · {steps} steps:"]
    for f in files:
        lines.append(f"  · {f['filename']} → {_view_url(f['filename'], f['subfolder'], f['type'])}")
    return "\n".join(lines)