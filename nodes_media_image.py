"""
🎬 PolzaMedia — Universal media generation via Polza.ai /v1/media API.

Supports ALL Polza.ai media models through a single node:
  🖼️ Images : Seedream 3/4.5 · Nano Banana · GPT Image · Flux · Grok Imagine …
  🎬 Video  : Veo 3.1 · Wan 2.5/2.6 · Kling 3.0 · Seedance · Sora …
  🔊 Audio  : ElevenLabs TTS · speech synthesis …
  🎵 Music  : Suno and other music-generation models

Features:
  • Text-to-Image / Image-to-Image  (batch via ComfyUI Batch Images)
  • Text-to-Video / Image-to-Video
  • Text-to-Speech (TTS)
  • Music generation
  • Async generation with automatic polling
  • Extra params via JSON for any parameter not exposed as a widget
"""

from __future__ import annotations

import json
import logging
from typing import List

import torch

from .api import (
    PolzaAPIError,
    extract_usage_info,
    get_model_options,
    images_from_generation,
    images_to_batch_tensor,
    media_create,
    resolve_api_key,
    tensor_to_b64,
)

logger = logging.getLogger("PolzaAI")


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Model list (lazy-loaded, cached)                                ║
# ╚═══════════════════════════════════════════════════════════════════╝

DEFAULT_ALL_MEDIA_MODELS: list[str] = [
    # Images
    "seedream-3",
    "seedream-4-5",
    "nano-banana",
    "gpt-image-1",
    "flux-1-1-ultra",
    "grok-2-image",
    # Video
    "veo-3",
    "veo-3-1",
    "wan-2-6",
    "kling-3-0",
    "seedance-1-0",
    "sora",
    # Audio / TTS
    "elevenlabs-tts-turbo",
]

_cached_all_models: list[str] | None = None


def _get_all_media_models() -> list[str]:
    """Fetch image + video + audio models from the API; fall back to defaults.

    Result is cached after the first successful (or failed) attempt so that
    ComfyUI startup is never blocked by a slow/unavailable network.
    """
    global _cached_all_models
    if _cached_all_models is not None:
        return _cached_all_models

    collected: set[str] = set()
    for model_type in ("image", "video", "audio"):
        try:
            collected.update(get_model_options(model_type=model_type))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch %s models: %s", model_type, exc)

    _cached_all_models = (
        sorted(collected, key=str.lower) if collected else list(DEFAULT_ALL_MEDIA_MODELS)
    )
    return _cached_all_models


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Dropdown value lists                                            ║
# ╚═══════════════════════════════════════════════════════════════════╝

ASPECT_RATIOS = [
    "auto", "1:1", "16:9", "9:16",
    "4:3", "3:4", "3:2", "2:3",
    "4:5", "5:4", "21:9",
]

QUALITIES          = ["auto", "high", "medium", "basic"]
IMAGE_RESOLUTIONS  = ["auto", "1K", "2K", "4K"]
OUTPUT_FORMATS     = ["png", "jpeg", "webp"]
DURATIONS          = ["auto", "5s", "10s", "15s"]
VIDEO_RESOLUTIONS  = ["auto", "480p", "580p", "720p", "1080p"]


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Local helpers                                                   ║
# ╚═══════════════════════════════════════════════════════════════════╝

def _extract_media_urls(data: dict) -> List[str]:
    """Pull every ``url`` value out of the ``data`` field of a response.

    Works regardless of whether ``data`` is a single dict or a list of dicts.
    """
    raw = data.get("data")
    if raw is None:
        return []
    items = [raw] if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    return [item["url"] for item in items if isinstance(item, dict) and item.get("url")]


def _url_media_kind(url: str) -> str:
    """Guess 🎬/🔊/📎 prefix from a URL extension."""
    lo = url.lower()
    if any(ext in lo for ext in (".mp4", ".webm", ".mov", ".avi")):
        return "🎬 Video"
    if any(ext in lo for ext in (".mp3", ".wav", ".ogg", ".flac", ".aac")):
        return "🔊 Audio"
    return "📎 File"


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  PolzaMedia  —  universal media generation node                  ║
# ╚═══════════════════════════════════════════════════════════════════╝

