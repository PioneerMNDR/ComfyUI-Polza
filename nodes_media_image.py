"""
🎬 PolzaMedia — Universal media generation via Polza.ai /v1/media API.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
import uuid
from fractions import Fraction
from typing import List, Optional

from PIL import Image
import torch
import folder_paths

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

# ── Native VIDEO support (ComfyUI >= 0.3) ────────────────────────
try:
    from comfy_api.latest import InputImpl, Types

    _HAS_NATIVE_VIDEO = True
except ImportError:
    InputImpl = None
    Types = None
    _HAS_NATIVE_VIDEO = False

# ── ComfyUI video helpers ───────────────────────────────────────
try:
    import numpy as np

    def _video_tensor_to_images(video_tensor: torch.Tensor) -> list[np.ndarray]:
        """Convert VIDEO tensor [B,H,W,C] or [B,T,H,W,C] to list of RGB images."""
        if video_tensor.dim() == 5:
            video_tensor = video_tensor[0]
        elif video_tensor.dim() == 4:
            pass
        else:
            raise ValueError(f"Unexpected video tensor shape: {video_tensor.shape}")

        frames = []
        for t in range(video_tensor.shape[0]):
            frame = video_tensor[t].cpu().numpy()
            if frame.dtype != np.uint8:
                frame = (np.clip(frame, 0, 1) * 255).astype(np.uint8)
            frames.append(frame)
        return frames
except ImportError:
    np = None
    _video_tensor_to_images = None

logger = logging.getLogger("PolzaAI")


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Model list                                                      ║
# ╚═══════════════════════════════════════════════════════════════════╝

DEFAULT_ALL_MEDIA_MODELS: list[str] = [
    # Image
    "seedream-3", "seedream-4-5", "nano-banana", "gpt-image-1",
    "flux-1-1-ultra", "grok-2-image",
    # Video
    "veo-3", "veo-3-1", "wan-2-6", "kling-3-0", "seedance-1-0", "sora",
    # Audio / TTS / STT
    "elevenlabs-tts-turbo", "elevenlabs-tts-flash",
    "openai/gpt-audio",
]

# All model type categories that the /v1/media endpoint can handle
_MEDIA_MODEL_TYPES = ("image", "video", "audio", "tts", "stt")

_cached_all_models: list[str] | None = None


def _get_all_media_models() -> list[str]:
    """Fetch all media-capable models from the API (image + video + audio + tts + stt)."""
    global _cached_all_models
    if _cached_all_models is not None:
        return _cached_all_models

    collected: set[str] = set()
    for mt in _MEDIA_MODEL_TYPES:
        try:
            collected.update(get_model_options(model_type=mt))
        except Exception as exc:
            logger.warning("Failed to fetch '%s' models: %s", mt, exc)

    if collected:
        _cached_all_models = sorted(collected, key=str.lower)
    else:
        logger.warning("Could not fetch models from API, using defaults")
        _cached_all_models = list(DEFAULT_ALL_MEDIA_MODELS)

    logger.info("PolzaMedia: loaded %d models: %s", len(_cached_all_models),
                ", ".join(_cached_all_models[:10]) + ("…" if len(_cached_all_models) > 10 else ""))
    return _cached_all_models


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Dropdown values                                                 ║
# ╚═══════════════════════════════════════════════════════════════════╝

ASPECT_RATIOS       = ["auto","1:1","16:9","9:16","4:3","3:4","3:2","2:3","4:5","5:4","21:9"]
QUALITIES           = ["auto","high","medium","basic"]
IMAGE_RESOLUTIONS   = ["auto","1K","2K","4K"]
OUTPUT_FORMATS      = ["png","jpeg","webp"]
DURATIONS           = ["auto","5s","10s","15s"]
VIDEO_RESOLUTIONS   = ["auto","480p","580p","720p","1080p"]


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  URL classification                                              ║
# ╚═══════════════════════════════════════════════════════════════════╝

VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".avi", ".mkv")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")

# ── Model type detection ───────────────────────────────────────
VIDEO_MODEL_KEYWORDS = [
    "kling", "veo", "wan", "sora", "seedance", "minimax", "luma",
    "runway", "pika", "gen-3", "gen-4",
]
AUDIO_MODEL_KEYWORDS = [
    "elevenlabs", "tts", "stt", "whisper", "audio", "voice",
    "speech", "sound",
]


def _is_video_model(model: str) -> bool:
    """Return True if model is a video generation model."""
    model_lower = model.lower()
    return any(kw in model_lower for kw in VIDEO_MODEL_KEYWORDS)


def _is_audio_model(model: str) -> bool:
    """Return True if model is an audio generation model."""
    model_lower = model.lower()
    return any(kw in model_lower for kw in AUDIO_MODEL_KEYWORDS)


def _get_model_type(model: str) -> str:
    """
    Determine the model type for building the correct API input.
    
    Returns one of: "kling", "wan", "veo", "sora", "seedance", "audio", "image"
    """
    model_lower = model.lower()

    # Video models — specific types
    if "kling" in model_lower:
        return "kling"
    elif "wan" in model_lower:
        return "wan"
    elif "veo" in model_lower:
        return "veo"
    elif "sora" in model_lower:
        return "sora"
    elif "seedance" in model_lower:
        return "seedance"
    elif _is_video_model(model):
        return "video_generic"

    # Audio models
    elif _is_audio_model(model):
        return "audio"

    # Default — image
    return "image"


def _build_video_input(
    model: str,
    prompt: str,
    aspect_ratio: str,
    duration: str,
    video_resolution: str,
    sound: bool,
    multi_shots: bool,
    mode: str,
    image: torch.Tensor | None,
    strength: float,
) -> dict:
    """Строит input dict с учётом специфики каждой видео-модели."""

    inp: dict = {"prompt": prompt}
    model_type = _get_model_type(model)

    # ── Kling 3.0 ────────────────────────────────────────────
    if model_type == "kling":
        # duration — MUST be a string
        if duration in ("auto", "5s"):
            inp["duration"] = "5"
        elif duration == "10s":
            inp["duration"] = "10"
        else:
            inp["duration"] = "5"

        inp["mode"] = mode  # "std" или "pro"
        inp["sound"] = "true" if sound else "false"
        inp["aspect_ratio"] = aspect_ratio if aspect_ratio != "auto" else "16:9"

        if image is None:
            inp["images"] = []

    # ── Wan 2.5 / 2.6 ────────────────────────────────────────
    elif model_type == "wan":
        if duration in ("auto", "5s"):
            inp["duration"] = "5"
        elif duration == "10s":
            inp["duration"] = "10"
        elif duration == "15s":
            inp["duration"] = "10"
        else:
            inp["duration"] = "5"

        inp["resolution"] = video_resolution if video_resolution != "auto" else "720p"
        inp["multi_shots"] = "true" if multi_shots else "false"

        if image is None:
            inp["images"] = []

    # ── Veo 3 / 3.1 ──────────────────────────────────────────
    elif model_type == "veo":
        if aspect_ratio != "auto":
            inp["aspect_ratio"] = aspect_ratio
        if duration != "auto":
            inp["duration"] = duration

    # ── Sora ─────────────────────────────────────────────────
    elif model_type == "sora":
        if aspect_ratio != "auto":
            inp["aspect_ratio"] = aspect_ratio
        if duration != "auto":
            inp["duration"] = duration
        if video_resolution != "auto":
            inp["resolution"] = video_resolution

    # ── Seedance ─────────────────────────────────────────────
    elif model_type == "seedance":
        if aspect_ratio != "auto":
            inp["aspect_ratio"] = aspect_ratio
        if duration != "auto":
            inp["duration"] = duration

    # ── Generic video ────────────────────────────────────────
    else:
        if aspect_ratio != "auto":
            inp["aspect_ratio"] = aspect_ratio
        if duration != "auto":
            inp["duration"] = duration
        if video_resolution != "auto":
            inp["resolution"] = video_resolution

    return inp


def _classify_url(url: str) -> str:
    """Return 'video', 'audio', or 'image'."""
    lo = url.lower().split("?")[0]
    if any(lo.endswith(ext) for ext in VIDEO_EXTENSIONS):
        return "video"
    if any(lo.endswith(ext) for ext in AUDIO_EXTENSIONS):
        return "audio"
    return "image"


def _extract_media_urls(data: dict) -> List[str]:
    raw = data.get("data")
    if raw is None:
        return []
    items = [raw] if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
    return [item["url"] for item in items if isinstance(item, dict) and item.get("url")]


def _url_media_kind(url: str) -> str:
    return {"video": "🎬 Video", "audio": "🔊 Audio"}.get(_classify_url(url), "📎 File")


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Download helpers                                                ║
# ╚═══════════════════════════════════════════════════════════════════╝

def _download_video_to_temp(url: str) -> tuple[str, str]:
    lo = url.lower().split("?")[0]
    ext = ".mp4"
    for candidate in VIDEO_EXTENSIONS:
        if lo.endswith(candidate):
            ext = candidate
            break

    filename = f"polza_{uuid.uuid4().hex[:12]}{ext}"
    temp_dir = folder_paths.get_temp_directory()
    filepath = os.path.join(temp_dir, filename)

    logger.info("PolzaMedia: downloading video → %s", filepath)
    download_media_file(url, filepath)
    file_size = os.path.getsize(filepath)
    logger.info("PolzaMedia: video saved (%d bytes, %.1f MB)", file_size, file_size / 1048576)

    return filepath, filename


def _download_audio_to_temp(url: str) -> tuple[str, str]:
    lo = url.lower().split("?")[0]
    ext = ".mp3"
    for candidate in AUDIO_EXTENSIONS:
        if lo.endswith(candidate):
            ext = candidate
            break

    filename = f"polza_{uuid.uuid4().hex[:12]}{ext}"
    temp_dir = folder_paths.get_temp_directory()
    filepath = os.path.join(temp_dir, filename)

    logger.info("PolzaMedia: downloading audio → %s", filepath)
    download_media_file(url, filepath)
    logger.info("PolzaMedia: audio saved (%d bytes)", os.path.getsize(filepath))

    return filepath, filename


def _safe_tensor_to_b64(tensor: torch.Tensor, fmt: str = "PNG") -> str:
    if tensor.dim() == 3:
        tensor = tensor.unsqueeze(0)
    elif tensor.dim() == 4 and tensor.shape[0] != 1:
        tensor = tensor[:1]
    return tensor_to_b64(tensor, fmt=fmt)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  PolzaMedia node                                                 ║
# ╚═══════════════════════════════════════════════════════════════════╝

class PolzaMedia:
    """
    Universal media generation via Polza.ai /v1/media.

    Outputs:
      • images        — IMAGE tensor (batch) for generated images
      • video         — native VIDEO output → connects to SaveVideo / GetVideoComponents
      • audio         — AUDIO output → connects to PreviewAudio / SaveAudio
      • media_url     — raw URL(s) for any media type
      • media_id      — generation task ID
      • text_response — text content from the API response
      • cost_rub      — generation cost in rubles
    """

    CATEGORY    = "🤖 Polza.ai"
    FUNCTION    = "execute"
    OUTPUT_NODE = True

    RETURN_TYPES = ("IMAGE", "VIDEO", "AUDIO", "STRING", "STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("images", "video", "audio", "media_url", "media_id", "text_response", "cost_rub")

    DESCRIPTION = (
        "Универсальная генерация медиа через Polza.ai Media API.\n\n"
        "🖼️ Изображения · 🎬 Видео (нативный VIDEO → SaveVideo) · 🔊 Аудио (TTS → PreviewAudio)\n\n"
        "Выход «video» напрямую подключается к SaveVideo / GetVideoComponents.\n"
        "Выход «audio» подключается к PreviewAudio / SaveAudio.\n"
        "Подключите IMAGE для img2img / img2vid.\n"
        "Любые параметры API — через extra_params_json."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (_get_all_media_models(), {
                    "default": _get_all_media_models()[0] if _get_all_media_models() else "seedream-3",
                    "tooltip": (
                        "ID модели Polza.ai.\n"
                        "Изображения: seedream-3, gpt-image-1, flux-1-1-ultra …\n"
                        "Видео: veo-3-1, wan-2-6, kling-3-0, sora …\n"
                        "Аудио/TTS: elevenlabs-tts-turbo, openai/gpt-audio …"
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
                        "Batch: каждый фрейм [B,H,W,3] → отдельный элемент images[]."
                    ),
                }),
                "video": ("VIDEO", {
                    "tooltip": (
                        "Видео для video-to-video генерации (нативный VIDEO вход).\n"
                        "Подключите выход VIDEO любого нода (LoadVideo, etc.)."
                    ),
                }),
                "aspect_ratio": (ASPECT_RATIOS, {"default": "auto"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2_147_483_647}),
                "quality": (QUALITIES, {"default": "auto"}),
                "image_resolution": (IMAGE_RESOLUTIONS, {"default": "auto"}),
                "output_format": (OUTPUT_FORMATS, {"default": "png"}),
                "max_images": ("INT", {"default": 1, "min": 1, "max": 6}),
                "guidance_scale": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 30.0, "step": 0.5}),
                "strength": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.05}),
                "is_enhance": ("BOOLEAN", {"default": False}),
                "enable_safety": ("BOOLEAN", {"default": True}),
                "duration": (DURATIONS, {"default": "auto"}),
                "video_resolution": (VIDEO_RESOLUTIONS, {"default": "auto"}),
                "kling_mode": (["std", "pro"], {
                    "default": "std",
                    "tooltip": "Режим Kling 3.0: std (быстрее) или pro (качественнее)",
                }),
                "multi_shots": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Мульти-шоты для Wan 2.6 (несколько сцен в одном видео)",
                }),
                "sound": ("BOOLEAN", {"default": False}),
                "voice": ("STRING", {"default": ""}),
                "speed": ("FLOAT", {"default": 1.0, "min": 0.7, "max": 1.2, "step": 0.05}),
                "language_code": ("STRING", {"default": ""}),
                "extra_params_json": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "placeholder": '{"watermark":"Brand","mode":"pro"}',
                }),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **_kw):
        return float("nan")

    # ── Execute ───────────────────────────────────────────────

    def execute(
        self,
        model: str,
        prompt: str,
        api_key: str = "",
        image: torch.Tensor | None = None,
        video: torch.Tensor | None = None,
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
        kling_mode: str = "std",
        multi_shots: bool = False,
        sound: bool = False,
        voice: str = "",
        speed: float = 1.0,
        language_code: str = "",
        extra_params_json: str = "",
    ) -> dict:

        t0 = time.time()

        # ── 1. API key ──────────────────────────────────────────
        try:
            key = resolve_api_key(api_key)
        except ValueError as exc:
            return self._error(str(exc))

        if not prompt.strip():
            return self._error("❌ Промпт не может быть пустым")

        # ── 2. Determine model type ─────────────────────────────
        model_type = _get_model_type(model)
        logger.info("PolzaMedia: start  model=%s  type=%s", model, model_type)

        # ── 3. Build input dict ──────────────────────────────────
        if model_type in ("kling", "wan", "veo", "sora", "seedance", "video_generic"):
            # Video model — use specialized builder
            inp = _build_video_input(
                model=model,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                duration=duration,
                video_resolution=video_resolution,
                sound=sound,
                multi_shots=multi_shots,
                mode=kling_mode,
                image=image,
                strength=strength,
            )

        elif model_type == "audio":
            # Audio / TTS model — only send relevant params, NOT image/video params
            inp = {"prompt": prompt}
            # voice, speed, language are relevant for TTS
            if voice.strip():
                inp["voice"] = voice.strip()
            if speed != 1.0:
                inp["speed"] = speed
            if language_code.strip():
                inp["language_code"] = language_code.strip()

        else:
            # Image model — general logic
            inp = {"prompt": prompt}
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

        # ── 3a. Encode input VIDEO ─────────────────────────────────
        if video is not None and _video_tensor_to_images is not None and model_type != "audio":
            try:
                frames = _video_tensor_to_images(video)
                if frames:
                    frame = frames[0]
                    pil_img = Image.fromarray(frame)
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    inp["videos"] = [{"type": "base64", "data": f"data:image/png;base64,{b64}"}]
                    logger.info("PolzaMedia: attached video input (%d frames, using frame 0)", len(frames))
            except Exception as exc:
                logger.warning("PolzaMedia: failed to encode video input: %s", exc)

        # ── 3b. Audio-specific params for non-audio models ──────────
        # (voice/speed/language_code are already handled in audio branch above)
        if model_type != "audio":
            if voice.strip():
                inp["voice"] = voice.strip()
            if speed != 1.0:
                inp["speed"] = speed
            if language_code.strip():
                inp["language_code"] = language_code.strip()

        # ── 4. Encode batch IMAGE ────────────────────────────────
        if image is not None and model_type != "audio":
            img_4d = image if image.dim() == 4 else image.unsqueeze(0)
            encoded: list[dict] = []
            for i in range(img_4d.shape[0]):
                b64 = _safe_tensor_to_b64(img_4d[i], fmt="PNG")
                encoded.append({"type": "base64", "data": f"data:image/png;base64,{b64}"})
            inp["images"] = encoded
            if model_type in ("kling", "wan"):
                inp["strength"] = strength
            logger.info("PolzaMedia: attached %d image(s)", len(encoded))

        # ── 5. Merge extra JSON ──────────────────────────────────
        if extra_params_json.strip():
            try:
                extra = json.loads(extra_params_json)
            except json.JSONDecodeError as exc:
                return self._error(f"❌ Невалидный JSON: {exc}")
            if not isinstance(extra, dict):
                return self._error("❌ extra_params_json должен быть JSON-объектом {}")
            inp.update(extra)

        # ── 6. Call API ──────────────────────────────────────────
        logger.info("PolzaMedia [%s]: %s", model_type, json.dumps(inp, ensure_ascii=False))
        try:
            data = media_create(key, model=model, input=inp)
        except PolzaAPIError as exc:
            return self._error(f"❌ API [{exc.status_code}]: {exc.message}")
        except Exception as exc:
            logger.exception("PolzaMedia: unexpected error")
            return self._error(f"❌ Unexpected: {exc}")

        elapsed = time.time() - t0
        status = data.get("status", "?")
        logger.info("PolzaMedia: status=%s  id=%s  %.1fs", status, data.get("id", "?"), elapsed)

        if status == "failed":
            err_obj = data.get("error", {})
            err_msg = err_obj.get("message", "Ошибка") if isinstance(err_obj, dict) else str(err_obj)
            return self._error(f"❌ Генерация не удалась: {err_msg}")

        # ── 7. Parse response ────────────────────────────────────
        pil_images    = images_from_generation(data)
        media_urls    = _extract_media_urls(data)
        media_url_str = "\n".join(media_urls)
        media_id      = data.get("id", "")
        text_response = data.get("content", "") or ""
        reasoning     = data.get("reasoning_summary", "") or ""
        cost_rub, usage_summary = extract_usage_info(data)
        warnings_list = data.get("warnings") or []

        # ── 8. Download and classify media ───────────────────────
        video_filepath: str | None = None
        video_filename: str | None = None
        audio_files: list[tuple[str, str]] = []

        for url in media_urls:
            kind = _classify_url(url)
            if kind == "video" and video_filepath is None:
                try:
                    video_filepath, video_filename = _download_video_to_temp(url)
                except Exception as exc:
                    logger.error("PolzaMedia: video download failed: %s", exc)
            elif kind == "audio":
                try:
                    audio_files.append(_download_audio_to_temp(url))
                except Exception as exc:
                    logger.error("PolzaMedia: audio download failed: %s", exc)

        # ── 9. Build IMAGE tensor ────────────────────────────────
        if pil_images:
            batch_tensor = images_to_batch_tensor(pil_images)
        else:
            batch_tensor = torch.zeros(1, 64, 64, 3, dtype=torch.float32)

        # ── 10. Build native VIDEO output ────────────────────────
        video_output: Optional[object] = None
        if video_filepath and _HAS_NATIVE_VIDEO:
            try:
                video_output = InputImpl.VideoFromFile(video_filepath)
                logger.info("PolzaMedia: created native VIDEO from %s", video_filepath)
            except Exception as exc:
                logger.error("PolzaMedia: VideoFromFile failed: %s", exc)
        elif video_filepath and not _HAS_NATIVE_VIDEO:
            logger.warning(
                "PolzaMedia: video downloaded but comfy_api.latest not available. "
                "Update ComfyUI for native VIDEO output."
            )
        # Fallback: create VIDEO from generated images
        elif pil_images and not video_filepath and _HAS_NATIVE_VIDEO:
            try:
                video_tensor = images_to_batch_tensor(pil_images)
                frames_list: list[np.ndarray] = []
                for i in range(video_tensor.shape[0]):
                    frame = video_tensor[i].cpu().numpy()
                    if frame.dtype != np.uint8:
                        frame = (np.clip(frame, 0, 1) * 255).astype(np.uint8)
                    frames_list.append(frame)
                video_output = InputImpl.VideoFromComponents(
                    Types.VideoComponents(
                        images=np.stack(frames_list),  # ndarray, not list!
                        audio=None,
                        frame_rate=Fraction(1),
                    )
                )
                logger.info("PolzaMedia: created native VIDEO from %d image(s)", len(frames_list))
            except Exception as exc:
                logger.warning("PolzaMedia: VideoFromComponents failed: %s", exc)

        # ── 11. Build AUDIO output ───────────────────────────────
        audio_output: Optional[dict] = None
        if audio_files:
            audio_path, audio_filename = audio_files[0]
            try:
                import torchaudio
                waveform, sample_rate = torchaudio.load(audio_path)
                # torchaudio returns [channels, samples]
                # ComfyUI expects [batch, channels, samples]
                if waveform.dim() == 2:
                    waveform = waveform.unsqueeze(0)
                audio_output = {"waveform": waveform, "sample_rate": sample_rate}
                logger.info("PolzaMedia: audio loaded: %s (%d Hz, %.1fs)",
                           audio_filename, sample_rate, waveform.shape[-1] / sample_rate)
            except ImportError:
                logger.warning(
                    "PolzaMedia: torchaudio not available — cannot create AUDIO output. "
                    "Install torchaudio or use media_url to access the audio file."
                )
            except Exception as exc:
                logger.warning("PolzaMedia: failed to load audio %s: %s", audio_path, exc)

        # ── 12. Validate we got something ────────────────────────
        if not pil_images and not video_filepath and not audio_files and not text_response:
            return self._error(
                f"❌ API не вернул ни изображений, ни видео, ни аудио.\n"
                f"status={status}  id={media_id}"
            )

        # ── 13. Build UI dict ────────────────────────────────────
        ui: dict = {"text": []}
        ui_text: list[str] = ui["text"]

        if pil_images:
            n = len(pil_images)
            h, w = batch_tensor.shape[1], batch_tensor.shape[2]
            ui_text.append(f"✅ {n} image{'s' if n > 1 else ''} · {w}×{h}")

        if video_filename:
            ui_text.append(f"🎬 Video: {video_filename}")
            ui["gifs"] = [{
                "filename": video_filename,
                "subfolder": "",
                "type": "temp",
            }]

        for audio_path, audio_fn in audio_files:
            ui_text.append(f"🔊 Audio: {audio_fn}")

        if media_id:
            ui_text.append(f"🆔 {media_id}")
        ui_text.append(f"📊 {usage_summary}")
        ui_text.append(f"⏱ {elapsed:.1f}s")
        if reasoning:
            ui_text.append(f"💭 {reasoning[:200]}")
        if text_response:
            ui_text.append(f"📝 {text_response[:300]}")
        for w in warnings_list:
            ui_text.append(f"⚠️ {w}")

        for line in ui_text:
            logger.info("PolzaMedia UI: %s", line)

        return {
            "ui":     ui,
            "result": (
                batch_tensor,       # IMAGE
                video_output,       # VIDEO
                audio_output,       # AUDIO
                media_url_str,      # STRING
                media_id,           # STRING
                text_response,      # STRING
                cost_rub,           # FLOAT
            ),
        }

    # ── Error helper ─────────────────────────────────────────

    @staticmethod
    def _error(msg: str) -> dict:
        logger.error("PolzaMedia: %s", msg)
        blank = torch.zeros(1, 64, 64, 3, dtype=torch.float32)

        # Create a minimal valid VIDEO
        video_blank = None
        if _HAS_NATIVE_VIDEO and InputImpl is not None and Types is not None:
            try:
                frame = (blank[0].cpu().numpy() * 255).astype(np.uint8)
                video_blank = InputImpl.VideoFromComponents(
                    Types.VideoComponents(
                        images=np.stack([frame]),  # ndarray, not list!
                        audio=None,
                        frame_rate=Fraction(1),
                    )
                )
            except Exception as exc:
                logger.warning("PolzaMedia: failed to create blank video: %s", exc)

        # Create minimal silent audio so PreviewAudio doesn't crash on None
        audio_blank = {"waveform": torch.zeros(1, 1, 16000), "sample_rate": 16000}

        return {
            "ui":     {"text": [msg]},
            "result": (blank, video_blank, audio_blank, "", "", "", 0.0),
        }