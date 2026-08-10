"""HTTP client thin a ComfyUI: system_stats, prompt, history, view."""

import httpx

from .config import COMFY_URL, DEFAULT_TIMEOUT


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=COMFY_URL, timeout=timeout)


async def reachable() -> bool:
    try:
        async with _client(timeout=3.0) as c:
            r = await c.get("/system_stats")
            return r.status_code == 200
    except Exception:
        return False


async def submit_prompt(workflow: dict) -> str:
    """Envía un workflow a ComfyUI y devuelve el prompt_id."""
    async with _client() as c:
        r = await c.post("/prompt", json={"prompt": workflow})
        if r.status_code != 200:
            raise RuntimeError(
                f"ComfyUI rechazó el workflow (HTTP {r.status_code}): {r.text[:500]}"
            )
        return r.json()["prompt_id"]


async def wait_for_result(prompt_id: str, timeout: float) -> dict:
    """Espera a que termine la generación y devuelve la entrada de /history."""
    import asyncio

    deadline = asyncio.get_event_loop().time() + timeout
    async with _client(timeout=30.0) as c:
        while asyncio.get_event_loop().time() < deadline:
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
