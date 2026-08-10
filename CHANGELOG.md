# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-09

### Añadido
- **Transporte HTTP/SSE**: Migración de MCP de stdio a servidor FastMCP HTTP/SSE accesible en puerto `8201`.
- **Integración GPU Arbiter**: Coordinación automática de VRAM entre ComfyUI y `llama-server` para evitar colisiones de memoria en GPU de 12GB.
- **Herramientas MCP**:
  - `generate_image`: Generación txt2img con soporte para presets (`producto`, `realista`, `rapido`, `anime`), aspect ratio y seed manual.
  - `img2img`: Transformación img2img pasando imagen base como URL o base64 con denoising adaptable.
  - `list_models`: Consulta de checkpoints, LoRAs y samplers disponibles en el server ComfyUI.
  - `comfy_health`: Monitor de salud de ComfyUI (versión, VRAM libre/total, cola de ejecución).
  - `comfy_view_url`: Resolución de URLs LAN para descarga directa de imágenes generadas.
- **Construcción Dinámica de Workflows**: Módulo `workflow.py` para generación de grafos JSON de prompts SDXL compatibles con ComfyUI API.
- **Documentación Profesional**: Cobertura de arquitectura (`docs/ARCHITECTURE.md`), instalación del servidor base ComfyUI (`docs/SERVER_SETUP.md`), guías de contribución y configuración multi-cliente.
