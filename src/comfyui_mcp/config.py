"""Configuración central: env vars, presets, aspects y constantes."""

import os
from typing import Any

COMFY_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFY_PUBLIC_URL = os.getenv("COMFYUI_PUBLIC_URL", "http://localhost:8188")
COMFYUI_SERVICE = "comfyui.service"
GPU_BROKER = os.path.expanduser("~/stack/gpu-broker/gpu-broker.sh")

_WAKE_TIMEOUT_S = 90
_WAKE_POLL_S = 2

DEFAULT_TIMEOUT = 15.0
GENERATE_TIMEOUT = 600.0  # primera carga de un checkpoint SDXL (6.5GB) + sampling

DEFAULT_NEGATIVE = (
    "low quality, worst quality, blurry, jpeg artifacts, watermark, text, "
    "logo, signature, deformed, bad anatomy, extra fingers"
)

# Presets: checkpoint + sampler tuning. "rapido" usa SDXL-Lightning (4-8 steps).
# "anime" requiere animagine-xl-3.1.safetensors — NO migrado, fallará con error claro.
PRESETS: dict[str, dict[str, Any]] = {
    "producto": {
        "checkpoint": "RealVisXL_V4.0.safetensors",
        "steps": 30, "cfg": 5.5, "sampler": "dpmpp_2m", "scheduler": "karras",
        "descripcion": "fotorrealista para fotos de producto/marketing",
    },
    "realista": {
        "checkpoint": "juggernautXL_ragnarokBy.safetensors",
        "steps": 30, "cfg": 5.0, "sampler": "dpmpp_2m", "scheduler": "karras",
        "descripcion": "fotorrealista versátil (escenas, personas, ambientes)",
    },
    "rapido": {
        "checkpoint": "juggernautXL_ragnarokBy.safetensors",
        "lora": "sdxl-lightning-4step.safetensors", "lora_strength": 1.0,
        "steps": 6, "cfg": 1.5, "sampler": "euler", "scheduler": "sgm_uniform",
        "descripcion": "borradores en ~5s con SDXL-Lightning (menor calidad)",
    },
    "anime": {
        "checkpoint": "animagine-xl-3.1.safetensors",
        "steps": 28, "cfg": 7.0, "sampler": "euler_ancestral", "scheduler": "normal",
        "descripcion": "ilustración estilo anime (checkpoint NO migrado — fallará)",
    },
}

# Resoluciones SDXL-friendly (~1MP, múltiplos de 8) por aspect ratio.
ASPECTS = {
    "1:1": (1024, 1024),
    "4:5": (896, 1120),
    "5:4": (1120, 896),
    "9:16": (768, 1344),
    "16:9": (1344, 768),
    "3:2": (1216, 832),
    "2:3": (832, 1216),
}
