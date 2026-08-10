<p align="center">
  <img src="docs/assets/og-image.png" alt="ComfyUI MCP — Image Generation for AI Agents via Model Context Protocol" width="720">
</p>

**English** · [Español](README.md)

# ComfyUI MCP — Image Generation for AI Agents via Model Context Protocol (MCP)

> **Connect SDXL image generation capabilities to any AI agent on your network.**
> Open-source MCP server exposing ComfyUI inference (SDXL / RTX 3060) to Claude Code, Cursor, Windsurf, Hermes Gateway, and any client compatible with [Model Context Protocol](https://modelcontextprotocol.io). FastMCP HTTP/SSE + GPU Arbiter, **zero client dependencies, 100% on your hardware**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP%2FSSE-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![CI](https://github.com/GermaniU/comfyui-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/GermaniU/comfyui-mcp/actions/workflows/ci.yml)
[![FastMCP](https://img.shields.io/badge/FastMCP-v2.0+-purple.svg)](https://github.com/jlowin/fastmcp)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Tags:** `mcp-server` · `comfyui` · `sdxl` · `image-generation` · `ai-agents` · `fastmcp` · `claude-code` · `cursor` · `hermes-gateway` · `gpu-arbiter` · `local-first` · `self-hosted`

---

## 💡 Why It Exists

Generating images in multi-agent environments usually requires installing heavy PyTorch dependencies, dedicated GPUs, and complex setups on every client machine. **ComfyUI MCP** solves this by acting as a decoupled HTTP/SSE middleware adapter:

- 🚀 **Zero Local Installation**: Any client or gateway consumes image generation over HTTP/SSE on port `8201` without installing PyTorch or downloading SDXL models locally.
- 🧠 **Smart GPU Arbiter**: Automatically switches between `llama-server` (LLMs) and `ComfyUI` on 12GB GPUs (RTX 3060) without VRAM collisions.
- 🎯 **Professional Presets**: Production-ready generation out of the box with presets like `producto` (RealVisXL V4.0) or `realista` (Juggernaut XL).

---

## 🏗️ Architecture & Component Boundaries

> ⚠️ **IMPORTANT: System Boundaries**
>
> `comfyui-mcp` is **strictly the MCP transport & interface layer**. It does NOT include the ComfyUI inference engine or large model weight files.
> For host server deployment instructions, see [docs/SERVER_SETUP.md](docs/SERVER_SETUP.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
 +-------------------------------------------------------+
 |                 MCP Clients (LAN)                     |
 | (Claude Code CLI / Cursor / Windsurf / Hermes Gateway)|
 +-------------------------------------------------------+
                             |
                             | HTTP / SSE (Port 8201)
                             v
 +-------------------------------------------------------+
 |                  comfyui-mcp Server                   |
 |           (FastMCP + Workflow JSON Builder)           |
 +-------------------------------------------------------+
                             |
                             | Loopback HTTP (Port 8188)
                             v
 +-------------------------------------------------------+
 |                 ComfyUI Backend Host                  |
 |  (PyTorch + CUDA + SDXL Checkpoints + GPU Arbiter)    |
 +-------------------------------------------------------+
```

---

## 📦 Quickstart

### Prerequisites
- Python 3.11+
- `uv` (recommended) or `pip`

### Install

```bash
git clone https://github.com/GermaniU/comfyui-mcp.git
cd comfyui-mcp

# Create venv and install
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## ⚙️ Configuration (Environment Variables)

Create a `.env` file or export environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `COMFYUI_URL` | `http://127.0.0.1:8188` | Loopback URL where the host ComfyUI engine is listening. |
| `COMFYUI_PUBLIC_URL` | `http://192.168.68.108:8188` | Public/LAN base URL for direct client image downloads. |
| `MCP_HOST` | `0.0.0.0` | Host binding for the MCP server. |
| `MCP_PORT` | `8201` | HTTP/SSE port for the MCP server. |
| `MCP_AUTH_TOKEN` | *(empty = no auth)* | If set, requires `Authorization: Bearer <token>` header on every HTTP/SSE request. |

---

## 🛠️ MCP Tool Reference

### 1. `generate_image` (txt2img)
Generates an image from a text prompt using SDXL.

- **Parameters**:
  - `prompt` (*string*, required): Detailed description of the image to generate.
  - `negative_prompt` (*string*, optional): Concepts to exclude. Default: `"ugly, blurry, low quality, distorted"`.
  - `preset` (*string*, optional): Preset profile (`producto`, `realista`, `rapido`, `anime`). Default: `"realista"`.
  - `aspect_ratio` (*string*, optional): Target aspect ratio (`1:1`, `16:9`, `9:16`, `4:3`, `3:4`). Default: `"1:1"`.
  - `seed` (*integer*, optional): Random seed (-1 for random). Default: `-1`.
  - `steps` (*integer*, optional): Sampler steps (overrides preset default).
  - `cfg` (*float*, optional): CFG scale.

### 2. `img2img`
Transforms an existing image using a new prompt and denoise strength.

- **Parameters**:
  - `image_source` (*string*, required): Public URL or Base64 string of input image.
  - `prompt` (*string*, required): Transformation instruction.
  - `denoise` (*float*, optional): Denoising strength (`0.1` to `1.0`). Default: `0.7`.
  - `preset` (*string*, optional): Preset checkpoint/sampler profile. Default: `"realista"`.

### 3. `list_models`
Returns available checkpoints, LoRAs, and samplers installed on the ComfyUI instance.

### 4. `comfy_health`
Retrieves backend engine health: ComfyUI version, GPU VRAM usage, and queue length.

### 5. `comfy_view_url`
Constructs the direct LAN download URL for a generated image given its `filename` and `subfolder`.

---

## 🎨 Preset Matrix

| Preset | Associated Checkpoint | Steps | CFG | Primary Use Case |
|--------|----------------------|-------|-----|------------------|
| `producto` | `RealVisXL_V4.0.safetensors` | 30 | 7.0 | Photorealistic product & commercial photography. |
| `realista` | `juggernautXL_ragnarokBy.safetensors` | 30 | 7.0 | High quality general photorealism (Default). |
| `rapido` | `juggernautXL_ragnarokBy.safetensors` | 6 | 2.0 | Draft previews in ~5 seconds. |
| `anime` | `animagine-xl-3.1.safetensors` | 28 | 7.0 | Digital illustration and anime styles. |

---

## 🔗 Client Integration Guides

### Claude Code CLI (`~/.claude.json`)

```json
{
  "mcpServers": {
    "comfyui": {
      "url": "http://192.168.68.108:8201/mcp"
    }
  }
}
```

### Hermes Gateway (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  comfyui:
    url: "http://192.168.68.108:8201/mcp"
    transport: "http"
```

---

## 🧪 Running Tests

```bash
uv run --with pytest --with pytest-asyncio pytest
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
