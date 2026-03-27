"""
👁️ PolzaVision — Multimodal (image + text) analysis node.
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Tuple

import numpy as np
import torch
from PIL import Image

from .api import resolve_api_key, chat_completion, extract_response, PolzaAPIError, get_model_options

logger = logging.getLogger("PolzaAI")

# Default fallback vision models (used if API is unreachable)
DEFAULT_VISION_MODELS = [
    ("openai/gpt-4o", "OpenAI GPT-4o"),
    ("openai/gpt-4o-mini", "OpenAI GPT-4o Mini"),
    ("anthropic/claude-sonnet-4-5-20250929", "Claude Sonnet 4"),
    ("anthropic/claude-3-5-sonnet", "Claude 3.5 Sonnet"),
    ("google/gemini-2.5-flash-preview", "Gemini 2.5 Flash"),
]


# Lazy-loaded + cached model list (avoids HTTP at import time)
_cached_vision_models: list | None = None


def get_vision_models() -> list:
    """Load vision-capable models from API, fallback to defaults on error.
    
    Caches result after first successful fetch to avoid repeated HTTP calls.
    Returns DEFAULT_VISION_MODELS immediately on any error (never blocks ComfyUI startup).
    """
    global _cached_vision_models
    if _cached_vision_models is not None:
        return _cached_vision_models
    try:
        models = get_model_options(model_type="chat")
        _cached_vision_models = models[:50] if len(models) > 50 else models
    except Exception as e:
        logger.warning("Failed to fetch vision models from API: %s. Using defaults.", e)
        _cached_vision_models = DEFAULT_VISION_MODELS
    return _cached_vision_models


def _tensor_to_data_uri(tensor: torch.Tensor) -> str:
    """Convert a ComfyUI IMAGE tensor [B,H,W,C] → PNG data URI."""
    if tensor.dim() == 4:
        tensor = tensor[0]
    arr = (tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


class PolzaVision:
    """
    Analyse images with vision‑capable models via Polza.ai.
    Accepts a ComfyUI IMAGE tensor + text prompt.
    """

    CATEGORY     = "🤖 Polza.ai"
    FUNCTION     = "execute"
    OUTPUT_NODE  = True

    RETURN_TYPES = ("STRING", "FLOAT", "INT")
    RETURN_NAMES = ("text",   "cost_rub", "total_tokens")

    DESCRIPTION = (
        "Мультимодальный анализ изображений через Polza.ai.\n"
        "Подключите IMAGE и задайте текстовый промпт."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "Опиши это изображение подробно.",
                    "placeholder": "Что нужно узнать об изображении?",
                    "dynamicPrompts": True,
                }),
            },
            "optional": {
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API‑ключ (пусто → env / config.json)",
                }),
                "model": (get_vision_models, {
                    "default": "openai/gpt-4o",
                    "tooltip": "Vision‑модель: openai/gpt-4o, anthropic/claude-sonnet-4-5-20250929, google/gemini-2.5-flash-preview …",
                }),
                "system_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Системный промпт…",
                }),
                "temperature": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0, "max": 2.0, "step": 0.05,
                }),
                "max_tokens": ("INT", {
                    "default": 2048,
                    "min": 1, "max": 128000, "step": 64,
                }),
                "detail": (["auto", "low", "high"], {
                    "default": "auto",
                    "tooltip": "Детализация изображения (low = быстрее/дешевле)",
                }),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def execute(
        self,
        image: torch.Tensor,
        prompt: str,
        api_key: str = "",
        model: str = "openai/gpt-4o",
        system_prompt: str = "",
        temperature: float = 1.0,
        max_tokens: int = 2048,
        detail: str = "auto",
    ) -> dict:

        try:
            key = resolve_api_key(api_key)
        except ValueError as exc:
            err = str(exc)
            return {"ui": {"text": [err]}, "result": (err, 0.0, 0)}

        # ── encode image(s) ──────────────────────────────────────────
        content: list[dict] = [{"type": "text", "text": prompt}]

        batch_size = image.shape[0] if image.dim() == 4 else 1
        for i in range(batch_size):
            frame = image[i : i + 1] if image.dim() == 4 else image.unsqueeze(0)
            uri = _tensor_to_data_uri(frame)
            content.append({
                "type": "image_url",
                "image_url": {"url": uri, "detail": detail},
            })

        # ── messages ─────────────────────────────────────────────────
        messages: list[dict] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": content})

        # ── call ─────────────────────────────────────────────────────
        params = {
            "model":       model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
            "stream":      False,
        }

        try:
            data = chat_completion(key, **params)
        except (PolzaAPIError, Exception) as exc:
            err = f"❌ {exc}"
            logger.error("Polza Vision error: %s", exc)
            return {"ui": {"text": [err]}, "result": (err, 0.0, 0)}

        text, _, cost_rub, total_tokens = extract_response(data)

        preview = text[:500] + ("…" if len(text) > 500 else "")
        ui_lines = [preview, f"\n📊 {total_tokens} tok · {cost_rub:.4f} ₽"]

        return {
            "ui":     {"text": ui_lines},
            "result": (text, cost_rub, total_tokens),
        }
