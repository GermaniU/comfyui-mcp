"""Tool generate_image: txt2img con presets o params manuales."""

import random

from .. import comfy_client, gpu_arbiter, workflow
from ..config import (ASPECTS, DEFAULT_NEGATIVE, GENERATE_TIMEOUT, PRESETS,
                      COMFY_PUBLIC_URL)


def _view_url(filename: str, subfolder: str, img_type: str) -> str:
    return (f"{COMFY_PUBLIC_URL}/view?filename={filename}"
            f"&subfolder={subfolder}&type={img_type}")


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
    wake_err = await gpu_arbiter.ensure_comfyui_running()
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
        wf = workflow.build_txt2img(
            prompt, negative, checkpoint, width, height, steps, cfg,
            p["sampler"], p["scheduler"], seed, batch,
            lora, lora_strength, filename_prefix, detail_face=detail_face,
        )
        prompt_id = await comfy_client.submit_prompt(wf)
        entry = await comfy_client.wait_for_result(prompt_id, GENERATE_TIMEOUT)
    except Exception as e:
        return f"Error generando imagen: {type(e).__name__}: {e}"

    files = []
    for node_out in entry.get("outputs", {}).values():
        for img in node_out.get("images", []):
            sub = img.get("subfolder", "")
            files.append({"filename": img["filename"], "subfolder": sub,
                          "type": img.get("type", "output")})

    if not files:
        return f"Terminó sin imágenes en la salida (prompt_id {prompt_id}) — revisar workflow."

    lines = [f"{len(files)} imagen(es) generada(s) · seed {seed} · {checkpoint} · "
             f"{width}x{height} · {steps} steps:"]
    for f in files:
        lines.append(f"  · {f['filename']} → {_view_url(f['filename'], f['subfolder'], f['type'])}")
    return "\n".join(lines)
