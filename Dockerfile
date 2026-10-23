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

# Bootstrap a pip that no longer trusts the compromised emSign CA
# (GHSA-6q48-6c7w-9gw2) before resolving anything from PyPI. The wheel is
# fetched with a pinned SHA-256 and run directly, so the base image's older
# pip never touches the network. The system CA store is refreshed too, since
# pip also consults it.
ADD --checksum=sha256:fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70 \
    https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl \
    /tmp/pip-26.2.2-py3-none-any.whl
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python /tmp/pip-26.2.2-py3-none-any.whl/pip install --no-cache-dir --no-index \
       /tmp/pip-26.2.2-py3-none-any.whl \
    && rm /tmp/pip-26.2.2-py3-none-any.whl

RUN pip install --no-cache-dir .

# El server expone HTTP/SSE en 8201 (modo por defecto) y stdio con --stdio.
# No hay ruta /health, así que no se declara HEALTHCHECK: en modo stdio no hay
# puerto que sondear y el probe marcaría el contenedor como unhealthy.
EXPOSE 8201

# Sin argumentos arranca en HTTP; el cliente MCP pasa --stdio para el modo stdio.
ENTRYPOINT ["comfyui-mcp"]
