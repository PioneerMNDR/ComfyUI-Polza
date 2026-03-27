"""
🖼️ PolzaMediaImage — Advanced image generation via /v1/media.

Supports all Polza.ai image models:
  • Seedream 3/4.5  • Nano Banana  • GPT Image  • Flux
  • Grok Imagine    • and many more

Features:
  • Text-to-Image
  • Image-to-Image (optional IMAGE input)
  • Aspect ratios, guidance scale, quality presets
  • Async generation with automatic polling
"""

from __future__ import annotations

import logging

import numpy as np
import torch
from PIL import Image

from .api import (
    resolve_api_key,
    media_create,
    images_from_generation,
    images_to_batch_tensor,
    extract_usage_info,
    tensor_to_b64,
    PolzaAPIError,
    get_model_options,
)

logger = logging.getLogger("PolzaAI")

# ── Dropdown constants ────────────────────────────────────────────────

# Default fallback media models (used if API is unreachable)
DEFAULT_MEDIA_MODELS = [
    ("seedream-3", "Seedream 3"),
    ("seedream-4-5", "Seedream 4.5"),
    ("nano-banana", "Nano Banana"),
    ("gpt-image-1", "GPT Image 1"),
    ("flux-1-1-ultra", "Flux 1.1 Ultra"),
    ("grok-2-image", "Grok 2 Image"),
]


# Lazy-loaded + cached model list (avoids HTTP at import time)
_cached_media_models: list | None = None


def get_media_models() -> list:
    """Load image media models from API, fallback to defaults on error.
    
    Caches result after first successful fetch to avoid repeated HTTP calls.
    Returns DEFAULT_MEDIA_MODELS immediately on any error (never blocks ComfyUI startup).
    """
    global _cached_media_models
    if _cached_media_models is not None:
        return _cached_media_models
    try:
        _cached_media_models = get_model_options(model_type="image")
    except Exception as e:
        logger.warning("Failed to fetch media models from API: %s. Using defaults.", e)
        _cached_media_models = DEFAULT_MEDIA_MODELS
    return _cached_media_models


ASPECT_RATIOS = [
    "1:1", "16:9", "9:16",
    "4:3", "3:4", "3:2", "2:3",
    "4:5", "5:4", "21:9", "auto",
]

QUALITIES = ["high", "medium", "basic"]

IMAGE_RESOLUTIONS = ["1K", "2K", "4K"]

OUTPUT_FORMATS = ["png", "jpeg", "webp"]


