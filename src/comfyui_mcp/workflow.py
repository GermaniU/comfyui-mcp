"""Construcción de workflows txt2img / img2img / video en formato API de ComfyUI."""

from typing import Any


def _base_nodes(checkpoint: str, lora: str | None,
                lora_strength: float) -> tuple[dict, list, list]:
    """Nodos base: checkpoint loader y refs de model/clip (con lora opcional)."""
    wf: dict[str, Any] = {
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": checkpoint}},
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
    filename_prefix: str, detail_face: bool = False, preview: bool = False,
) -> dict:
    """Workflow txt2img. Con lora opcional entre checkpoint y sampler."""
    wf, model_ref, clip_ref = _base_nodes(checkpoint, lora, lora_strength)
    wf["5"] = {"class_type": "EmptyLatentImage",
               "inputs": {"width": width, "height": height, "batch_size": batch}}
    _sampler_nodes(wf, model_ref, clip_ref, prompt, negative, seed, steps,
                   cfg, sampler, scheduler, ["5", 0])
    wf["9"]["inputs"]["filename_prefix"] = filename_prefix
    if detail_face:
        _add_face_detailer(wf, model_ref, clip_ref, seed, steps, cfg,
                           sampler, scheduler)
    if preview:
        _add_preview(wf, wf["9"]["inputs"]["images"])
    return wf


def build_img2img(
    prompt: str, negative: str, checkpoint: str, image_path: str,
    denoise: float, steps: int, cfg: float, sampler: str, scheduler: str,
    seed: int, lora: str | None, lora_strength: float,
    filename_prefix: str, preview: bool = False,
) -> dict:
    """Workflow img2img: carga una imagen, la codifica a latent y la varía con denoise."""
    wf, model_ref, clip_ref = _base_nodes(checkpoint, lora, lora_strength)
    wf["12"] = {"class_type": "LoadImage", "inputs": {"image": image_path}}
    wf["13"] = {"class_type": "VAEEncode",
                "inputs": {"pixels": ["12", 0], "vae": ["4", 2]}}
    _sampler_nodes(wf, model_ref, clip_ref, prompt, negative, seed, steps,
                   cfg, sampler, scheduler, ["13", 0])
    wf["3"]["inputs"]["denoise"] = denoise
    wf["9"]["inputs"]["filename_prefix"] = filename_prefix
    if preview:
        _add_preview(wf, wf["9"]["inputs"]["images"])
    return wf


def build_video(
    prompt: str, negative: str, unet: str, clip: str, vae: str,
    width: int, height: int, length: int, fps: int, steps: int, cfg: float,
    sampler: str, scheduler: str, shift: float, seed: int,
    filename_prefix: str, image_path: str | None = None, preview: bool = False,
) -> dict:
    """Workflow Wan 2.2 TI2V: txt2video, o img2video si hay image_path
    (la imagen es el primer frame)."""
    wf: dict[str, Any] = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": clip, "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": vae}},
        "4": {"class_type": "ModelSamplingSD3",
              "inputs": {"model": ["1", 0], "shift": shift}},
        "5": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": negative, "clip": ["2", 0]}},
        "7": {"class_type": "Wan22ImageToVideoLatent", "inputs": {
            "vae": ["3", 0], "width": width, "height": height,
            "length": length, "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler, "denoise": 1.0,
            "model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0],
            "latent_image": ["7", 0]}},
        "9": {"class_type": "VAEDecode",
              "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "CreateVideo",
               "inputs": {"images": ["9", 0], "fps": fps}},
        "11": {"class_type": "SaveVideo", "inputs": {
            "video": ["10", 0], "filename_prefix": filename_prefix,
            "format": "auto", "codec": "auto"}},
    }
    if image_path:
        wf["12"] = {"class_type": "LoadImage", "inputs": {"image": image_path}}
        wf["7"]["inputs"]["start_image"] = ["12", 0]
    if preview:
        wf["13"] = {"class_type": "ImageFromBatch",
                    "inputs": {"image": ["9", 0], "batch_index": 0, "length": 1}}
        _add_preview(wf, ["13", 0])
    return wf


def _add_preview(wf: dict, images: list) -> None:
    # Copia a la mitad de lo que se guarda (post FaceDetailer si lo hay; el
    # primer frame en video); PreviewImage la deja en temp/ como miniatura.
    wf["15"] = {"class_type": "ImageScaleBy", "inputs": {
        "image": images, "upscale_method": "area", "scale_by": 0.5}}
    wf["16"] = {"class_type": "PreviewImage", "inputs": {"images": ["15", 0]}}


def _add_face_detailer(wf: dict, model_ref: list, clip_ref: list, seed: int,
                       steps: int, cfg: float, sampler: str, scheduler: str) -> None:
    # Mismos steps/cfg/scheduler que el sampler: con el lora de Lightning
    # (preset rapido) los valores de SDXL normal queman la cara.
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
        "seed": seed, "steps": steps, "cfg": cfg,
        "sampler_name": sampler, "scheduler": scheduler,
        "positive": ["11", 0], "negative": ["12", 0],
        "denoise": 0.45, "feather": 5, "noise_mask": True, "force_inpaint": True,
        "bbox_threshold": 0.5, "bbox_dilation": 10, "bbox_crop_factor": 3.0,
        "sam_detection_hint": "center-1", "sam_dilation": 0, "sam_threshold": 0.93,
        "sam_bbox_expansion": 0, "sam_mask_hint_threshold": 0.7,
        "sam_mask_hint_use_negative": "False", "drop_size": 10,
        "bbox_detector": ["13", 0], "wildcard": "", "cycle": 1}}
    wf["9"]["inputs"]["images"] = ["14", 0]
