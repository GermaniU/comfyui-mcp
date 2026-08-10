"""Tool list_models: checkpoints, loras y samplers disponibles."""

from .. import comfy_client, gpu_arbiter
from ..config import PRESETS


async def list_models() -> str:
    wake_err = await gpu_arbiter.ensure_comfyui_running()
    if wake_err:
        return f"ComfyUI no disponible: {wake_err}"
    ckpts = await comfy_client.object_info("CheckpointLoaderSimple")
    ckpts = ckpts["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    loras = await comfy_client.object_info("LoraLoader")
    loras = loras["LoraLoader"]["input"]["required"]["lora_name"][0]
    lines = ["Checkpoints:"] + [f"  · {c}" for c in ckpts]
    lines += ["Loras:"] + [f"  · {l}" for l in loras]
    lines += ["Presets:"] + [f"  · {k}: {v['descripcion']} ({v['checkpoint']})"
                             for k, v in PRESETS.items()]
    return "\n".join(lines)