class PolzaMediaImage:
    """
    Advanced image generation via Polza.ai Media API.

    Supports text‑to‑image AND image‑to‑image (connect an IMAGE input).
    All generation is asynchronous with automatic status polling.
    """

    CATEGORY     = "🤖 Polza.ai"
    FUNCTION     = "execute"
    OUTPUT_NODE  = True

    RETURN_TYPES = ("IMAGE", "STRING", "FLOAT")
    RETURN_NAMES = ("images", "text_response", "cost_rub")

    DESCRIPTION = (
        "Продвинутая генерация изображений через Polza.ai Media API.\n"
        "Seedream · Nano Banana · GPT Image · Flux · Grok Imagine и др.\n"
        "Подключите IMAGE для img2img."
    )

    # ── Inputs ────────────────────────────────────────────────────────

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (get_media_models, {
                    "default": "seedream-3",
                    "tooltip": (
                        "ID модели: seedream-3, seedream-4-5, nano-banana, "
                        "gpt-image-1, flux-1-1-ultra, grok-2-image …"
                    ),
                }),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Describe the image…",
                    "dynamicPrompts": True,
                }),
            },
            "optional": {
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API‑ключ (пусто → env / config.json)",
                }),
                "image": ("IMAGE", {
                    "tooltip": "Входное изображение для img2img (необязательно)",
                }),
                "aspect_ratio": (ASPECT_RATIOS, {
                    "default": "1:1",
                    "tooltip": "Соотношение сторон",
                }),
                "quality": (QUALITIES, {
                    "default": "high",
                }),
                "image_resolution": (IMAGE_RESOLUTIONS, {
                    "default": "2K",
                    "tooltip": "Разрешение: 1K / 2K / 4K",
                }),
                "output_format": (OUTPUT_FORMATS, {
                    "default": "png",
                }),
                "max_images": ("INT", {
                    "default": 1,
                    "min": 1, "max": 6,
                    "tooltip": "Количество генерируемых изображений",
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0, "max": 2147483647,
                    "tooltip": "Seed (0 = случайный)",
                }),
                "guidance_scale": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0, "max": 30.0, "step": 0.5,
                    "tooltip": "CFG scale (0 = использовать default модели)",
                }),
                "strength": ("FLOAT", {
                    "default": 0.8,
                    "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": "Сила трансформации для img2img (0–1)",
                }),
                "is_enhance": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Улучшить промпт моделью (GPT‑Image‑1)",
                }),
                "enable_safety": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Включить проверку безопасности",
                }),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    # ── Main logic ────────────────────────────────────────────────────

    def execute(
        self,
        model: str,
        prompt: str,
        api_key: str = "",
        image: torch.Tensor | None = None,
        aspect_ratio: str = "1:1",
        quality: str = "high",
        image_resolution: str = "2K",
        output_format: str = "png",
        max_images: int = 1,
        seed: int = 0,
        guidance_scale: float = 0.0,
        strength: float = 0.8,
        is_enhance: bool = False,
        enable_safety: bool = True,
    ) -> dict:

        # ── resolve key ──────────────────────────────────────────────
        try:
            key = resolve_api_key(api_key)
        except ValueError as exc:
            return self._error(str(exc))

        if not prompt.strip():
            return self._error("❌ Промпт не может быть пустым")

        # ── build input object ───────────────────────────────────────
        media_input: dict = {
            "prompt":           prompt,
            "aspect_ratio":     aspect_ratio,
            "quality":          quality,
            "image_resolution": image_resolution,
            "output_format":    output_format,
            "max_images":       max_images,
            "enable_safety_checker": enable_safety,
        }

        if seed > 0:
            media_input["seed"] = seed

        if guidance_scale > 0:
            media_input["guidance_scale"] = guidance_scale

        if is_enhance:
            media_input["isEnhance"] = True

        # ── img2img: encode input image ──────────────────────────────
        if image is not None:
            b64_data = tensor_to_b64(image, fmt="PNG")
            media_input["images"] = [{
                "type":  "base64",
                "data":  f"data:image/png;base64,{b64_data}",
            }]
            media_input["strength"] = strength

        # ── call Media API ───────────────────────────────────────────
        try:
            data = media_create(key, model=model, input=media_input)
        except (PolzaAPIError, Exception) as exc:
            logger.error("PolzaMediaImage error: %s", exc)
            return self._error(f"❌ {exc}")

        # ── extract images ───────────────────────────────────────────
        pil_images = images_from_generation(data)

        if not pil_images:
            # Some models return a text response instead of / alongside images
            text_content = data.get("content", "")
            if text_content:
                return self._error(
                    f"⚠️ Модель вернула текст вместо изображения:\n{text_content[:500]}"
                )
            return self._error("❌ API не вернул изображений")

        batch_tensor = images_to_batch_tensor(pil_images)
        cost_rub, usage_summary = extract_usage_info(data)

        # ── optional text / reasoning from response ──────────────────
        text_response = data.get("content", "") or ""
        reasoning = data.get("reasoning_summary", "") or ""

        # ── warnings ─────────────────────────────────────────────────
        warnings = data.get("warnings") or []

        # ── UI feedback ──────────────────────────────────────────────
        count = batch_tensor.shape[0]
        h, w = batch_tensor.shape[1], batch_tensor.shape[2]
        ui_lines = [f"✅ {count} image{'s' if count > 1 else ''} · {w}×{h}"]
        ui_lines.append(f"📊 {usage_summary}")
        if reasoning:
            ui_lines.append(f"💭 {reasoning[:200]}")
        if text_response:
            ui_lines.append(f"📝 {text_response[:200]}")
        for warn in warnings:
            ui_lines.append(f"⚠️ {warn}")

        return {
            "ui":     {"text": ui_lines},
            "result": (batch_tensor, text_response, cost_rub),
        }

    # ── Error helper ─────────────────────────────────────────────────

    @staticmethod
    def _error(msg: str) -> dict:
        blank = torch.zeros(1, 64, 64, 3, dtype=torch.float32)
        return {"ui": {"text": [msg]}, "result": (blank, "", 0.0)}
