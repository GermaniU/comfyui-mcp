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
VIDEO_TIMEOUT = 1800.0  # Wan 2.2 5B en la 3060 con offload: varios minutos por clip

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

# Video: Wan 2.2 TI2V 5B, nodos nativos de ComfyUI. Un solo modelo hace
# txt2video e img2video; con el offload de ComfyUI entra en los 12GB.
VIDEO_MODEL = {
    "unet": "wan2.2_ti2v_5B_fp16.safetensors",
    "clip": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
    "vae": "wan2.2_vae.safetensors",
    "steps": 20, "cfg": 5.0, "sampler": "uni_pc", "scheduler": "simple", "shift": 8.0,
}
VIDEO_FPS = 24
VIDEO_MAX_SECONDS = 5  # entrenado con clips de 121 frames

# Lados múltiplos de 32 (Wan22ImageToVideoLatent); 1280x704 es su 720p nativo.
VIDEO_ASPECTS = {
    "16:9": (1280, 704),
    "9:16": (704, 1280),
    "1:1": (960, 960),
}
# Borrador: ~0.4MP, menos de la mitad de píxeles que 720p, para iterar el
# prompt rápido y después sacar la versión final.
VIDEO_DRAFT_ASPECTS = {
    "16:9": (832, 480),
    "9:16": (480, 832),
    "1:1": (640, 640),
}

# El negativo del workflow oficial de Wan (umT5 es multilingüe).
VIDEO_NEGATIVE = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，"
    "低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，"
    "毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走"
)
