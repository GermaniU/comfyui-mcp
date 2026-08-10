"""Tool comfy_health: estado de ComfyUI, VRAM y cola."""

from .. import comfy_client


async def comfy_health() -> str:
    if not await comfy_client.reachable():
        return "ComfyUI no disponible (inactivo). Usar generate_image para arrancarlo."
    stats = await comfy_client.system_stats()
    q = await comfy_client.queue()
    dev = stats["devices"][0]
    vram_free = dev["vram_free"] / 1024**3
    vram_total = dev["vram_total"] / 1024**3
    pending = len(q.get("queue_pending", []))
    running = len(q.get("queue_running", []))
    return (
        f"ComfyUI OK ({stats['system']['comfyui_version']}) · {dev['name']} · "
        f"VRAM {vram_free:.1f}/{vram_total:.1f} GB libres · "
        f"cola: {running} corriendo, {pending} pendientes"
    )
