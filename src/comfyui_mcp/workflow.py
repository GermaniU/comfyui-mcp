"""Construcción de workflows txt2img / img2img en formato API de ComfyUI."""

from typing import Any


def _base_nodes(checkpoint: str, width: int, height: int, batch: int,
                lora: str | None, lora_strength: float) -> tuple[dict, list, list]:
    """Nodos base: checkpoint loader, latent, y refs de model/clip (con lora opcional)."""
    wf: dict[str, Any] = {
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": checkpoint}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": batch}},
    }
    model_ref, clip_ref = ["4", 0], ["4", 1]
    if lora:
        wf["10"] = {"class_type": "LoraLoader", "inputs": {
            "lora_name": lora, "strength_model": lora_strength,
            "strength_clip": lora_strength, "model": ["4", 0], "clip": ["4", 1]}}
        model_ref, clip_ref = ["10", 0], ["10", 1]
    return wf, model_ref, clip_ref


def _sampler_nodes(wf: dict, model_ref: list, clip_ref: list, prompt: str,
                   negative: str, seed: int, steps: int, cfg: float,
                   sampler: str, scheduler: str, latent_ref: list) -> None:
    wf.update({
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": clip_ref}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative, "clip": clip_ref}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler, "denoise": 1.0,
            "model": model_ref, "positive": ["6", 0], "negative": ["7", 0],
            "latent_image": latent_ref}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "mcp"}},
    })


def build_txt2img(
    prompt: str, negative: str, checkpoint: str, width: int, height: int,
    steps: int, cfg: float, sampler: str, scheduler: str, seed: int,
    batch: int, lora: str | None, lora_strength: float,
    filename_prefix: str, detail_face: bool = False,
) -> dict:
    """Workflow txt2img. Con lora opcional entre checkpoint y sampler."""
    wf, model_ref, clip_ref = _base_nodes(
        checkpoint, width, height, batch, lora, lora_strength)
    _sampler_nodes(wf, model_ref, clip_ref, prompt, negative, seed, steps,
                   cfg, sampler, scheduler, ["5", 0])
    wf["9"]["inputs"]["filename_prefix"] = filename_prefix
    if detail_face:
        _add_face_detailer(wf, model_ref, clip_ref, seed, sampler)
    return wf


def build_img2img(
    prompt: str, negative: str, checkpoint: str, image_path: str,
    denoise: float, steps: int, cfg: float, sampler: str, scheduler: str,
    seed: int, lora: str | None, lora_strength: float,
    filename_prefix: str,
) -> dict:
    """Workflow img2img: carga una imagen, la codifica a latent y la varía con denoise."""
    wf, model_ref, clip_ref = _base_nodes(
        checkpoint, 1024, 1024, 1, lora, lora_strength)
    wf["12"] = {"class_type": "LoadImage", "inputs": {"image": image_path}}
    wf["13"] = {"class_type": "VAEEncode",
                "inputs": {"pixels": ["12", 0], "vae": ["4", 2]}}
    _sampler_nodes(wf, model_ref, clip_ref, prompt, negative, seed, steps,
                   cfg, sampler, scheduler, ["13", 0])
    wf["3"]["inputs"]["denoise"] = denoise
    wf["9"]["inputs"]["filename_prefix"] = filename_prefix
    return wf


def _add_face_detailer(wf: dict, model_ref: list, clip_ref: list,
                       seed: int, sampler: str) -> None:
    wf["11"] = {"class_type": "CLIPTextEncode", "inputs": {
        "clip": clip_ref,
        "text": "professional portrait photography, sharp detailed realistic eyes, "
                "natural symmetric eyes, detailed iris and pupil, natural catchlights, skin texture"}}
    wf["12"] = {"class_type": "CLIPTextEncode", "inputs": {
        "clip": clip_ref,
        "text": "crossed eyes, lazy eye, asymmetric eyes, blurry eyes, deformed iris, "
                "extra pupils, glassy doll eyes, low quality, worst quality"}}
    wf["13"] = {"class_type": "UltralyticsDetectorProvider",
                "inputs": {"model_name": "bbox/face_yolov8m.pt"}}
    wf["14"] = {"class_type": "FaceDetailer", "inputs": {
        "image": ["8", 0], "model": model_ref, "clip": clip_ref, "vae": ["4", 2],
        "guide_size": 768, "guide_size_for": True, "max_size": 1024,
        "seed": seed, "steps": 24, "cfg": 5.0,
        "sampler_name": sampler, "scheduler": "karras",
        "positive": ["11", 0], "negative": ["12", 0],
        "denoise": 0.45, "feather": 5, "noise_mask": True, "force_inpaint": True,
        "bbox_threshold": 0.5, "bbox_dilation": 10, "bbox_crop_factor": 3.0,
        "sam_detection_hint": "center-1", "sam_dilation": 0, "sam_threshold": 0.93,
        "sam_bbox_expansion": 0, "sam_mask_hint_threshold": 0.7,
        "sam_mask_hint_use_negative": "False", "drop_size": 10,
        "bbox_detector": ["13", 0], "wildcard": "", "cycle": 1}}
    wf["9"]["inputs"]["images"] = ["14", 0]
