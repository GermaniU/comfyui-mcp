"""Tool generate_video: clips cortos con Wan 2.2 (txt2video o img2video)."""

import random

from .. import comfy_client, gpu_arbiter, workflow
from ..config import (
    A14B_ASPECTS,
    A14B_FPS,
    A14B_TIMEOUT,
    VIDEO_ASPECTS,
    VIDEO_DRAFT_MAX_SECONDS,
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
    draft: bool = False,
    preview: bool = False,
    model: str = "auto",
) -> str | list:
    if model not in ("auto", "a14b", "5b"):
        return "Modelo desconocido: elige auto, a14b o 5b"
    selected = ("a14b" if image_filename else "5b") if model == "auto" else model
    if selected == "a14b":
        if not image_filename:
            return "A14B I2V requiere image_filename; usa model='5b' para txt2video"
        if draft:
            return "A14B ya usa 480p; draft no está disponible. Usa draft=False"
        if steps is not None and steps != 4:
            return "A14B lightx2v requiere steps=4; omite steps o usa model='5b'"
        if cfg is not None and cfg != 1.0:
            return "A14B lightx2v requiere cfg=1; omite cfg o usa model='5b'"
    sizes = A14B_ASPECTS if selected == "a14b" else VIDEO_ASPECTS
    if aspect not in sizes:
        return f"Aspect desconocido para {selected}: '{aspect}'. Válidos: {list(sizes.keys())}"
    width, height = sizes[aspect]
    try:
        seconds = min(max(int(seconds), 1), VIDEO_MAX_SECONDS)
        if selected == "5b" and draft:
            seconds = min(seconds, VIDEO_DRAFT_MAX_SECONDS)
        if seed is not None and (not isinstance(seed, int) or not 0 <= seed < 2**64):
            return "seed debe ser un entero entre 0 y 2^64-1"
        if selected == "5b":
            params = {
                **VIDEO_MODEL,
                "steps": int(steps if steps is not None else VIDEO_MODEL["steps"]),
                "cfg": float(cfg if cfg is not None else VIDEO_MODEL["cfg"]),
            }
        else:
            params = {"steps": 4}
    except (TypeError, ValueError) as e:
        return f"Parámetros de video inválidos: {e}"
    fps = A14B_FPS if selected == "a14b" else VIDEO_FPS
    length = seconds * fps + 1  # ambos fps son múltiplos de 4
    seed = seed if seed is not None else random.randint(0, 2**48)
    wake_err = await gpu_arbiter.ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"

    try:
        if selected == "a14b":
            wf = workflow.build_a14b_video(
                prompt, negative_prompt if negative_prompt is not None else VIDEO_NEGATIVE,
                f"{image_filename} [output]", width, height, length, seed,
                filename_prefix, preview,
            )
        else:
            wf = workflow.build_video(
                prompt=prompt, negative=negative_prompt or VIDEO_NEGATIVE,
                width=width, height=height, length=length, fps=fps, seed=seed,
                filename_prefix=filename_prefix,
                image_path=f"{image_filename} [output]" if image_filename else None,
                preview=preview, **params,
            )
        prompt_id = await comfy_client.submit_prompt(wf)
        entry = await comfy_client.wait_for_result(
            prompt_id, A14B_TIMEOUT if selected == "a14b" else VIDEO_TIMEOUT)
    except Exception as e:  # noqa: BLE001
        detail = f"{type(e).__name__}: {e}"
        if selected == "a14b" and any(node in detail for node in (
            "UnetLoaderGGUF", "LoraLoaderModelOnly", "CLIPLoader", "VAELoader",
        )):
            detail += (" — verifica ComfyUI-GGUF instalado y los GGUF high/low en models/unet/, "
                       "LoRA high/low en models/loras/, umt5 en models/text_encoders/ "
                       "y wan_2.1_vae en models/vae/; consulta docs/SERVER_SETUP.md")
        return f"Error generando video: {detail}"

    lines = image_lines(entry)
    base = f"img2video base={image_filename}" if image_filename else "txt2video"
    if draft:
        base += " (borrador)"
    header = (
        f"{len(lines)} video(s) generado(s) · {base} · {selected.upper()} · seed {seed} · {width}x{height} · "
        f"{seconds}s ({length} frames a {fps}fps) · {params['steps']} steps:"
    )
    text = "\n".join([header, *lines])
    return [text, *await thumbnails(entry)] if preview else text
