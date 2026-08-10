# Arquitectura de `comfyui-mcp`

`comfyui-mcp` es un **servidor MCP HTTP/SSE** desacoplado que actúa como adaptador middleware entre clientes MCP (Claude Desktop, Claude Code CLI, Cursor, Windsurf, Hermes Gateway) y un motor de inferencia **ComfyUI**.

---

## 🏗️ Visión General de la Arquitectura

```
 +-------------------------------------------------------------------+
 |                      MCP Clients / Gateways                       |
 |    (Claude Desktop / Cursor / Windsurf / Hermes Gateway LAN)      |
 +-------------------------------------------------------------------+
                                  |
                                  | HTTP / SSE (Puerto 8201)
                                  v
 +-------------------------------------------------------------------+
 |                         comfyui-mcp Server                        |
 |                                                                   |
 |  +--------------------+  +--------------------+  +-------------+  |
 |  | FastMCP Server     |  | GPU Arbiter Client |  | Workflow    |  |
 |  | (server.py)        |  | (gpu_arbiter.py)   |  | Builder     |  |
 |  +--------------------+  +--------------------+  +-------------+  |
 |            |                        |                           |
 |            +------------+-----------+                           |
 |                         | HTTP Client                           |
 |                         v                                       |
 |             +------------------------+                          |
 |             | ComfyClient            |                          |
 |             | (comfy_client.py)      |                          |
 |             +------------------------+                          |
 +-------------------------------------------------------------------+
                           |
                           | Loopback HTTP REST / WS (Puerto 8188)
                           v
 +-------------------------------------------------------------------+
 |                         ComfyUI Engine                            |
 |        (PyTorch + CUDA + SDXL Checkpoints + Impact Pack)         |
 +-------------------------------------------------------------------+
                                  |
                                  | Renderiza Imagen en /output
                                  v
 +-------------------------------------------------------------------+
 |                   Static LAN HTTP File Access                     |
 |             http://<LAN_IP>:8188/view?filename=...                |
 +-------------------------------------------------------------------+
```

---

## 🧩 Componentes Principales

### 1. FastMCP Server (`src/comfyui_mcp/server.py`)
- Expone endpoints HTTP y SSE bajo el protocolo Model Context Protocol (MCP).
- Declara e inicia las herramientas expuestas (`generate_image`, `img2img`, `list_models`, `comfy_health`, `comfy_view_url`).
- Maneja el ciclo de vida del servidor Uvicorn / Starlette.

### 2. Comfy Client (`src/comfyui_mcp/comfy_client.py`)
- Cliente HTTP asíncrono liviano sobre `httpx`.
- Traduce llamadas MCP en invocaciones a la REST API interna de ComfyUI:
  - `GET /system_stats` — Monitoreo de VRAM y estado de GPU.
  - `POST /prompt` — Encolamiento de grafos JSON de workflow.
  - `GET /history/{prompt_id}` — Polling del estado de ejecución de la imagen.
  - `GET /object_info` — Descubrimiento de checkpoints, LoRAs y samplers instalados.

### 3. Workflow Builder (`src/comfyui_mcp/workflow.py`)
- Construye el grafo JSON del prompt de ComfyUI de forma programática.
- Soporta pipelines SDXL txt2img e img2img.
- Configura nodos clave: `KSampler`, `CheckpointLoaderSimple`, `CLIPTextEncode`, `EmptyLatentImage`, `VAEDecode`, `SaveImage`, y `LoadImage`.
- Aplica presets predefinidos (`producto`, `realista`, `rapido`, `anime`) ajustando modelos, pasos de muestreo, cfg y sampler name.

### 4. GPU Arbiter (`src/comfyui_mcp/gpu_arbiter.py`)
- Coordina el uso de memoria VRAM en servidores con GPUs compartidas (ej. NVIDIA RTX 3060 de 12GB).
- Evita colisiones de VRAM entre ComfyUI y servidores LLM locales (`llama-server`).
- Interactúa con el script del host `gpu-broker.sh` mediante invocaciones HTTP/Systemd para asegurar que ComfyUI esté levantado y con VRAM lista antes de encolar una generación.

---

## 🔄 Flujo de Datos (txt2img / img2img)

1. **Recepción**: El cliente MCP envía una solicitud a la tool `generate_image` o `img2img` en `http://<HOST>:8201/mcp`.
2. **Arbitraje GPU**: `gpu_arbiter.py` verifica y asegura que ComfyUI esté activo (`ensure_comfyui_running`). Si `llama-server` está ocupando VRAM, el arbiter realiza la transición de servicios vía systemd.
3. **Generación del Grafo**: `workflow.py` compila los parámetros (prompt, negative prompt, aspect ratio, seed, steps, preset) en el formato JSON nativo de nodos de ComfyUI.
4. **Encolamiento**: `comfy_client.py` envía la carga útil a `POST http://127.0.0.1:8188/prompt`.
5. **Monitoreo**: El cliente realiza polling en `GET /history/{prompt_id}` hasta confirmar que los nodos completaron el procesamiento.
6. **Resolución de URL**: El servidor extrae el `filename` y `subfolder` de la salida devuelta por ComfyUI y construye una URL pública LAN accesible (`http://<LAN_IP>:8188/view?filename=...`).

---

## 🔒 Red y Seguridad

- **Loopback Interno**: ComfyUI escucha en `127.0.0.1:8188` para evitar exponer APIs administrativas no autenticadas a la red externa.
- **MCP LAN Binding**: El MCP server se enlaza en `0.0.0.0:8201` (o la interfaz LAN configurada), protegido por reglas UFW del host (`ufw allow from <YOUR_LAN_CIDR>`).
