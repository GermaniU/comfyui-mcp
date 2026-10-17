"""FastMCP server + entry point (stdio/HTTP)."""

import hmac
import os
import sys

import uvicorn
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .tools.generate import generate_image
from .tools.health import comfy_health
from .tools.img2img import img2img
from .tools.models import list_models
from .tools.video import generate_video
from .tools.view import comfy_view_url

mcp = FastMCP("comfyui-image")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = os.getenv("MCP_AUTH_TOKEN")
        if token:
            header = request.headers.get("authorization", "")
            if not hmac.compare_digest(header.encode(), f"Bearer {token}".encode()):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


@mcp.tool(
    name="generate_image",
    description=(
        "Genera imágenes en la RTX 3060 (SDXL vía ComfyUI). Presets: producto "
        "(fotorrealista marketing), realista (versátil), rapido (borradores ~5s), "
        "anime (checkpoint no disponible). Devuelve filename+subfolder en Pop!_OS "
        "(pedir con comfy_view_url para la URL directa de descarga). La primera "
        "generación con un checkpoint tarda ~1 min extra por carga del modelo, más "
        "~10-30s si hay que despertar el servicio (switch de GPU con el LLM). "
        "Prompt en inglés funciona mejor. preview=true devuelve además una "
        "miniatura JPEG (~512px) para ver el resultado; solo en clientes con visión."
    ),
    output_schema=None,
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
    lora_strength: float | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    filename_prefix: str = "mcp",
    detail_face: bool = False,
    preview: bool = False,
) -> str | list:
    return await generate_image(
        prompt=prompt, preset=preset, aspect=aspect,
        negative_prompt=negative_prompt, seed=seed, batch=batch,
        checkpoint=checkpoint, lora=lora, lora_strength=lora_strength,
        steps=steps, cfg=cfg, filename_prefix=filename_prefix,
        detail_face=detail_face, preview=preview,
    )


@mcp.tool(
    name="list_models",
    description=(
        "Lista checkpoints, loras y presets disponibles en ComfyUI. Si ComfyUI "
        "está dormido devuelve solo los presets, sin despertarlo."
    ),
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
    description="Devuelve la URL LAN de descarga directa para una imagen o video ya generado (por filename).",
)
async def _comfy_view_url(filename: str, subfolder: str = "", img_type: str = "output") -> str:
    return comfy_view_url(filename, subfolder, img_type)


@mcp.tool(
    name="img2img",
    description=(
        "Varía una imagen ya generada usando img2img. Pasar image_filename (ej: "
        "test_00001_.png) y denoise (0.0=idéntica, 1.0=completamente nueva, "
        "0.3-0.7 recomendado). Si prompt está vacío, hace variación visual pura. "
        "Útil para iterar un arte sin partir de cero o generar variaciones de memes. "
        "preview=true devuelve además una miniatura JPEG; solo en clientes con visión."
    ),
    output_schema=None,
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
    lora_strength: float | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    filename_prefix: str = "mcp-i2i",
    preview: bool = False,
) -> str | list:
    return await img2img(
        image_filename=image_filename, prompt=prompt,
        negative_prompt=negative_prompt, preset=preset, denoise=denoise,
        seed=seed, checkpoint=checkpoint, lora=lora, lora_strength=lora_strength,
        steps=steps, cfg=cfg, filename_prefix=filename_prefix, preview=preview,
    )


@mcp.tool(
    name="generate_video",
    description=(
        "Genera un clip corto (1-5s, 24fps, MP4) con Wan 2.2 en la RTX 3060. Sin "
        "image_filename es txt2video; con image_filename (una imagen ya generada, "
        "ej: mcp_00001_.png) la anima usándola como primer frame — conviene que su "
        "aspect coincida con el del video. aspect: 16:9, 9:16 o 1:1. Tarda varios "
        "minutos (más la primera vez por carga del modelo); describir la escena y el "
        "movimiento de cámara en inglés. draft=true genera a ~480p, bastante más "
        "rápido: útil para probar el prompt antes de la versión final. Devuelve "
        "filename + URL de descarga. "
        "preview=true devuelve además una miniatura JPEG del primer frame."
    ),
    output_schema=None,
)
async def _generate_video(
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
) -> str | list:
    return await generate_video(
        prompt=prompt, aspect=aspect, seconds=seconds,
        image_filename=image_filename, negative_prompt=negative_prompt,
        seed=seed, steps=steps, cfg=cfg, filename_prefix=filename_prefix,
        draft=draft, preview=preview,
    )


def main():
    use_stdio = "--stdio" in sys.argv or os.getenv("MCP_TRANSPORT") == "stdio"
    port = int(os.getenv("MCP_PORT", "8201"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    if use_stdio:
        mcp.run(transport="stdio")
    else:
        app = mcp.http_app(stateless_http=True)
        app.add_middleware(BearerAuthMiddleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=os.getenv("MCP_CORS_ORIGINS", "*").split(","),
            allow_methods=["*"],
            allow_headers=["*"],
        )
        uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
