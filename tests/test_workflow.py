"""Tests de workflow: estructura de nodos txt2img, img2img y video."""

from comfyui_mcp.config import A14B_MODEL, VIDEO_MODEL
from comfyui_mcp.workflow import (
    build_a14b_video,
    build_img2img,
    build_txt2img,
    build_video,
)


def test_txt2img_nodos_esenciales():
    wf = build_txt2img(
        prompt="a cat", negative="bad", checkpoint="ckpt.safetensors",
        width=1024, height=1024, steps=30, cfg=5.0,
        sampler="dpmpp_2m", scheduler="karras", seed=1, batch=1,
        lora=None, lora_strength=0.8, filename_prefix="mcp",
    )
    assert wf["4"]["class_type"] == "CheckpointLoaderSimple"
    assert wf["3"]["class_type"] == "KSampler"
    assert wf["8"]["class_type"] == "VAEDecode"
    assert wf["9"]["class_type"] == "SaveImage"
    assert wf["9"]["inputs"]["filename_prefix"] == "mcp"


def test_txt2img_con_lora():
    wf = build_txt2img(
        prompt="a cat", negative="bad", checkpoint="ckpt.safetensors",
        width=1024, height=1024, steps=30, cfg=5.0,
        sampler="dpmpp_2m", scheduler="karras", seed=1, batch=1,
        lora="lora.safetensors", lora_strength=0.8, filename_prefix="mcp",
    )
    assert wf["10"]["class_type"] == "LoraLoader"
    # el sampler debe referenciar el lora como model/clip
    assert wf["3"]["inputs"]["model"] == ["10", 0]
    assert wf["3"]["inputs"]["positive"] == ["6", 0]


def test_img2img_usa_vaeencode_y_denoise():
    wf = build_img2img(
        prompt="a cat", negative="bad", checkpoint="ckpt.safetensors",
        image_path="input.png", denoise=0.6, steps=30, cfg=5.0,
        sampler="dpmpp_2m", scheduler="karras", seed=1,
        lora=None, lora_strength=0.8, filename_prefix="mcp",
    )
    assert wf["12"]["class_type"] == "LoadImage"
    assert wf["13"]["class_type"] == "VAEEncode"
    assert wf["3"]["inputs"]["denoise"] == 0.6
    assert wf["3"]["inputs"]["latent_image"] == ["13", 0]


def test_img2img_no_arma_latent_vacio():
    wf = build_img2img(
        prompt="a cat", negative="bad", checkpoint="ckpt.safetensors",
        image_path="input.png", denoise=0.6, steps=30, cfg=5.0,
        sampler="dpmpp_2m", scheduler="karras", seed=1,
        lora=None, lora_strength=0.8, filename_prefix="mcp",
    )
    assert "5" not in wf


def test_face_detailer_usa_params_del_sampler():
    wf = build_txt2img(
        prompt="a cat", negative="bad", checkpoint="ckpt.safetensors",
        width=1024, height=1024, steps=6, cfg=1.5,
        sampler="euler", scheduler="sgm_uniform", seed=1, batch=1,
        lora="lightning.safetensors", lora_strength=1.0, filename_prefix="mcp",
        detail_face=True,
    )
    fd = wf["14"]["inputs"]
    assert (fd["steps"], fd["cfg"], fd["scheduler"]) == (6, 1.5, "sgm_uniform")
    assert wf["9"]["inputs"]["images"] == ["14", 0]


def test_preview_escala_lo_que_guarda_saveimage():
    wf = build_txt2img(
        prompt="a cat", negative="bad", checkpoint="ckpt.safetensors",
        width=1024, height=1024, steps=30, cfg=5.0,
        sampler="dpmpp_2m", scheduler="karras", seed=1, batch=1,
        lora=None, lora_strength=0.8, filename_prefix="mcp",
        detail_face=True, preview=True,
    )
    assert wf["15"]["inputs"]["image"] == ["14", 0]
    assert wf["16"] == {"class_type": "PreviewImage", "inputs": {"images": ["15", 0]}}


def test_sin_preview_no_hay_nodos_extra():
    wf = build_img2img(
        prompt="a cat", negative="bad", checkpoint="ckpt.safetensors",
        image_path="input.png", denoise=0.6, steps=30, cfg=5.0,
        sampler="dpmpp_2m", scheduler="karras", seed=1,
        lora=None, lora_strength=0.8, filename_prefix="mcp",
    )
    assert "15" not in wf and "16" not in wf


def _video(**kw):
    return build_video(prompt="a cat", negative="bad", width=1280, height=704,
                       length=73, fps=24, seed=1, filename_prefix="mcp-video",
                       **VIDEO_MODEL, **kw)


