"""
🎬 PolzaMedia — Universal media generation via Polza.ai /v1/media API.

Supports ALL Polza.ai media models through a single node:
  🖼️ Images : Seedream 3/4.5 · Nano Banana · GPT Image · Flux · Grok Imagine …
  🎬 Video  : Veo 3.1 · Wan 2.5/2.6 · Kling 3.0 · Seedance · Sora …
  🔊 Audio  : ElevenLabs TTS · speech synthesis …
  🎵 Music  : Suno and other music-generation models

Features:
  • Text-to-Image / Image-to-Image  (batch via ComfyUI Batch Images)
  • Text-to-Video / Image-to-Video  (native VIDEO output)
  • Text-to-Speech (TTS)
  • Music generation
  • Async generation with automatic polling
  • Extra params via JSON for any parameter not exposed as a widget
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import List

import torch

try:
    import folder_paths
except ImportError:
    import sys
    # folder_paths is a ComfyUI built-in module; provide a dummy for static analysis
    class _FolderPathsDummy:
        @staticmethod
        def get_output_directory():
            return "./output"
    folder_paths = _FolderPathsDummy()
    sys.modules["folder_paths"] = folder_paths

from .api import (
    PolzaAPIError,
    download_media_file,
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
    global _cached_all_models
    if _cached_all_models is not None:
        return _cached_all_models

    collected: set[str] = set()
    for model_type in ("image", "video", "audio"):
        try:
            collected.update(get_model_options(model_type=model_type))
        except Exception as exc:
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
# ║  Video output helper                                             ║
# ╚═══════════════════════════════════════════════════════════════════╝

# Video file extensions we recognize
VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi", ".mkv")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")


def _classify_url(url: str) -> str:
    """Classify a media URL as 'video', 'audio', or 'image'."""
    lo = url.lower().split("?")[0]  # strip query params
    if any(lo.endswith(ext) for ext in VIDEO_EXTENSIONS):
        return "video"
    if any(lo.endswith(ext) for ext in AUDIO_EXTENSIONS):
        return "audio"
    return "image"


def _extract_media_urls(data: dict) -> List[str]:
    """Pull every ``url`` out of the ``data`` field of a response."""
    raw = data.get("data")
    if raw is None:
        return []
    items = [raw] if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    return [item["url"] for item in items if isinstance(item, dict) and item.get("url")]


def _save_video_to_output(url: str, api_key: str = "") -> dict:
    """
    Download a video URL and save it to ComfyUI's output directory.

    Returns a dict compatible with ComfyUI's video preview system:
        {"filename": ..., "subfolder": ..., "type": "output"}
    """
    # Determine file extension from URL
    lo = url.lower().split("?")[0]
    ext = ".mp4"  # default
    for candidate in VIDEO_EXTENSIONS:
        if lo.endswith(candidate):
            ext = candidate
            break

    # Generate unique filename
    filename = f"polza_video_{uuid.uuid4().hex[:12]}{ext}"
    subfolder = "polza_videos"

    # Ensure subfolder exists in output directory
    output_dir = folder_paths.get_output_directory()
    video_dir = os.path.join(output_dir, subfolder)
    os.makedirs(video_dir, exist_ok=True)

    filepath = os.path.join(video_dir, filename)

    # Download the video
    logger.info("PolzaMedia: downloading video to %s", filepath)
    download_media_file(url, filepath)
    logger.info("PolzaMedia: video saved (%d bytes)", os.path.getsize(filepath))

    return {
        "filename": filename,
        "subfolder": subfolder,
        "type": "output",
    }


def _save_audio_to_output(url: str, api_key: str = "") -> dict:
    """
    Download an audio URL and save it to ComfyUI's output directory.
    """
    lo = url.lower().split("?")[0]
    ext = ".mp3"
    for candidate in AUDIO_EXTENSIONS:
        if lo.endswith(candidate):
            ext = candidate
            break

    filename = f"polza_audio_{uuid.uuid4().hex[:12]}{ext}"
    subfolder = "polza_audio"

    output_dir = folder_paths.get_output_directory()
    audio_dir = os.path.join(output_dir, subfolder)
    os.makedirs(audio_dir, exist_ok=True)

    filepath = os.path.join(audio_dir, filename)

    logger.info("PolzaMedia: downloading audio to %s", filepath)
    download_media_file(url, filepath)
    logger.info("PolzaMedia: audio saved (%d bytes)", os.path.getsize(filepath))

    return {
        "filename": filename,
        "subfolder": subfolder,
        "type": "output",
    }


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Local helpers                                                   ║
# ╚═══════════════════════════════════════════════════════════════════╝

def _url_media_kind(url: str) -> str:
    kind = _classify_url(url)
    return {"video": "🎬 Video", "audio": "🔊 Audio"}.get(kind, "📎 File")


def _safe_tensor_to_b64(tensor: torch.Tensor, fmt: str = "PNG") -> str:
    """Encode a single-frame IMAGE tensor to base64.

    Accepts both [H, W, C] and [1, H, W, C] and always passes
    a properly-shaped [1, H, W, C] tensor to ``tensor_to_b64``.
    """
    if tensor.dim() == 3:
        tensor = tensor.unsqueeze(0)          # [H,W,C] → [1,H,W,C]
    elif tensor.dim() == 4 and tensor.shape[0] != 1:
        tensor = tensor[:1]                   # take first frame only
    return tensor_to_b64(tensor, fmt=fmt)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  PolzaMedia  —  universal media generation node                  ║
# ╚═══════════════════════════════════════════════════════════════════╝

class PolzaMedia:
    """
    Universal media generation via Polza.ai Media API ``/v1/media``.

    Outputs:
      • images  — IMAGE tensor for generated images (or empty 64×64 if none)
      • video   — VIDEO output: downloaded video file for ComfyUI preview/playback
      • audio   — AUDIO dict: downloaded audio file info
      • media_url — raw URL string (for chaining or external use)
      • media_id — generation task ID
      • text_response — any text content from the response
      • cost_rub — generation cost in rubles

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

    # Native VIDEO output uses the "VIDEO" type which ComfyUI frontend
    # knows how to preview. The format matches VHS / built-in video nodes.
    RETURN_TYPES = ("IMAGE", "VHS_VIDEO", "STRING", "STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("images", "video", "media_url", "media_id", "text_response", "cost_rub")

    DESCRIPTION = (
        "Универсальная генерация медиа через Polza.ai Media API.\n\n"
        "🖼️ Изображения · 🎬 Видео (нативный VIDEO выход) · 🔊 Аудио (TTS) · 🎵 Музыка\n\n"
        "Подключите IMAGE для img2img / img2vid.\n"
        "Для batch подключите через Batch Images (несколько фреймов → images[]).\n"
        "Любые параметры API — через extra_params_json."
    )

    # ── Inputs ────────────────────────────────────────────────────

    @classmethod
    def INPUT_TYPES(cls):
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
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API‑ключ Polza.ai (пусто → env POLZA_API_KEY / config.json)",
                }),
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

    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return float("nan")

    # ── Main ──────────────────────────────────────────────────────

    def execute(
        self,
        model: str,
        prompt: str,
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

        t0 = time.time()
        logger.info("PolzaMedia: execute start  model=%s", model)

        # ── 1. API key ──────────────────────────────────────────
        try:
            key = resolve_api_key(api_key)
        except ValueError as exc:
            return self._error(str(exc))

        if not prompt.strip():
            return self._error("❌ Промпт не может быть пустым")

        # ── 2. Build input dict (only non-default values) ────────
        inp: dict = {"prompt": prompt}

        if aspect_ratio != "auto":
            inp["aspect_ratio"] = aspect_ratio
        if seed > 0:
            inp["seed"] = seed
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
        if duration != "auto":
            inp["duration"] = duration
        if video_resolution != "auto":
            inp["resolution"] = video_resolution
        if sound:
            inp["sound"] = True
        if video_url.strip():
            inp["videos"] = [{"type": "url", "data": video_url.strip()}]
        if voice.strip():
            inp["voice"] = voice.strip()
        if speed != 1.0:
            inp["speed"] = speed
        if language_code.strip():
            inp["language_code"] = language_code.strip()

        # ── 3. Encode batch IMAGE input ──────────────────────────
        if image is not None:
            img_4d = image if image.dim() == 4 else image.unsqueeze(0)
            batch_count = img_4d.shape[0]
            encoded: list[dict] = []

            logger.info(
                "PolzaMedia: encoding %d frame(s) from tensor %s",
                batch_count, list(img_4d.shape),
            )

            for i in range(batch_count):
                frame = img_4d[i]                             # [H, W, C]
                b64 = _safe_tensor_to_b64(frame, fmt="PNG")   # ← fixed helper
                encoded.append({
                    "type": "base64",
                    "data": f"data:image/png;base64,{b64}",
                })
                logger.debug(
                    "  frame %d: b64 length=%d chars", i, len(b64),
                )

            inp["images"] = encoded
            inp["strength"] = strength
            logger.info(
                "PolzaMedia: attached %d image(s), b64 total ≈%.1f KB",
                len(encoded),
                sum(len(e["data"]) for e in encoded) / 1024,
            )

        # ── 4. Merge extra JSON params ───────────────────────────
        if extra_params_json.strip():
            try:
                extra = json.loads(extra_params_json)
            except json.JSONDecodeError as exc:
                return self._error(f"❌ Невалидный JSON в extra_params_json: {exc}")
            if not isinstance(extra, dict):
                return self._error(
                    "❌ extra_params_json должен быть JSON-объектом {}, а не массивом/скаляром"
                )
            inp.update(extra)
            logger.info("PolzaMedia: merged extra keys: %s", list(extra.keys()))

        # ── 5. Log final payload (without base64 blobs) ──────────
        log_inp = {
            k: (f"<{len(v)} items>" if k == "images" else v)
            for k, v in inp.items()
        }
        logger.info("PolzaMedia: calling media_create  model=%s  input=%s", model, log_inp)

        # ── 6. Call Media API ────────────────────────────────────
        try:
            data = media_create(key, model=model, input=inp)
        except PolzaAPIError as exc:
            logger.error("PolzaMedia: API error → %s", exc)
            return self._error(f"❌ API [{exc.status_code}]: {exc.message}")
        except Exception as exc:
            logger.exception("PolzaMedia: unexpected error during media_create")
            return self._error(f"❌ Unexpected: {exc}")

        elapsed = time.time() - t0
        status = data.get("status", "?")
        logger.info(
            "PolzaMedia: response received  status=%s  id=%s  elapsed=%.1fs",
            status, data.get("id", "?"), elapsed,
        )

        # ── 7. Log full response (debug level, for diagnostics) ──
        logger.debug("PolzaMedia: full response → %s", json.dumps(data, default=str)[:2000])

        # ── 8. Check for API-level failure ───────────────────────
        if status == "failed":
            err_obj = data.get("error", {})
            err_msg = (
                err_obj.get("message", "Неизвестная ошибка")
                if isinstance(err_obj, dict)
                else str(err_obj)
            )
            logger.error("PolzaMedia: generation failed → %s", err_msg)
            return self._error(f"❌ Генерация не удалась: {err_msg}")

        # ── 9. Parse response ────────────────────────────────────
        pil_images    = images_from_generation(data)
        media_urls    = _extract_media_urls(data)
        media_url_str = "\n".join(media_urls)
        media_id      = data.get("id", "")
        text_response = data.get("content", "") or ""
        reasoning     = data.get("reasoning_summary", "") or ""
        cost_rub, usage_summary = extract_usage_info(data)
        warnings = data.get("warnings") or []

        logger.info(
            "PolzaMedia: parsed → %d PIL images, %d media URLs, "
            "text=%d chars, cost=%.4f₽, elapsed=%.1fs",
            len(pil_images), len(media_urls),
            len(text_response), cost_rub, elapsed,
        )

        # ── 10. Classify media URLs and download video/audio ─────
        video_results: list[dict] = []
        audio_results: list[dict] = []

        for url in media_urls:
            kind = _classify_url(url)
            if kind == "video":
                try:
                    video_info = _save_video_to_output(url)
                    video_results.append(video_info)
                    logger.info("PolzaMedia: saved video → %s", video_info["filename"])
                except Exception as exc:
                    logger.error("PolzaMedia: failed to download video %s: %s", url, exc)
            elif kind == "audio":
                try:
                    audio_info = _save_audio_to_output(url)
                    audio_results.append(audio_info)
                    logger.info("PolzaMedia: saved audio → %s", audio_info["filename"])
                except Exception as exc:
                    logger.error("PolzaMedia: failed to download audio %s: %s", url, exc)

        # ── 11. Build image tensor ───────────────────────────────
        if pil_images:
            batch_tensor = images_to_batch_tensor(pil_images)
            logger.info(
                "PolzaMedia: image tensor shape=%s", list(batch_tensor.shape),
            )
        else:
            batch_tensor = torch.zeros(1, 64, 64, 3, dtype=torch.float32)

        # ── 12. Build video output ───────────────────────────────
        # VHS_VIDEO format: tuple of (file_info_list,) or None
        # The VHS (Video Helper Suite) standard expects:
        #   (filenames: list[str], subfolder: str, type: str)
        # But the most common format is just the file path info
        if video_results:
            # Return the first video in VHS-compatible format
            vr = video_results[0]
            video_output = {
                "filename": vr["filename"],
                "subfolder": vr["subfolder"],
                "type": vr["type"],
            }
        else:
            video_output = None

        # ── 13. Check if we got anything ─────────────────────────
        if not pil_images and not video_results and not audio_results and not text_response:
            logger.warning(
                "PolzaMedia: no images, no video, no audio, no text in response!"
            )
            logger.warning(
                "PolzaMedia: response keys=%s  data field=%s",
                list(data.keys()),
                repr(data.get("data"))[:500],
            )
            return self._error(
                "❌ API не вернул ни изображений, ни видео, ни аудио, ни текста.\n"
                f"status={status}  id={media_id}\n"
                f"Response keys: {list(data.keys())}"
            )

        # ── 14. UI feedback lines ────────────────────────────────
        ui: dict = {"text": []}
        ui_lines: list[str] = ui["text"]

        if pil_images:
            n = len(pil_images)
            h, w = batch_tensor.shape[1], batch_tensor.shape[2]
            ui_lines.append(f"✅ {n} image{'s' if n > 1 else ''} · {w}×{h}")

        # Add video previews to UI
        if video_results:
            ui["videos"] = video_results
            for vr in video_results:
                ui_lines.append(f"🎬 Video: {vr['filename']}")

        # Add audio info to UI
        if audio_results:
            ui["audio"] = audio_results
            for ar in audio_results:
                ui_lines.append(f"🔊 Audio: {ar['filename']}")

        if media_id:
            ui_lines.append(f"🆔 {media_id}")
        ui_lines.append(f"📊 {usage_summary}")
        ui_lines.append(f"⏱ {elapsed:.1f}s")

        if reasoning:
            ui_lines.append(f"💭 {reasoning[:200]}")
        if text_response:
            ui_lines.append(f"📝 {text_response[:300]}")
        for warn in warnings:
            ui_lines.append(f"⚠️ {warn}")

        if not ui_lines:
            ui_lines.append("✅ Генерация завершена")

        # ── log the same info to console ─────────────────────────
        for line in ui_lines:
            logger.info("PolzaMedia UI: %s", line)

        return {
            "ui":     ui,
            "result": (
                batch_tensor,
                video_output,
                media_url_str,
                media_id,
                text_response,
                cost_rub,
            ),
        }

    # ── Error helper ─────────────────────────────────────────────

    @staticmethod
    def _error(msg: str) -> dict:
        logger.error("PolzaMedia: %s", msg)
        blank = torch.zeros(1, 64, 64, 3, dtype=torch.float32)
        return {
            "ui":     {"text": [msg]},
            "result": (blank, None, "", "", "", 0.0),
        }