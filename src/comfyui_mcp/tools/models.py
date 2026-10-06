"""Tool list_models: checkpoints, loras y presets disponibles."""

from .. import comfy_client
from ..config import PRESETS


async def list_models() -> str:
    presets = ["Presets:"] + [f"  · {k}: {v['descripcion']} ({v['checkpoint']})"
                              for k, v in PRESETS.items()]
    # No despertar ComfyUI solo para listar: arrancarlo saca al LLM de la GPU.
    if not await comfy_client.reachable():
        dormido = ("ComfyUI dormido: checkpoints y loras se listan cuando esté "
                   "activo (lo arranca generate_image o img2img).")
        return "\n".join([*presets, dormido])
    ckpts = await comfy_client.object_info("CheckpointLoaderSimple")
    ckpts = ckpts["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    loras = await comfy_client.object_info("LoraLoader")
    loras = loras["LoraLoader"]["input"]["required"]["lora_name"][0]
    lines = ["Checkpoints:"] + [f"  · {c}" for c in ckpts]
    lines += ["Loras:"] + [f"  · {name}" for name in loras]
    return "\n".join(lines + presets)
