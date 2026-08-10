"""Tests de config: presets y aspects válidos."""

from comfyui_mcp.config import ASPECTS, PRESETS


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
