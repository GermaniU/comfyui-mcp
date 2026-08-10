# AGENTS.md — comfyui-mcp

MCP HTTP/SSE server que wrappea ComfyUI (SDXL, RTX 3060) para generación de imágenes. Corre en Pop!_OS junto con ComfyUI (puerto 8188) y expone tools vía HTTP en el puerto 8201. Cualquier gateway Hermes de la LAN lo consume sin instalar nada localmente.

## Stack

- Python 3.11+, `fastmcp`, `httpx`, `uvicorn`, `starlette`
- ComfyUI API en `http://127.0.0.1:8188` (loopback, misma máquina)
- GPU Broker (`~/stack/gpu-broker/gpu-broker.sh`) coordina la GPU con llama-server

## Estructura (vertical slice + clean)

```
src/comfyui_mcp/
├── config.py          # env vars, presets, aspects, constantes
├── comfy_client.py    # HTTP client thin a ComfyUI (system_stats, prompt, history, view)
├── gpu_arbiter.py     # ensure_comfyui_running + wake
├── workflow.py        # build_workflow (txt2img + img2img + upscale)
├── tools/             # generate_image, list_models, comfy_health, comfy_view_url, history
│   ├── __init__.py
│   ├── generate.py
│   ├── models.py
│   ├── health.py
│   └── view.py
└── server.py          # FastMCP + entry point (stdio/HTTP)
tests/                 # pytest por módulo
```

## Reglas de estilo (heredadas del AGENTS.md de ComfyUI)

- Cambios chicos y directos. Tocar el camino de código más angosto que explica el problema.
- Cambiar la menor cantidad de archivos posible.
- Preferir fixes prácticos sobre arquitectura amplia. Abstracciones solo cuando quitan lógica repetida real.
- Preferir menos dependencias. No agregar deps a menos que sean necesarias.
- Borrar código obsoleto agresivamente. Sin ramas muertas, sin funciones nunca llamadas.
- Preservar APIs existentes, nombres de nodos, layout de archivos y compatibilidad de workflows.
- **El código debe verse hand-written.** Cambios que lean como código genérico de IA serán rechazados: capas helper innecesarias, nombres vagos, comentarios boilerplate, ramas defensivas sin failure mode real, rewrites amplios.

## Tools actuales

| Tool | Descripción |
|------|-------------|
| `generate_image` | txt2img con presets (producto/realista/rapido/anime) o params manuales |
| `list_models` | Checkpoints, loras y samplers disponibles |
| `comfy_health` | Estado de ComfyUI: versión, VRAM, cola |

## Configuración (env vars)

| Env var | Default | Descripción |
|---------|---------|-------------|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | URL de ComfyUI (loopback) |
| `COMFYUI_PUBLIC_URL` | `http://192.168.68.108:8188` | URL LAN para descarga directa de imágenes |
| `MCP_PORT` | `8201` | Puerto del MCP server |
| `MCP_HOST` | `0.0.0.0` | Host binding |

## Deploy

- systemd: `comfyui-mcp.service` (puerto 8201)
- El servicio corre desde `~/stack/comfyui/` (runtime), el repo git desde `~/Sites/comfyui-mcp/` (fuente). Mantener sincronizados.
- GPU Broker en `ExecStartPre` del service para el switch de GPU con llama-server.

## Flujo de trabajo

1. Rama desde `master`: `git checkout master && git pull && git checkout -b feature/...`
2. Implementar siguiendo la estructura de `src/comfyui_mcp/`
3. Tests pytest por módulo
4. Commit con prefijo (`feat:`, `fix:`, `chore:`)
5. PR sin merge
6. Verificar con `pytest` antes de reportar
