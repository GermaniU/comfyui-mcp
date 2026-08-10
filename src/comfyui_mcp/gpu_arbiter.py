"""GPU arbiter: asegura que ComfyUI esté corriendo antes de generar."""

import asyncio
import subprocess
import time

from . import comfy_client
from .config import COMFYUI_SERVICE, _WAKE_POLL_S, _WAKE_TIMEOUT_S


async def ensure_comfyui_running() -> str | None:
    """Si ComfyUI no responde, arranca comfyui.service. El GPU Broker
    (configurado en ExecStartPre del systemd service) se encarga de parar
    llama-server gracefully si está idle. Devuelve None si OK, o error."""
    if await comfy_client.reachable():
        return None
    subprocess.run(["systemctl", "start", COMFYUI_SERVICE],
                   capture_output=True, text=True)
    deadline = time.time() + _WAKE_TIMEOUT_S
    while time.time() < deadline:
        if await comfy_client.reachable():
            return None
        await asyncio.sleep(_WAKE_POLL_S)
    return f"{COMFYUI_SERVICE} no respondió tras {_WAKE_TIMEOUT_S}s de arrancarlo."
