"""Tests de config: presets y aspects válidos."""

from comfyui_mcp.config import ASPECTS, PRESETS, VIDEO_ASPECTS, VIDEO_DRAFT_ASPECTS


def test_presets_requeridos():
    for k in ("producto", "realista", "rapido", "anime"):
        assert k in PRESETS
        assert "checkpoint" in PRESETS[k]
        assert "steps" in PRESETS[k]


def test_aspects_son_multiplos_de_8():
    for name, (w, h) in ASPECTS.items():
        assert w % 8 == 0, f"{name} width {w} no es múltiplo de 8"
        assert h % 8 == 0, f"{name} height {h} no es múltiplo de 8"


def test_aspects_1mp():
    for name, (w, h) in ASPECTS.items():
        assert 700_000 <= w * h <= 1_200_000, f"{name} fuera de rango ~1MP"


def test_video_aspects_son_multiplos_de_32():
    for name, (w, h) in [*VIDEO_ASPECTS.items(), *VIDEO_DRAFT_ASPECTS.items()]:
        assert w % 32 == 0 and h % 32 == 0, f"{name} {w}x{h} no es múltiplo de 32"


def test_borrador_tiene_los_mismos_aspects_y_menos_pixeles():
    assert VIDEO_DRAFT_ASPECTS.keys() == VIDEO_ASPECTS.keys()
    for name, (w, h) in VIDEO_DRAFT_ASPECTS.items():
        full_w, full_h = VIDEO_ASPECTS[name]
        assert w * h < full_w * full_h / 2, f"{name}: el borrador no ahorra la mitad"
