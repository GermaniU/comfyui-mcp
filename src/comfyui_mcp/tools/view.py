"""Tool comfy_view_url: URL LAN de descarga para una imagen ya generada."""

from ..config import COMFY_PUBLIC_URL


async def comfy_view_url(filename: str, subfolder: str = "", img_type: str = "output") -> str:
    """Devuelve la URL LAN de descarga directa para una imagen ya generada."""
    return (f"{COMFY_PUBLIC_URL}/view?filename={filename}"
            f"&subfolder={subfolder}&type={img_type}")
