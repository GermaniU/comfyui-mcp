# comfyui-mcp

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-HTTP%2FSSE-green.svg)](https://modelcontextprotocol.io/)
[![FastMCP](https://img.shields.io/badge/FastMCP-v2.0+-purple.svg)](https://github.com/jlowin/fastmcp)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/GermaniU/comfyui-mcp)

<p align="center">
  <img src="docs/assets/banner.jpg" alt="ComfyUI MCP Architecture & Banner" width="100%" />
</p>

**Servidor MCP HTTP/SSE profesional para generación de imágenes con ComfyUI (SDXL / RTX 3060).**

`comfyui-mcp` actúa como un adaptador middleware desacoplado que expone las capacidades de inferencia de ComfyUI a cualquier gateway o cliente compatible con el **Model Context Protocol (MCP)** en la red LAN sin necesidad de instalar entornos de PyTorch ni modelos localmente en los clientes.

[English Version (README.en.md)](README.en.md) | [Arquitectura](docs/ARCHITECTURE.md) | [Setup del Servidor Backend](docs/SERVER_SETUP.md)

---

## ⚡ Características Principales

- 🎨 **Generación txt2img y img2img**: Soporte nativo para prompts SDXL con configuración programática de aspect ratio, pasos de muestreo, denoising y semillas.
- 🎯 **Presets Optimizados**: Ajustes preconfigurados para casos de uso comunes (`producto`, `realista`, `rapido`, `anime`).
- 🧠 **GPU Arbiter (VRAM Switching)**: Coordinación automática de memoria VRAM con servidores LLM (`llama-server`) mediante systemd para maximizar el uso de GPUs de 12GB.
- 🌐 **Transporte HTTP/SSE Desacoplado**: Expone herramientas vía HTTP en el puerto `8201`, permitiendo que clientes en macOS, Linux o Windows consuman el servicio de manera transparente.
- 🖼️ **Entrega Directa de Imágenes**: Resolución de URLs públicas/LAN para descarga inmediata sin compartir sistemas de archivos.
- 🔍 **Monitoreo e Inspección**: Herramientas para consultar salud de la GPU, cola de procesamiento, checkpoints y LoRAs disponibles.

---

## 🏗️ Arquitectura y Deslinde de Componentes

> ⚠️ **IMPORTANTE: Entender los Límites del Sistema**
>
> `comfyui-mcp` es **únicamente la capa de transporte e interfaz MCP**. No incluye el motor de inferencia de ComfyUI ni los archivos de peso de modelos.
> Para la guía de despliegue del servidor backend, consulta [docs/SERVER_SETUP.md](docs/SERVER_SETUP.md).

```
 +-------------------------------------------------------+
 |                 Clientes MCP (LAN)                    |
 | (Claude Code CLI / Cursor / Windsurf / Hermes Gateway)|
 +-------------------------------------------------------+
                             |
                             | HTTP / SSE (Puerto 8201)
                             v
 +-------------------------------------------------------+
 |                  comfyui-mcp Server                   |
 |           (FastMCP + Workflow JSON Builder)           |
 +-------------------------------------------------------+
                             |
                             | Loopback HTTP (Puerto 8188)
                             v
 +-------------------------------------------------------+
 |                 ComfyUI Backend Host                  |
 |  (PyTorch + CUDA + SDXL Checkpoints + GPU Arbiter)    |
 +-------------------------------------------------------+
```

---

## 📦 Instalación Rápida

### Requisitos
- Python 3.11+
- `uv` (recomendado) o `pip`

### Clonar e Instalar

```bash
git clone https://github.com/GermaniU/comfyui-mcp.git
cd comfyui-mcp

# Crear entorno virtual e instalar
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## ⚙️ Configuración (Variables de Entorno)

Crea un archivo `.env` o exporta las siguientes variables:

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | URL loopback donde escucha el motor de ComfyUI. |
| `COMFYUI_PUBLIC_URL` | `http://192.168.68.108:8188` | Base URL pública/LAN para descarga de imágenes. |
| `MCP_HOST` | `0.0.0.0` | Host binding para el servidor MCP. |
| `MCP_PORT` | `8201` | Puerto HTTP/SSE del servidor MCP. |

---

## 🛠️ Herramientas Expuestas (Tool Reference)

### 1. `generate_image` (txt2img)
Genera una imagen desde un prompt textual usando SDXL.

- **Parámetros**:
  - `prompt` (*string*, requerido): Descripción detallada de la imagen a generar.
  - `negative_prompt` (*string*, opcional): Elementos a excluir. Default: `"ugly, blurry, low quality, distorted"`.
  - `preset` (*string*, opcional): Preset predefinido (`producto`, `realista`, `rapido`, `anime`). Default: `"realista"`.
  - `aspect_ratio` (*string*, opcional): Relación de aspecto (`1:1`, `16:9`, `9:16`, `4:3`, `3:4`). Default: `"1:1"`.
  - `seed` (*integer*, opcional): Semilla para reproducibilidad (-1 para aleatoria). Default: `-1`.
  - `steps` (*integer*, opcional): Pasos del sampler (sobreescribe preset si se especifica).
  - `cfg` (*float*, opcional): CFG scale.

### 2. `img2img` (Image-to-Image)
Transforma una imagen existente aplicando un nuevo prompt y nivel de denoise.

- **Parámetros**:
  - `image_source` (*string*, requerido): URL pública o cadena Base64 de la imagen de entrada.
  - `prompt` (*string*, requerido): Instrucción de transformación.
  - `denoise` (*float*, opcional): Intensidad de cambio (`0.1` a `1.0`). Default: `0.7`.
  - `preset` (*string*, opcional): Preset de checkpoint/sampler. Default: `"realista"`.

### 3. `list_models`
Retorna la lista de checkpoints, LoRAs y samplers disponibles en la instancia de ComfyUI.

### 4. `comfy_health`
Obtiene el estado de salud del backend: versión de ComfyUI, uso de VRAM de la GPU y tareas en cola.

### 5. `comfy_view_url`
Construye la URL LAN de descarga directa para un archivo generado previamente dado su `filename` y `subfolder`.

---

## 🎨 Matriz de Presets

| Preset | Checkpoint Asociado | Pasos | CFG | Caso de Uso |
|--------|---------------------|-------|-----|-------------|
| `producto` | `RealVisXL_V4.0.safetensors` | 30 | 7.0 | Fotografía comercial y de producto fotorrealista. |
| `realista` | `juggernautXL_ragnarokBy.safetensors` | 30 | 7.0 | Fotorrealismo versátil de alta calidad (Default). |
| `rapido` | `juggernautXL_ragnarokBy.safetensors` | 6 | 2.0 | Vista previa y borradores en ~5 segundos. |
| `anime` | `animagine-xl-3.1.safetensors` | 28 | 7.0 | Ilustración digital y estilo anime. |

---

## 🔗 Integración con Clientes MCP

### Configuración para Claude Code CLI (`~/.claude.json`)

```json
{
  "mcpServers": {
    "comfyui": {
      "url": "http://192.168.68.108:8201/mcp"
    }
  }
}
```

### Configuración para Hermes Gateway (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  comfyui:
    url: "http://192.168.68.108:8201/mcp"
    transport: "http"
```

### Configuración para Cursor / Windsurf / Claude Desktop

Añade un servidor MCP de tipo **SSE / HTTP** con la URL `http://<LAN_IP>:8201/mcp`.

---

## 📋 Componentes Faltantes y Roadmap (Server Gaps)

Dado que este repo representa la **capa MCP**, los siguientes elementos están fuera de este repositorio y deben configurarse en el servidor host:

1. **Servidor Backend ComfyUI**: Requiere instalación independiente de Python + PyTorch CUDA.
2. **Descarga de Checkpoints**: Los modelos SDXL deben descargarse manualmente en el directorio `models/checkpoints/` del servidor ComfyUI.
3. **GPU Arbiter Script**: El script `gpu-broker.sh` y las reglas `/etc/sudoers.d/gpu-arbiter` deben residir en la máquina Linux con la GPU.
4. **Futuras Mejoras del MCP**:
   - Soporte para inyección de workflows JSON personalizados dinámicos.
   - Cancelación y limpieza de colas de procesamiento vía tool MCP.
   - Conexión por WebSocket para reporte de progreso en tiempo real.

---

## 🧪 Pruebas Unitarias

```bash
uv run --with pytest --with pytest-asyncio pytest
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
