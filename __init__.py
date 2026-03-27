"""
ComfyUI Polza.ai — unified access to 300+ AI models.
Text, Vision, Image Generation via https://polza.ai
"""

from .nodes_chat import PolzaChat
from .nodes_vision import PolzaVision
from .nodes_t2i import PolzaTextToImage
from .nodes_media_image import PolzaMedia
from .nodes_utils import PolzaShowText

NODE_CLASS_MAPPINGS = {
    "PolzaChat":        PolzaChat,
    "PolzaVision":      PolzaVision,
    "PolzaTextToImage": PolzaTextToImage,
    "PolzaMedia": PolzaMedia,
    "PolzaShowText":    PolzaShowText,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PolzaChat":        "💬 Polza Chat",
    "PolzaVision":      "👁️ Polza Vision",
    "PolzaTextToImage": "🎨 Polza Text‑to‑Image",
    "PolzaMedia": "🎬 Polza.ai Media",
    "PolzaShowText":    "📝 Polza Show Text",
}

WEB_DIRECTORY = "./web"

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