def test_txt2video_sin_imagen_de_partida():
    wf = _video()
    assert wf["1"]["inputs"] == {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors",
                                  "weight_dtype": "fp8_e4m3fn"}
    assert wf["8"]["inputs"]["steps"] == 30
    assert (wf["8"]["inputs"]["cfg"], wf["8"]["inputs"]["sampler_name"],
            wf["8"]["inputs"]["scheduler"], wf["4"]["inputs"]["shift"]) == (5.0, "uni_pc", "simple", 8.0)
    assert wf["9"] == {"class_type": "VAEDecodeTiled", "inputs": {
        "samples": ["8", 0], "vae": ["3", 0], "tile_size": 512,
        "overlap": 64, "temporal_size": 64, "temporal_overlap": 8}}
    assert wf["7"]["class_type"] == "Wan22ImageToVideoLatent"
    assert "start_image" not in wf["7"]["inputs"]
    assert "12" not in wf
    assert wf["8"]["inputs"]["model"] == ["4", 0], "el sampler va con el shift de ModelSamplingSD3"
    assert wf["11"]["class_type"] == "SaveVideo"
    assert wf["11"]["inputs"]["video"] == ["10", 0]
    assert (wf["11"]["inputs"]["format"], wf["11"]["inputs"]["codec"]) == ("mp4", "h264")


def test_img2video_usa_la_imagen_como_primer_frame():
    wf = _video(image_path="base_00001_.png [output]")
    assert wf["12"] == {"class_type": "LoadImage", "inputs": {"image": "base_00001_.png [output]"}}
    assert wf["7"]["inputs"]["start_image"] == ["12", 0]


def test_preview_de_video_es_el_primer_frame():
    wf = _video(preview=True)
    assert wf["13"]["inputs"] == {"image": ["9", 0], "batch_index": 0, "length": 1}
    assert wf["15"]["inputs"]["image"] == ["13", 0]
    assert wf["16"]["class_type"] == "PreviewImage"


def test_a14b_rechaza_formas_y_longitudes_no_validadas():
    import pytest

    for width, height, length, image in (
        (704, 1280, 81, "base.png"), (640, 640, 81, "base.png"),
        (480, 832, 80, "base.png"), (480, 832, 81, ""),
    ):
        with pytest.raises(ValueError, match="A14B"):
            build_a14b_video("motion", "bad", image, width, height,
                             length, 42, "clip")


def test_a14b_grafo_dos_etapas_con_imagen_y_preview():
    wf = build_a14b_video("motion", "no blur", "base.png [output]", 480, 832,
                          81, 42, "clip", preview=True)
    assert wf["1"] == {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": A14B_MODEL["high"]}}
    assert wf["1b"]["inputs"]["unet_name"] == A14B_MODEL["low"]
    assert wf["3"]["inputs"]["vae_name"] == "wan_2.1_vae.safetensors"
    assert wf["20"]["inputs"] == {"model": ["1", 0], "lora_name": A14B_MODEL["lora_high"], "strength_model": 1.0}
    assert wf["20b"]["inputs"]["model"] == ["1b", 0]
    assert wf["20b"]["inputs"]["lora_name"] == A14B_MODEL["lora_low"]
    assert wf["4"]["inputs"] == {"model": ["20", 0], "shift": 5.0}
    assert wf["4b"]["inputs"] == {"model": ["20b", 0], "shift": 5.0}
    assert wf["5"]["inputs"]["text"] == "motion"
    assert wf["6"]["inputs"]["text"] == "no blur"
    assert wf["12"]["inputs"]["image"] == "base.png [output]"
    assert wf["7"]["class_type"] == "WanImageToVideo"
    assert wf["7"]["inputs"] == {"positive": ["5", 0], "negative": ["6", 0],
                                   "vae": ["3", 0], "start_image": ["12", 0],
                                   "width": 480, "height": 832, "length": 81, "batch_size": 1}
    high, low = wf["8a"]["inputs"], wf["8"]["inputs"]
    assert (high["add_noise"], high["start_at_step"], high["end_at_step"], high["return_with_leftover_noise"]) == ("enable", 0, 2, "enable")
    assert (low["add_noise"], low["start_at_step"], low["end_at_step"], low["return_with_leftover_noise"]) == ("disable", 2, 10000, "disable")
    assert (high["model"], low["model"], low["latent_image"]) == (["4", 0], ["4b", 0], ["8a", 0])
    for sampler in (high, low):
        assert (sampler["steps"], sampler["cfg"], sampler["sampler_name"], sampler["scheduler"], sampler["noise_seed"]) == (4, 1.0, "euler", "simple", 42)
        assert (sampler["positive"], sampler["negative"]) == (["7", 0], ["7", 1])
    assert wf["9"]["inputs"]["samples"] == ["8", 0]
    assert wf["9"]["class_type"] == "VAEDecode"
    assert wf["10"]["inputs"] == {"images": ["9", 0], "fps": 16}
    assert wf["11"]["inputs"] == {"video": ["10", 0], "filename_prefix": "clip", "format": "mp4", "codec": "h264"}
    assert wf["13"]["inputs"]["image"] == ["9", 0]
