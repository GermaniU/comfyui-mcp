FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Dentro del contenedor hay que escuchar en todas las interfaces para que
    # el port mapping funcione; publica el puerto solo en 127.0.0.1 del host.
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8201

# El MCP Registry verifica la propiedad de la imagen con este label: su valor
# debe coincidir EXACTO con el "name" de server.json.
LABEL io.modelcontextprotocol.server.name="io.github.GermaniU/comfyui-mcp"

WORKDIR /app

# README.md hace falta: pyproject.toml lo declara como readme del paquete.
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

# El server expone HTTP/SSE en 8201 (modo por defecto) y stdio con --stdio.
# No hay ruta /health, así que no se declara HEALTHCHECK: en modo stdio no hay
# puerto que sondear y el probe marcaría el contenedor como unhealthy.
EXPOSE 8201

# Sin argumentos arranca en HTTP; el cliente MCP pasa --stdio para el modo stdio.
ENTRYPOINT ["comfyui-mcp"]
