"""FastMCP server + entry point (stdio/HTTP)."""

import os
import sys

from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from .tools.generate import generate_image
from .tools.health import comfy_health
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
async def _generate_image(**kwargs) -> str:
    return await generate_image(**kwargs)


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
