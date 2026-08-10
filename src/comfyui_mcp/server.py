"""FastMCP server + entry point (stdio/HTTP)."""

import os
import sys

from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from .tools.generate import generate_image
from .tools.health import comfy_health
from .tools.img2img import img2img
from .tools.models import list_models
from .tools.view import comfy_view_url

mcp = FastMCP("comfyui-image")


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
async def _generate_image(
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
    return await generate_image(
        prompt=prompt, preset=preset, aspect=aspect,
        negative_prompt=negative_prompt, seed=seed, batch=batch,
        checkpoint=checkpoint, lora=lora, lora_strength=lora_strength,
        steps=steps, cfg=cfg, filename_prefix=filename_prefix,
        detail_face=detail_face,
    )


@mcp.tool(
    name="list_models",
    description="Lista checkpoints, loras y samplers disponibles en ComfyUI.",
)
async def _list_models() -> str:
    return await list_models()


@mcp.tool(
    name="comfy_health",
    description="Estado de ComfyUI: si responde, VRAM libre/total de la GPU y tamaño de la cola.",
)
async def _comfy_health() -> str:
    return await comfy_health()


@mcp.tool(
    name="comfy_view_url",
    description="Devuelve la URL LAN de descarga directa para una imagen ya generada (por filename).",
)
async def _comfy_view_url(filename: str, subfolder: str = "", img_type: str = "output") -> str:
    return await comfy_view_url(filename, subfolder, img_type)


@mcp.tool(
    name="img2img",
    description=(
        "Varía una imagen ya generada usando img2img. Pasar image_filename (ej: "
        "test_00001_.png) y denoise (0.0=idéntica, 1.0=completamente nueva, "
        "0.3-0.7 recomendado). Si prompt está vacío, hace variación visual pura. "
        "Útil para iterar un arte sin partir de cero o generar variaciones de memes."
    ),
)
async def _img2img(
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
    return await img2img(
        image_filename=image_filename, prompt=prompt,
        negative_prompt=negative_prompt, preset=preset, denoise=denoise,
        seed=seed, checkpoint=checkpoint, lora=lora, lora_strength=lora_strength,
        steps=steps, cfg=cfg, filename_prefix=filename_prefix,
    )


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
