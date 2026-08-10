# comfyui-mcp

MCP HTTP/SSE server que wrappea ComfyUI para generación de imágenes SDXL.

Corre en Pop!_OS junto con ComfyUI (puerto 8188). Expone herramientas vía HTTP/SSE en el puerto 8201 — cualquier gateway de la LAN lo consume sin instalar nada localmente.

## Tools

| Tool | Descripción |
|------|-------------|
| `generate_image` | txt2img con presets (producto/realista/rapido/anime) o params manuales |
| `list_models` | Lista checkpoints, loras y samplers disponibles |
| `comfy_health` | Estado de ComfyUI: versión, VRAM libre/total, cola |

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
| `COMFYUI_URL` | `http://127.0.0.1:8188` | URL de ComfyUI |
| `MCP_PORT` | `8201` | Puerto del MCP server |
| `MCP_HOST` | `0.0.0.0` | Host binding |

## Coordinación de GPU (opcional)

Si `ComfyUI` no responde, este MCP arranca `comfyui.service` (systemd) y espera a que levante — eso es todo lo que hace este repo respecto a GPU.

Si tu setup corre otros procesos que compiten por VRAM (un LLM local, por ejemplo), puedes liberar VRAM *antes* de que `comfyui.service` arranque agregando un `ExecStartPre=` a tu propia unit de `comfyui.service` que pare esos procesos. Ese mecanismo vive en tu infraestructura, fuera de este repo — no es necesario para usar el MCP.

## Instalación

```bash
# venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# systemd — editar comfyui-mcp.service primero: reemplazar <usuario> y
# /ruta/al/repo por los valores reales de tu máquina
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

⚠️ El servidor escucha en `0.0.0.0` por defecto y no tiene autenticación — pensado para redes internas de confianza. Si lo expones a una red no confiable, pon un proxy con auth delante.

## Licencia

[MIT](LICENSE).