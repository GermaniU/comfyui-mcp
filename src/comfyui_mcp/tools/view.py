"""Tool comfy_view_url: URL LAN de descarga para una imagen ya generada."""

from urllib.parse import urlencode

from fastmcp.utilities.types import Image

from .. import comfy_client
from ..config import COMFY_PUBLIC_URL


def comfy_view_url(filename: str, subfolder: str = "", img_type: str = "output") -> str:
    """Devuelve la URL LAN de descarga directa para una imagen ya generada."""
    query = urlencode({"filename": filename, "subfolder": subfolder, "type": img_type})
    return f"{COMFY_PUBLIC_URL}/view?{query}"


def _images(entry: dict, img_type: str) -> list[dict]:
    return [img for out in entry["outputs"].values()
            for img in out.get("images", []) if img["type"] == img_type]


def image_lines(entry: dict) -> list[str]:
    """Una línea `filename → url` por imagen guardada en output/."""
    return [
        f"  · {img['filename']} → " + comfy_view_url(img["filename"], img["subfolder"])
        for img in _images(entry, "output")
    ]


async def thumbnails(entry: dict) -> list[Image]:
    """Las miniaturas que dejó PreviewImage en temp/, como JPEG."""
    return [
        Image(data=await comfy_client.view_jpeg(img["filename"], img["subfolder"], "temp"),
              format="jpeg")
        for img in _images(entry, "temp")
    ]
