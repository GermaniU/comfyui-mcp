"""Tool comfy_view_url: URL LAN de descarga para una imagen ya generada."""

from urllib.parse import urlencode

from ..config import COMFY_PUBLIC_URL


def comfy_view_url(filename: str, subfolder: str = "", img_type: str = "output") -> str:
    """Devuelve la URL LAN de descarga directa para una imagen ya generada."""
    query = urlencode({"filename": filename, "subfolder": subfolder, "type": img_type})
    return f"{COMFY_PUBLIC_URL}/view?{query}"


def image_lines(entry: dict) -> list[str]:
    """Una línea `filename → url` por imagen en los outputs de /history."""
    return [
        f"  · {img['filename']} → "
        + comfy_view_url(img["filename"], img.get("subfolder", ""), img.get("type", "output"))
        for out in entry["outputs"].values()
        for img in out.get("images", [])
    ]
