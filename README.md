# comfyui-mcp

MCP HTTP/SSE server que wrappea ComfyUI para generación de imágenes SDXL.

Corre en Pop!_OS junto con ComfyUI (puerto 8188). Expone herramientas vía HTTP/SSE en el puerto 8201 — cualquier gateway de la LAN lo consume sin instalar nada localmente.

## Tools

| Tool | Descripción |
|------|-------------|
| `generate_image` | txt2img con presets (producto/realista/rapido/anime) o params manuales |
| `list_models` | Lista checkpoints, loras y samplers disponibles |
| `comfy_health` | Estado de ComfyUI: versión, VRAM libre/total, cola |
| `comfy_view_url` | URL LAN de descarga directa para una imagen ya generada |

## Presets

| Preset | Checkpoint | Uso |
|--------|-----------|-----|
| `producto` | RealVisXL_V4.0 | Fotorrealista marketing |
| `realista` | juggernautXL_ragnarokBy | Versátil (default) |
| `rapido` | juggernautXL + 6 steps | Borradores ~5s |
| `anime` | animagine-xl-3.1 | Ilustración (checkpoint no migrado) |

## Configuración

| Env var | Default | Descripción |
|---------|---------|-------------|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | URL de ComfyUI (loopback) |
| `COMFYUI_PUBLIC_URL` | `http://192.168.68.108:8188` | URL LAN para descarga directa |
| `MCP_PORT` | `8201` | Puerto del MCP server |
| `MCP_HOST` | `0.0.0.0` | Host binding |

## Estructura

```
src/comfyui_mcp/
├── config.py          # env vars, presets, aspects
├── comfy_client.py    # HTTP client thin a ComfyUI
├── gpu_arbiter.py     # ensure_comfyui_running + wake
├── workflow.py        # build_workflow (txt2img + img2img)
├── tools/             # generate_image, list_models, comfy_health, comfy_view_url
└── server.py          # FastMCP + entry point
tests/                 # pytest por módulo
```

## GPU Broker

El MCP usa el [GPU Broker](../stack/gpu-broker/) para coordinar el uso de la GPU con llama-server. Antes de generar, asegura que ComfyUI tenga VRAM disponible. Ver `gpu-broker.sh` para detalles.

## Instalación

```bash
# venv
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# tests
pytest

# systemd
sudo cp comfyui-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now comfyui-mcp.service
```

## Uso

```bash
# Health check
curl -X POST http://localhost:8201/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```
