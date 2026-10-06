"""Tool img2img: variar una imagen existente con denoise controlado."""

import random

from .. import comfy_client, gpu_arbiter, workflow
from ..config import (
    DEFAULT_NEGATIVE,
    GENERATE_TIMEOUT,
    PRESETS,
)
from .generate import resolve_preset
from .view import image_lines, thumbnails


async def img2img(
    image_filename: str,
    prompt: str = "",
    negative_prompt: str | None = None,
    preset: str = "realista",
    denoise: float = 0.55,
    seed: int | None = None,
    checkpoint: str | None = None,
    lora: str | None = None,
    lora_strength: float | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    filename_prefix: str = "mcp-i2i",
    preview: bool = False,
) -> str | list:
    """Variar una imagen existente en el output de ComfyUI usando img2img.
    image_filename: nombre del archivo ya generado (ej: test_00001_.png).
    denoise: 0.0 = imagen idéntica, 1.0 = imagen completamente nueva. 0.3-0.7 recomendado.
    Si prompt está vacío, usa solo el prompt negativo base (variación pura visual)."""
    wake_err = await gpu_arbiter.ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"

    if preset not in PRESETS:
        return f"Preset desconocido: '{preset}'. Válidos: {list(PRESETS.keys())}"
    seed = seed if seed is not None else random.randint(0, 2**48)
    params = resolve_preset(preset, checkpoint, lora, lora_strength, steps, cfg)
    denoise = max(0.0, min(1.0, float(denoise)))
    # Si no hay prompt, usar uno neutro que no distorsione
    if not prompt:
        prompt = "high quality, detailed, sharp focus"

    try:
        wf = workflow.build_img2img(
            prompt=prompt, negative=negative_prompt or DEFAULT_NEGATIVE,
            # LoadImage resuelve el sufijo " [output]" contra output/ de ComfyUI
            image_path=f"{image_filename} [output]", denoise=denoise,
            seed=seed, filename_prefix=filename_prefix, preview=preview, **params,
        )
        prompt_id = await comfy_client.submit_prompt(wf)
        entry = await comfy_client.wait_for_result(prompt_id, GENERATE_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        return f"Error en img2img: {type(e).__name__}: {e}"

    lines = image_lines(entry)
    header = (
        f"{len(lines)} imagen(es) generada(s) · img2img · base={image_filename} · "
        f"denoise={denoise} · seed={seed} · {params['checkpoint']} · {params['steps']} steps:"
    )
    text = "\n".join([header, *lines])
    return [text, *await thumbnails(entry)] if preview else text
