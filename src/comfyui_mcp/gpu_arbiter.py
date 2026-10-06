"""GPU arbiter: asegura que ComfyUI esté corriendo antes de generar."""

import asyncio
import subprocess
import time

from . import comfy_client
from .config import _WAKE_POLL_S, _WAKE_TIMEOUT_S, COMFYUI_SERVICE

_START_FLOOR_S = 10  # piso entre starts; systemd rate-limita starts apilados


def _try_start() -> None:
    # reset-failed despeja el rate-limit de systemd ("Start request repeated
    # too quickly"); un start bloqueado por él no falla distinto de uno por
    # VRAM insuficiente, así que se re-emite antes de cada intento.
    # --no-block: sin él systemctl espera al ExecStartPre del broker (bajar
    # llama-server) y congela el event loop; el polling de abajo ya espera.
    subprocess.run(["systemctl", "reset-failed", COMFYUI_SERVICE],
                   capture_output=True, text=True, check=False)
    subprocess.run(["systemctl", "start", "--no-block", COMFYUI_SERVICE],
                   capture_output=True, text=True, check=False)


async def ensure_comfyui_running() -> str | None:
    """Si ComfyUI no responde, arranca comfyui.service. El GPU Broker
    (configurado en ExecStartPre del systemd service) se encarga de parar
    llama-server gracefully si está idle. Devuelve None si OK, o error."""
    if await comfy_client.reachable():
        return None
    _try_start()
    last_start = time.time()
    deadline = last_start + _WAKE_TIMEOUT_S
    while time.time() < deadline:
        if await comfy_client.reachable():
            return None
        await asyncio.sleep(_WAKE_POLL_S)
        if time.time() - last_start >= _START_FLOOR_S:
            # El start puede fallar por VRAM ocupada (otro servicio con
            # prioridad en el broker la retiene) o quedar rate-blocked;
            # reintentar dentro de la ventana da margen a que la VRAM se libere.
            _try_start()
            last_start = time.time()
    return (
        f"{COMFYUI_SERVICE} no respondió tras {_WAKE_TIMEOUT_S}s de arrancarlo. "
        "Causa típica: el GPU Broker no consiguió la VRAM que pide (otro "
        "servicio la está usando). Reintentar cuando se libere."
    )