"""Demo grabable: el agente genera una imagen real vía MCP y obtiene su URL.

Habla MCP de verdad contra un server comfyui-mcp en modo HTTP. Genera una imagen
con el preset "rapido" (SDXL-Lightning) y resuelve la URL de descarga con
comfy_view_url. Es la fuente de docs/assets/demo.gif.

Requiere un server comfyui-mcp escuchando (por defecto http://localhost:8299/mcp)
con COMFYUI_URL apuntando a un ComfyUI real.

Uso:
    MCP_DEMO_URL=http://localhost:8299/mcp python scripts/demo_generate.py
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time

from fastmcp import Client

URL = os.environ.get("MCP_DEMO_URL", "http://localhost:8299/mcp")
PROMPT = "a ceramic coffee cup on a walnut desk, soft window light, product photo"


def out(text: str = "") -> None:
    print(text, flush=True)


def beat(seconds: float = 0.6) -> None:
    time.sleep(seconds)


def payload(result):
    """Extrae el contenido útil de un CallToolResult."""
    if result.structured_content is not None:
        sc = result.structured_content
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    raw = result.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


async def main() -> int:
    out()
    out("  \033[1mComfyUI MCP\033[0m — el agente genera una imagen en la RTX 3060")
    out("  \033[2m──────────────────────────────────────────────────────────\033[0m")
    beat()
    async with Client(URL) as c:
        out("  \033[2magent →\033[0m generate_image  { preset: \"rapido\" }")
        beat()
        res = payload(await c.call_tool("generate_image", {
            "prompt": PROMPT,
            "preset": "rapido",
            "aspect": "1:1",
        }))
        text = res if isinstance(res, str) else json.dumps(res, ensure_ascii=False)
        out("  \033[2mserver ←\033[0m " + text.strip()[:280].replace("\n", "\n             "))
        match = re.search(r"([\w\-]+\.png)", text)
        if not match:
            out("  \033[1;31mno pude extraer el filename de la respuesta\033[0m")
            return 1
        filename = match.group(1)
        beat()
        out(f"  \033[2magent →\033[0m comfy_view_url  {{ filename: \"{filename}\" }}")
        beat()
        url = payload(await c.call_tool("comfy_view_url", {"filename": filename}))
        out("  \033[2mserver ←\033[0m " + str(url).strip())
    out()
    out("  \033[1;32m✓ imagen generada en la GPU del server — el cliente no instaló PyTorch\033[0m")
    out()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
