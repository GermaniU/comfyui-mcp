"""Tests de workflow: estructura de nodos txt2img, img2img y video."""

from comfyui_mcp.config import VIDEO_MODEL
from comfyui_mcp.workflow import build_img2img, build_txt2img, build_video


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
    assert wf["7"]["class_type"] == "Wan22ImageToVideoLatent"
    assert "start_image" not in wf["7"]["inputs"]
    assert "12" not in wf
    assert wf["8"]["inputs"]["model"] == ["4", 0], "el sampler va con el shift de ModelSamplingSD3"
    assert wf["11"]["class_type"] == "SaveVideo"
    assert wf["11"]["inputs"]["video"] == ["10", 0]


def test_img2video_usa_la_imagen_como_primer_frame():
    wf = _video(image_path="base_00001_.png [output]")
    assert wf["12"] == {"class_type": "LoadImage", "inputs": {"image": "base_00001_.png [output]"}}
    assert wf["7"]["inputs"]["start_image"] == ["12", 0]


def test_preview_de_video_es_el_primer_frame():
    wf = _video(preview=True)
    assert wf["13"]["inputs"] == {"image": ["9", 0], "batch_index": 0, "length": 1}
    assert wf["15"]["inputs"]["image"] == ["13", 0]
    assert wf["16"]["class_type"] == "PreviewImage"
