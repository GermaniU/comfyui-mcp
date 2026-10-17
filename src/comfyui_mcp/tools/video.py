"""Tool generate_video: clips cortos con Wan 2.2 (txt2video o img2video)."""

import random

from .. import comfy_client, gpu_arbiter, workflow
from ..config import (
    VIDEO_ASPECTS,
    VIDEO_FPS,
    VIDEO_MAX_SECONDS,
    VIDEO_MODEL,
    VIDEO_NEGATIVE,
    VIDEO_TIMEOUT,
)
from .view import image_lines, thumbnails


async def generate_video(
    prompt: str,
    aspect: str = "16:9",
    seconds: int = 3,
    image_filename: str | None = None,
    negative_prompt: str | None = None,
    seed: int | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    filename_prefix: str = "mcp-video",
    preview: bool = False,
) -> str | list:
    wake_err = await gpu_arbiter.ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"

    if aspect not in VIDEO_ASPECTS:
        return f"Aspect desconocido: '{aspect}'. Válidos: {list(VIDEO_ASPECTS.keys())}"
    width, height = VIDEO_ASPECTS[aspect]
    seconds = min(max(int(seconds), 1), VIDEO_MAX_SECONDS)
    length = seconds * VIDEO_FPS + 1  # Wan pide 4n+1 frames
    seed = seed if seed is not None else random.randint(0, 2**48)
    params = {
        **VIDEO_MODEL,
        "steps": int(steps if steps is not None else VIDEO_MODEL["steps"]),
        "cfg": float(cfg if cfg is not None else VIDEO_MODEL["cfg"]),
    }

    try:
        wf = workflow.build_video(
            prompt=prompt, negative=negative_prompt or VIDEO_NEGATIVE,
            width=width, height=height, length=length, fps=VIDEO_FPS, seed=seed,
            filename_prefix=filename_prefix,
            image_path=f"{image_filename} [output]" if image_filename else None,
            preview=preview, **params,
        )
        prompt_id = await comfy_client.submit_prompt(wf)
        entry = await comfy_client.wait_for_result(prompt_id, VIDEO_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        return f"Error generando video: {type(e).__name__}: {e}"

    lines = image_lines(entry)
    base = f"img2video base={image_filename}" if image_filename else "txt2video"
    header = (
        f"{len(lines)} video(s) generado(s) · {base} · seed {seed} · {width}x{height} · "
        f"{seconds}s ({length} frames a {VIDEO_FPS}fps) · {params['steps']} steps:"
    )
    text = "\n".join([header, *lines])
    return [text, *await thumbnails(entry)] if preview else text
