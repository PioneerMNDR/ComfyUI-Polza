"""
ComfyUI Polza.ai — unified access to 300+ AI models.
Text, Vision, Image Generation via https://polza.ai
"""

from __future__ import annotations

import logging

from aiohttp import web

try:
    from server import PromptServer
except Exception:  # pragma: no cover - ComfyUI-only import
    PromptServer = None

from .nodes_chat import PolzaChat
from .nodes_vision import PolzaVision
from .nodes_t2i import PolzaTextToImage
from .nodes_media_image import PolzaMedia
from .nodes_utils import PolzaShowText
from .api import PolzaAPIError, get_model_options, set_runtime_model_options

logger = logging.getLogger("PolzaAI")

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
    "PolzaMedia":        "🎬 Polza Media",
    "PolzaShowText":    "📝 Polza Show Text",
}

WEB_DIRECTORY = "./web"


def _fetch_media_models(api_key: str = "") -> list[str]:
    collected: set[str] = set()
    for model_type in ("image", "video", "audio", "tts", "stt"):
        try:
            collected.update(get_model_options(model_type=model_type, api_key=api_key))
        except Exception as exc:
            logger.warning("Polza media model fetch failed for '%s': %s", model_type, exc)
    return sorted(collected, key=str.lower)


def _load_models_for_scope(scope: str, api_key: str = "") -> list[str]:
    if scope == "chat":
        return get_model_options(model_type="chat", api_key=api_key)
    if scope == "vision":
        return get_model_options(
            model_type="chat",
            require_input_modality="image",
            api_key=api_key,
        )
    if scope == "t2i":
        return get_model_options(model_type="image", api_key=api_key)
    if scope == "media":
        return _fetch_media_models(api_key=api_key)
    raise ValueError(f"Unknown Polza model scope: {scope}")


if PromptServer is not None and getattr(PromptServer, "instance", None) is not None:
    if not getattr(PromptServer.instance, "_polza_models_route_registered", False):

        @PromptServer.instance.routes.post("/polza/models")
        async def polza_models_route(request):
            try:
                payload = await request.json()
            except Exception:
                payload = {}

            scope = str(payload.get("scope", "")).strip().lower()
            api_key = str(payload.get("api_key", "")).strip()

            if not scope:
                return web.json_response({"error": "Missing scope"}, status=400)

            try:
                models = _load_models_for_scope(scope, api_key=api_key)
            except ValueError as exc:
                return web.json_response({"error": str(exc)}, status=400)
            except PolzaAPIError as exc:
                return web.json_response(
                    {"error": exc.message, "status_code": exc.status_code},
                    status=exc.status_code,
                )
            except Exception as exc:
                logger.exception("Failed to load Polza models for scope '%s'", scope)
                return web.json_response({"error": str(exc)}, status=500)

            if not models:
                return web.json_response({"error": "No models returned"}, status=404)

            set_runtime_model_options(scope, models)

            return web.json_response({"models": models, "scope": scope})

        PromptServer.instance._polza_models_route_registered = True

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
