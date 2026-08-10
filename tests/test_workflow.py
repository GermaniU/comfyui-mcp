"""Tests de workflow: estructura de nodos txt2img e img2img."""

from comfyui_mcp.workflow import build_img2img, build_txt2img


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
