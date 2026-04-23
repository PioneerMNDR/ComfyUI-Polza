"""
🎨 PolzaTextToImage — OpenAI-compatible image generation.

Uses POST /v2/images/generations.
Supports: gpt-image-1, dall-e-3, dall-e-2 and compatible models.
"""

from __future__ import annotations

import logging

from .api import (
    get_cached_or_placeholder_model_options,
    resolve_api_key,
    image_generation,
    images_from_generation,
    images_to_batch_tensor,
    extract_usage_info,
    PolzaAPIError,
    UNLOADED_MODEL_OPTION,
    is_unloaded_model_option,
)

logger = logging.getLogger("PolzaAI")

# ── Dropdown constants ────────────────────────────────────────────────

# Default fallback T2I models (used if API is unreachable)
DEFAULT_T2I_MODELS = [
    "gpt-image-1",
    "dall-e-3",
    "dall-e-2",
]


def get_t2i_models() -> list[str]:
    """Return runtime-loaded models, or a placeholder before the first load."""
    return get_cached_or_placeholder_model_options("t2i")


SIZES = [
    "auto",
    "1024x1024",
    "1792x1024",
    "1024x1792",
    "1536x1024",
    "1024x1536",
    "512x512",
    "256x256",
]

QUALITIES = ["auto", "high", "medium", "low", "hd", "standard"]

STYLES = ["vivid", "natural"]

OUTPUT_FORMATS = ["png", "jpeg", "webp"]

BACKGROUNDS = ["auto", "opaque", "transparent"]


class PolzaTextToImage:
    """
    Generate images via Polza.ai (OpenAI-compatible endpoint).

    Supported models:
      • gpt-image-1  — GPT Image (OpenAI)
      • dall-e-3      — DALL·E 3
      • dall-e-2      — DALL·E 2

    Synchronous generation up to ~120 s, then automatic async polling.
    """

    CATEGORY     = "🤖 Polza.ai"
    FUNCTION     = "execute"
    OUTPUT_NODE  = True

    RETURN_TYPES = ("IMAGE", "STRING", "FLOAT")
    RETURN_NAMES = ("images", "revised_prompt", "cost_rub")

    DESCRIPTION = (
        "Генерация изображений через OpenAI-совместимый API Polza.ai.\n"
        "gpt-image-1 · dall-e-3 · dall-e-2"
    )

    # ── Inputs ────────────────────────────────────────────────────────

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (get_t2i_models(), {
                    "default": "gpt-image-1",
                    "tooltip": "gpt-image-1, dall-e-3, dall-e-2",
                }),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Describe the image…",
                    "dynamicPrompts": True,
                    "tooltip": "Текстовое описание изображения (до 32 000 символов для gpt-image-1)",
                }),
            },
            "optional": {
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API‑ключ Polza.ai  (пусто → env / config.json)",
                }),
                "size": (SIZES, {
                    "default": "1024x1024",
                    "tooltip": "Размер изображения",
                }),
                "quality": (QUALITIES, {
                    "default": "auto",
                    "tooltip": "auto / high / medium / low / hd / standard",
                }),
                "style": (STYLES, {
                    "default": "vivid",
                    "tooltip": "Стиль (vivid / natural) — только DALL·E 3",
                }),
                "n": ("INT", {
                    "default": 1,
                    "min": 1, "max": 10,
                    "tooltip": "Количество изображений (для DALL·E 3 только 1)",
                }),
                "output_format": (OUTPUT_FORMATS, {
                    "default": "png",
                    "tooltip": "Формат выхода (gpt-image-1)",
                }),
                "background": (BACKGROUNDS, {
                    "default": "auto",
                    "tooltip": "Фон: transparent / opaque / auto (gpt-image-1)",
                }),
                "output_compression": ("INT", {
                    "default": 100,
                    "min": 0, "max": 100, "step": 5,
                    "tooltip": "Сжатие 0–100 (gpt-image-1)",
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
        size: str = "1024x1024",
        quality: str = "auto",
        style: str = "vivid",
        n: int = 1,
        output_format: str = "png",
        background: str = "auto",
        output_compression: int = 100,
    ) -> dict:

        # ── resolve key ──────────────────────────────────────────────
        try:
            key = resolve_api_key(api_key)
        except ValueError as exc:
            return self._error(str(exc))

        if is_unloaded_model_option(model):
            return self._error("Click Load models first and choose a model")

        if not prompt.strip():
            return self._error("❌ Промпт не может быть пустым")

        # ── build params ─────────────────────────────────────────────
        params: dict = {
            "model":           model,
            "prompt":          prompt,
            "n":               n,
            "size":            size,
            "quality":         quality,
            "response_format": "url",
        }

        # DALL-E 3 specific
        if "dall-e-3" in model.lower():
            params["style"] = style

        # gpt-image-1 specific
        if "gpt-image" in model.lower():
            params["output_format"] = output_format
            if background != "auto":
                params["background"] = background
            if output_compression < 100:
                params["output_compression"] = output_compression

        # ── call API ─────────────────────────────────────────────────
        try:
            data = image_generation(key, **params)
        except (PolzaAPIError, Exception) as exc:
            logger.error("PolzaTextToImage error: %s", exc)
            return self._error(f"❌ {exc}")

        # ── extract images ───────────────────────────────────────────
        pil_images = images_from_generation(data)

        if not pil_images:
            return self._error("❌ API вернул ответ без изображений")

        batch_tensor = images_to_batch_tensor(pil_images)
        cost_rub, usage_summary = extract_usage_info(data)

        # ── revised prompt (DALL-E 3) ────────────────────────────────
        revised = ""
        data_items = data.get("data") or []
        if data_items and isinstance(data_items[0], dict):
            revised = data_items[0].get("revised_prompt", "")

        # ── UI feedback ──────────────────────────────────────────────
        count = batch_tensor.shape[0]
        h, w = batch_tensor.shape[1], batch_tensor.shape[2]
        ui_lines = [
            f"✅ {count} image{'s' if count > 1 else ''} · {w}×{h}",
            f"📊 {usage_summary}",
        ]
        if revised:
            ui_lines.append(f"📝 {revised[:200]}{'…' if len(revised) > 200 else ''}")

        return {
            "ui":     {"text": ui_lines},
            "result": (batch_tensor, revised, cost_rub),
        }

    # ── Error helper ─────────────────────────────────────────────────

    @staticmethod
    def _error(msg: str) -> dict:
        import torch
        blank = torch.zeros(1, 64, 64, 3, dtype=torch.float32)
        return {"ui": {"text": [msg]}, "result": (blank, "", 0.0)}
