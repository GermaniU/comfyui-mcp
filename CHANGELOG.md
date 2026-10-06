# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Añadido
- `preview` en `generate_image` e `img2img`: devuelve una miniatura JPEG (~512px) junto al texto para que el modelo vea el resultado. Sin dependencias nuevas: la escala ComfyUI (`ImageScaleBy` + `PreviewImage`) y la convierte `/view?preview=jpeg`.

### Cambiado
- Los rechazos de ComfyUI nombran el nodo, el input y los valores válidos (ej: checkpoint inexistente) en vez de volcar el JSON crudo.
- `list_models` ya no despierta ComfyUI: si está dormido devuelve los presets, sin sacar al LLM de la GPU.
- `MCP_CORS_ORIGINS` permite restringir los orígenes CORS (default `*`).
- `requires-python` pasa a `>=3.11`, en línea con docs y CI.

### Corregido
- El preset `rapido` aplica el LoRA de Lightning a la fuerza del preset (1.0) en vez de 0.8.
- `detail_face` usa los steps/cfg/scheduler del preset; con `rapido` quemaba las caras.
- Las URLs de descarga codifican `filename`/`subfolder` (espacios, `&`).
- El arranque de `comfyui.service` ya no bloquea el event loop mientras el GPU Broker libera la GPU.
- Una generación que vence el timeout se saca de la cola de ComfyUI.
- `img2img` lee la imagen directo de `output/` (`LoadImage` con `[output]`) sin copiarla a `input/` ni depender de rutas fijas.
- `comfyui-mcp.service` apunta al entry point actual.

## [0.1.0] - 2026-08-09

### Añadido
- **Transporte HTTP/SSE**: Migración de MCP de stdio a servidor FastMCP HTTP/SSE accesible en puerto `8201`.
- **Integración GPU Arbiter**: Coordinación automática de VRAM entre ComfyUI y `llama-server` para evitar colisiones de memoria en GPU de 12GB.
- **Herramientas MCP**:
  - `generate_image`: Generación txt2img con soporte para presets (`producto`, `realista`, `rapido`, `anime`), aspect ratio y seed manual.
  - `img2img`: Variación de una imagen ya generada (por filename) con denoising adaptable.
  - `list_models`: Consulta de checkpoints, LoRAs y samplers disponibles en el server ComfyUI.
  - `comfy_health`: Monitor de salud de ComfyUI (versión, VRAM libre/total, cola de ejecución).
  - `comfy_view_url`: Resolución de URLs LAN para descarga directa de imágenes generadas.
- **Construcción Dinámica de Workflows**: Módulo `workflow.py` para generación de grafos JSON de prompts SDXL compatibles con ComfyUI API.
- **Documentación Profesional**: Cobertura de arquitectura (`docs/ARCHITECTURE.md`), instalación del servidor base ComfyUI (`docs/SERVER_SETUP.md`), guías de contribución y configuración multi-cliente.