class PolzaMedia:
    """
    Universal media generation via Polza.ai Media API ``/v1/media``.

    * Connect an **IMAGE** input for img2img / img2vid.
      Batch is fully supported — every frame in ``[B, H, W, 3]``
      becomes a separate element of the ``images[]`` array sent to the API.
    * For vid2vid supply a ``video_url``.
    * Any parameter not exposed as a widget can be passed through
      ``extra_params_json`` (merged into the ``input`` object).
    """

    CATEGORY    = "🤖 Polza.ai"
    FUNCTION    = "execute"
    OUTPUT_NODE = True

    # -- outputs --
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("images", "media_url", "media_id", "text_response", "cost_rub")

    DESCRIPTION = (
        "Универсальная генерация медиа через Polza.ai Media API.\n\n"
        "🖼️ Изображения · 🎬 Видео · 🔊 Аудио (TTS) · 🎵 Музыка\n\n"
        "Подключите IMAGE для img2img / img2vid.\n"
        "Для batch подключите через Batch Images (несколько фреймов → images[]).\n"
        "Любые параметры API — через extra_params_json."
    )

    # ── Inputs ────────────────────────────────────────────────────

    @classmethod
    def INPUT_TYPES(cls):  # noqa: N802
        return {
            "required": {
                "model": (_get_all_media_models(), {
                    "default": "seedream-3",
                    "tooltip": (
                        "ID модели Polza.ai.\n"
                        "Изображения: seedream-3, gpt-image-1, flux-1-1-ultra …\n"
                        "Видео: veo-3-1, wan-2-6, kling-3-0, sora …\n"
                        "Аудио: elevenlabs-tts-turbo …"
                    ),
                }),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Опишите, что нужно сгенерировать…",
                    "dynamicPrompts": True,
                }),
            },
            "optional": {
                # ── Auth ────────────────────────────────────────
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API‑ключ Polza.ai (пусто → env POLZA_API_KEY / config.json)",
                }),

                # ── Reference media ─────────────────────────────
                "image": ("IMAGE", {
                    "tooltip": (
                        "Входное изображение для img2img / img2vid / editing.\n"
                        "Batch поддерживается: каждый фрейм [B,H,W,3]\n"
                        "кодируется отдельным элементом images[]."
                    ),
                }),
                "video_url": ("STRING", {
                    "default": "",
                    "tooltip": "URL видео для video-to-video генерации.",
                }),

                # ── Common ──────────────────────────────────────
                "aspect_ratio": (ASPECT_RATIOS, {
                    "default": "auto",
                    "tooltip": "Соотношение сторон (изображения / видео).",
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 2_147_483_647,
                    "tooltip": "Seed для воспроизводимости (0 = случайный).",
                }),

                # ── Image ───────────────────────────────────────
                "quality": (QUALITIES, {
                    "default": "auto",
                    "tooltip": "Качество изображения (auto = default модели).",
                }),
                "image_resolution": (IMAGE_RESOLUTIONS, {
                    "default": "auto",
                    "tooltip": "Разрешение: 1K / 2K / 4K.",
                }),
                "output_format": (OUTPUT_FORMATS, {
                    "default": "png",
                }),
                "max_images": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 6,
                    "tooltip": "Количество генерируемых изображений (1–6).",
                }),
                "guidance_scale": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 30.0,
                    "step": 0.5,
                    "tooltip": "CFG scale (0 = default модели).",
                }),
                "strength": ("FLOAT", {
                    "default": 0.8,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": "Сила трансформации для img2img (0–1).",
                }),
                "is_enhance": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Улучшить промпт моделью (GPT‑Image‑1).",
                }),
                "enable_safety": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Проверка безопасности контента.",
                }),

                # ── Video ───────────────────────────────────────
                "duration": (DURATIONS, {
                    "default": "auto",
                    "tooltip": "Длительность видео.",
                }),
                "video_resolution": (VIDEO_RESOLUTIONS, {
                    "default": "auto",
                    "tooltip": "Разрешение видео.",
                }),
                "sound": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Генерация звука в видео (Kling 2.6 / 3.0).",
                }),

                # ── Audio / TTS ─────────────────────────────────
                "voice": ("STRING", {
                    "default": "",
                    "tooltip": "Голос для TTS (напр. Rachel, Josh).",
                }),
                "speed": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.7,
                    "max": 1.2,
                    "step": 0.05,
                    "tooltip": "Скорость речи (0.7–1.2).",
                }),
                "language_code": ("STRING", {
                    "default": "",
                    "tooltip": "Код языка ISO 639‑1 (напр. ru, en). Только Turbo 2.5.",
                }),

                # ── Advanced ────────────────────────────────────
                "extra_params_json": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": '{"watermark":"Brand","mode":"pro","instrumental":true}',
                    "tooltip": (
                        "Дополнительные параметры в формате JSON.\n"
                        "Мерджатся в input‑объект запроса.\n"
                        "Перекрывают одноимённые виджеты."
                    ),
                }),
            },
        }

    # ── Always re-execute ─────────────────────────────────────────

    @classmethod
    def IS_CHANGED(cls, **_kwargs):  # noqa: N802
        return float("nan")

    # ── Main ──────────────────────────────────────────────────────

    def execute(  # noqa: C901, PLR0912, PLR0913, PLR0915
        self,
        model: str,
        prompt: str,
        # optional ↓
        api_key: str = "",
        image: torch.Tensor | None = None,
        video_url: str = "",
        aspect_ratio: str = "auto",
        seed: int = 0,
        quality: str = "auto",
        image_resolution: str = "auto",
        output_format: str = "png",
        max_images: int = 1,
        guidance_scale: float = 0.0,
        strength: float = 0.8,
        is_enhance: bool = False,
        enable_safety: bool = True,
        duration: str = "auto",
        video_resolution: str = "auto",
        sound: bool = False,
        voice: str = "",
        speed: float = 1.0,
        language_code: str = "",
        extra_params_json: str = "",
    ) -> dict:
        # ── 1. API key ──────────────────────────────────────────
        try:
            key = resolve_api_key(api_key)
        except ValueError as exc:
            return self._error(str(exc))

        if not prompt.strip():
            return self._error("❌ Промпт не может быть пустым")

        # ── 2. Build input dict (only non-default values) ────────
        inp: dict = {"prompt": prompt}

        # -- common ---------------------------------------------------
        if aspect_ratio != "auto":
            inp["aspect_ratio"] = aspect_ratio
        if seed > 0:
            inp["seed"] = seed

        # -- image ----------------------------------------------------
        if quality != "auto":
            inp["quality"] = quality
        if image_resolution != "auto":
            inp["image_resolution"] = image_resolution
        if output_format != "png":
            inp["output_format"] = output_format
        if max_images > 1:
            inp["max_images"] = max_images
        if guidance_scale > 0:
            inp["guidance_scale"] = guidance_scale
        if is_enhance:
            inp["isEnhance"] = True
        if not enable_safety:
            inp["enable_safety_checker"] = False

        # -- video ----------------------------------------------------
        if duration != "auto":
            inp["duration"] = duration
        if video_resolution != "auto":
            inp["resolution"] = video_resolution
        if sound:
            inp["sound"] = True
        if video_url.strip():
            inp["videos"] = [{"type": "url", "data": video_url.strip()}]

        # -- audio / tts ----------------------------------------------
        if voice.strip():
            inp["voice"] = voice.strip()
        if speed != 1.0:
            inp["speed"] = speed
        if language_code.strip():
            inp["language_code"] = language_code.strip()

        # ── 3. Encode batch IMAGE input ──────────────────────────
        if image is not None:
            img_4d = image if image.dim() == 4 else image.unsqueeze(0)
            encoded: list[dict] = []
            for i in range(img_4d.shape[0]):
                b64 = tensor_to_b64(img_4d[i], fmt="PNG")
                encoded.append({
                    "type": "base64",
                    "data": f"data:image/png;base64,{b64}",
                })
            inp["images"] = encoded
            inp["strength"] = strength
            logger.info(
                "PolzaMedia: attached %d image(s) from batch tensor %s",
                len(encoded),
                list(image.shape),
            )

        # ── 4. Merge extra JSON params ───────────────────────────
        if extra_params_json.strip():
            try:
                extra = json.loads(extra_params_json)
            except json.JSONDecodeError as exc:
                return self._error(f"❌ Невалидный JSON в extra_params_json: {exc}")
            if not isinstance(extra, dict):
                return self._error(
                    "❌ extra_params_json должен быть JSON-объектом { }, а не массивом/скаляром"
                )
            inp.update(extra)

        # ── 5. Call Media API ────────────────────────────────────
        try:
            data = media_create(key, model=model, input=inp)
        except PolzaAPIError as exc:
            return self._error(f"❌ API: {exc}")
        except Exception as exc:
            logger.exception("PolzaMedia unexpected error")
            return self._error(f"❌ {exc}")

        # ── 6. Parse response ────────────────────────────────────
        #   images → tensor;  any media → url list
        pil_images   = images_from_generation(data)
        batch_tensor = (
            images_to_batch_tensor(pil_images)
            if pil_images
            else torch.zeros(1, 64, 64, 3, dtype=torch.float32)
        )

        media_urls = _extract_media_urls(data)
        media_url  = "\n".join(media_urls)
        media_id   = data.get("id", "")

        text_response = data.get("content", "") or ""
        reasoning     = data.get("reasoning_summary", "") or ""
        cost_rub, usage_summary = extract_usage_info(data)
        warnings = data.get("warnings") or []

        # ── 7. UI feedback lines ─────────────────────────────────
        ui: list[str] = []

        if pil_images:
            n = len(pil_images)
            h, w = batch_tensor.shape[1], batch_tensor.shape[2]
            ui.append(f"✅ {n} image{'s' if n > 1 else ''} · {w}×{h}")

        # URLs for non-image media (video / audio) — or image URLs
        # when PIL decoding failed (e.g. WEBP from CDN)
        for url in media_urls:
            kind = _url_media_kind(url)
            # Don't duplicate image URLs already shown above
            if pil_images and kind == "📎 File":
                continue
            ui.append(f"{kind}: {url}")

        if media_id:
            ui.append(f"🆔 {media_id}")
        ui.append(f"📊 {usage_summary}")

        if reasoning:
            ui.append(f"💭 {reasoning[:200]}")
        if text_response:
            ui.append(f"📝 {text_response[:300]}")
        for warn in warnings:
            ui.append(f"⚠️ {warn}")

        if not ui:
            ui.append("✅ Генерация завершена")

        return {
            "ui":     {"text": ui},
            "result": (batch_tensor, media_url, media_id, text_response, cost_rub),
        }

    # ── Error helper ─────────────────────────────────────────────

    @staticmethod
    def _error(msg: str) -> dict:
        blank = torch.zeros(1, 64, 64, 3, dtype=torch.float32)
        return {
            "ui":     {"text": [msg]},
            "result": (blank, "", "", "", 0.0),
        }