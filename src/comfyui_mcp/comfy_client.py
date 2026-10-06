"""HTTP client thin a ComfyUI: system_stats, prompt, history, view."""

import asyncio
import time

import httpx

from .config import COMFY_URL, DEFAULT_TIMEOUT


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=COMFY_URL, timeout=timeout)


async def reachable() -> bool:
    try:
        async with _client(timeout=3.0) as c:
            r = await c.get("/system_stats")
            return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def _rejection(r: httpx.Response) -> str:
    """Resume los node_errors de un 400 de /prompt: qué nodo, qué input y,
    para valores fuera de lista, cuáles son válidos (viene en details)."""
    try:
        body = r.json()
    except ValueError:
        return f"HTTP {r.status_code}: {r.text[:500]}"
    errors = [
        f"{node['class_type']}: {e['message']}" + (f" — {e['details']}" if e.get("details") else "")
        for node in body.get("node_errors", {}).values()
        for e in node["errors"]
    ]
    return "; ".join(errors) or body["error"]["message"]


async def submit_prompt(workflow: dict) -> str:
    """Envía un workflow a ComfyUI y devuelve el prompt_id."""
    async with _client() as c:
        r = await c.post("/prompt", json={"prompt": workflow})
        if r.status_code != 200:
            raise RuntimeError(f"ComfyUI rechazó el workflow: {_rejection(r)}")
        return r.json()["prompt_id"]


async def wait_for_result(prompt_id: str, timeout: float) -> dict:
    """Espera a que termine la generación y devuelve la entrada de /history.
    Si vence el timeout la saca de la cola para que no siga ocupando la GPU."""
    deadline = time.monotonic() + timeout
    async with _client(timeout=30.0) as c:
        while time.monotonic() < deadline:
            r = await c.get(f"/history/{prompt_id}")
            r.raise_for_status()
            data = r.json()
            if prompt_id in data:
                entry = data[prompt_id]
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    msgs = [m for m in status.get("messages", [])
                            if m[0] == "execution_error"]
                    detail = msgs[0][1].get("exception_message") if msgs else "?"
                    raise RuntimeError(f"ComfyUI reportó error: {detail}")
                if entry.get("outputs"):
                    return entry
            await asyncio.sleep(2.0)
        await c.post("/queue", json={"delete": [prompt_id]})
        await c.post("/interrupt", json={"prompt_id": prompt_id})
    raise TimeoutError(f"la generación no terminó en {int(timeout)}s")


async def system_stats() -> dict:
    async with _client() as c:
        r = await c.get("/system_stats")
        r.raise_for_status()
        return r.json()


async def queue() -> dict:
    async with _client() as c:
        r = await c.get("/queue")
        r.raise_for_status()
        return r.json()


async def object_info(node_class: str) -> dict:
    async with _client() as c:
        r = await c.get(f"/object_info/{node_class}")
        r.raise_for_status()
        return r.json()


async def view_jpeg(filename: str, subfolder: str, img_type: str) -> bytes:
    """Imagen vía /view, convertida a JPEG por ComfyUI (param preview)."""
    async with _client() as c:
        r = await c.get("/view", params={"filename": filename, "subfolder": subfolder,
                                         "type": img_type, "preview": "jpeg;80"})
        r.raise_for_status()
        return r.content
