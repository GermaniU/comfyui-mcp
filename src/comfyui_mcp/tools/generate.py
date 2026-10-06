"""Tool generate_image: txt2img con presets o params manuales."""

import random

from .. import comfy_client, gpu_arbiter, workflow
from ..config import (
    ASPECTS,
    DEFAULT_NEGATIVE,
    GENERATE_TIMEOUT,
    PRESETS,
)
from .view import image_lines


def resolve_preset(preset: str, checkpoint: str | None, lora: str | None,
                   lora_strength: float | None, steps: int | None,
                   cfg: float | None) -> dict:
    """Params de sampling: los explícitos pisan a los del preset."""
    p = PRESETS[preset]
    return {
        "checkpoint": checkpoint or p["checkpoint"],
        "lora": lora or p.get("lora"),
        "lora_strength": float(lora_strength if lora_strength is not None
                               else p.get("lora_strength", 0.8)),
        "steps": int(steps if steps is not None else p["steps"]),
        "cfg": float(cfg if cfg is not None else p["cfg"]),
        "sampler": p["sampler"],
        "scheduler": p["scheduler"],
    }


async def generate_image(
    prompt: str,
    preset: str = "producto",
    aspect: str = "1:1",
    negative_prompt: str | None = None,
    seed: int | None = None,
    batch: int = 1,
    checkpoint: str | None = None,
    lora: str | None = None,
    lora_strength: float | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    filename_prefix: str = "mcp",
    detail_face: bool = False,
) -> str:
    wake_err = await gpu_arbiter.ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"

    if preset not in PRESETS:
        return f"Preset desconocido: '{preset}'. Válidos: {list(PRESETS.keys())}"
    if aspect not in ASPECTS:
        return f"Aspect desconocido: '{aspect}'. Válidos: {list(ASPECTS.keys())}"
    width, height = ASPECTS[aspect]
    seed = seed if seed is not None else random.randint(0, 2**48)
    batch = min(max(int(batch), 1), 4)
    params = resolve_preset(preset, checkpoint, lora, lora_strength, steps, cfg)

    try:
        wf = workflow.build_txt2img(
            prompt=prompt, negative=negative_prompt or DEFAULT_NEGATIVE,
            width=width, height=height, seed=seed, batch=batch,
            filename_prefix=filename_prefix, detail_face=detail_face, **params,
        )
        prompt_id = await comfy_client.submit_prompt(wf)
        entry = await comfy_client.wait_for_result(prompt_id, GENERATE_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        return f"Error generando imagen: {type(e).__name__}: {e}"

    lines = image_lines(entry)
    header = (
        f"{len(lines)} imagen(es) generada(s) · seed {seed} · {params['checkpoint']} · "
        f"{width}x{height} · {params['steps']} steps:"
    )
    return "\n".join([header, *lines])
