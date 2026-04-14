"""
Polza.ai API client for ComfyUI nodes.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
import torch
from PIL import Image

logger = logging.getLogger("PolzaAI")

# ── Constants ─────────────────────────────────────────────────────────

API_BASE = "https://polza.ai/api"
REQUEST_TIMEOUT = 180
POLL_TIMEOUT    = 600
POLL_INTERVAL   = 4
IMAGE_DOWNLOAD_TIMEOUT  = 60
MEDIA_DOWNLOAD_TIMEOUT  = 300   # video/audio can be large

# Extensions used to distinguish media types in URLs
_VIDEO_EXTS = (".mp4", ".webm", ".mov", ".avi", ".mkv")
_AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Exceptions                                                      ║
# ╚═══════════════════════════════════════════════════════════════════╝

class PolzaAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[HTTP {status_code}] {message}")


class PolzaTimeoutError(PolzaAPIError):
    def __init__(self, media_id: str):
        super().__init__(408, f"Генерация {media_id} не завершилась за {POLL_TIMEOUT}s")
        self.media_id = media_id


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  API key resolution                                              ║
# ╚═══════════════════════════════════════════════════════════════════╝

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def resolve_api_key(node_key: str = "") -> str:
    if node_key and node_key.strip():
        return node_key.strip()
    env_key = os.environ.get("POLZA_API_KEY", "").strip()
    if env_key:
        return env_key
    if os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as fh:
                cfg = json.load(fh)
                key = cfg.get("api_key", "").strip()
                if key:
                    return key
        except Exception:
            pass
    raise ValueError(
        "🔑 API‑ключ Polza.ai не найден.\n"
        "  1. Поле «api_key» ноды\n"
        "  2. Env POLZA_API_KEY\n"
        "  3. config.json: {\"api_key\": \"pk-...\"}"
    )


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  HTTP helpers                                                    ║
# ╚═══════════════════════════════════════════════════════════════════╝

def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
        "User-Agent":    "ComfyUI-PolzaAI/1.0",
    }


def _post(api_key: str, path: str, payload: dict, timeout: int = REQUEST_TIMEOUT) -> dict:
    url = f"{API_BASE}{path}"
    logger.info("Polza.ai POST %s", url)
    try:
        resp = requests.post(url, headers=_headers(api_key), json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        raise PolzaAPIError(408, f"Таймаут запроса (>{timeout}s)")
    except requests.exceptions.ConnectionError:
        raise PolzaAPIError(503, "Нет соединения с polza.ai")
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        raise PolzaAPIError(resp.status_code, msg)
    return resp.json()


def _get(api_key: str, path: str, timeout: int = 30) -> dict:
    url = f"{API_BASE}{path}"
    try:
        resp = requests.get(url, headers=_headers(api_key), timeout=timeout)
    except requests.exceptions.Timeout:
        raise PolzaAPIError(408, "Таймаут запроса")
    except requests.exceptions.ConnectionError:
        raise PolzaAPIError(503, "Нет соединения с polza.ai")
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        raise PolzaAPIError(resp.status_code, msg)
    return resp.json()


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Media file download (video / audio)                             ║
# ╚═══════════════════════════════════════════════════════════════════╝

def download_media_file(
    url: str,
    filepath: str,
    timeout: int = MEDIA_DOWNLOAD_TIMEOUT,
) -> str:
    """
    Streaming download of a media file (video / audio) to *filepath*.
    Returns the filepath on success.
    """
    logger.info("Downloading media: %s → %s", url, filepath)
    resp = requests.get(url, timeout=timeout, stream=True)
    resp.raise_for_status()

    total = 0
    with open(filepath, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                fh.write(chunk)
                total += len(chunk)

    logger.info("Downloaded %d bytes (%.1f MB)", total, total / 1048576)
    return filepath


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Chat Completions                                                ║
# ╚═══════════════════════════════════════════════════════════════════╝

def chat_completion(api_key: str, **kwargs: Any) -> dict:
    payload = {k: v for k, v in kwargs.items() if v is not None}
    data = _post(api_key, "/v1/chat/completions", payload)
    _log_usage(data)
    return data


def extract_response(data: dict):
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    text      = msg.get("content") or ""
    reasoning = msg.get("reasoning") or ""
    usage     = data.get("usage") or {}
    cost_rub  = float(usage.get("cost_rub", 0) or 0)
    tokens    = int(usage.get("total_tokens", 0) or 0)
    return text, reasoning, cost_rub, tokens


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Image Generation                                                ║
# ╚═══════════════════════════════════════════════════════════════════╝

def image_generation(api_key: str, **kwargs: Any) -> dict:
    payload = {k: v for k, v in kwargs.items() if v is not None}
    data = _post(api_key, "/v2/images/generations", payload, timeout=REQUEST_TIMEOUT)
    if data.get("status") in ("pending", "processing"):
        data = poll_until_complete(api_key, data["id"])
    _log_usage(data)
    return data


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Media API                                                       ║
# ╚═══════════════════════════════════════════════════════════════════╝

def media_create(api_key: str, **kwargs: Any) -> dict:
    payload = {k: v for k, v in kwargs.items() if v is not None}
    data = _post(api_key, "/v1/media", payload)
    media_id = data.get("id")
    if data.get("status") == "completed":
        _log_usage(data)
        return data
    if not media_id:
        raise PolzaAPIError(500, "Ответ Media API не содержит id задачи")
    logger.info("Polza.ai ⏳ Media task %s  polling…", media_id)
    completed = poll_until_complete(api_key, media_id)
    _log_usage(completed)
    return completed


def media_status(api_key: str, media_id: str) -> dict:
    return _get(api_key, f"/v1/media/{media_id}")


def poll_until_complete(
    api_key: str,
    media_id: str,
    timeout: int = POLL_TIMEOUT,
    interval: int = POLL_INTERVAL,
) -> dict:
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        data = media_status(api_key, media_id)
        status = data.get("status", "unknown")
        if status == "completed":
            logger.info("Polza.ai ✅ %s completed (poll #%d)", media_id, attempt)
            return data
        if status == "failed":
            error = data.get("error", {})
            err_msg = error.get("message", "Ошибка") if isinstance(error, dict) else str(error)
            raise PolzaAPIError(500, f"{media_id} failed: {err_msg}")
        logger.info("Polza.ai ⏳ %s  status=%s  poll #%d", media_id, status, attempt)
        time.sleep(interval)
    raise PolzaTimeoutError(media_id)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Image tensor helpers                                            ║
# ╚═══════════════════════════════════════════════════════════════════╝

def download_image(url: str) -> Image.Image:
    resp = requests.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT, stream=True)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


def b64_to_pil(b64_string: str) -> Image.Image:
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(b64_string))).convert("RGB")


def pil_to_tensor(img: Image.Image) -> torch.Tensor:
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


def tensor_to_b64(tensor: torch.Tensor, fmt: str = "PNG") -> str:
    if tensor.dim() == 4:
        tensor = tensor[0]
    arr = (tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format=fmt, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _is_media_url(url: str) -> bool:
    """Return True if URL points to a video or audio file (not an image)."""
    lo = url.lower().split("?")[0]
    return any(lo.endswith(ext) for ext in _VIDEO_EXTS + _AUDIO_EXTS)


def images_from_generation(data: dict) -> List[Image.Image]:
    """
    Extract PIL images from a generation response.

    **Skips** video and audio URLs — those are handled separately
    by the media node via ``download_media_file``.
    """
    images: List[Image.Image] = []
    raw = data.get("data")
    if raw is None:
        return images

    data_items = [raw] if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])

    for item in data_items:
        if not isinstance(item, dict):
            continue

        # base64-encoded image
        b64 = item.get("b64_json")
        if b64:
            images.append(b64_to_pil(b64))
            continue

        # URL — only download if it's an image, NOT video/audio
        url = item.get("url")
        if url:
            if _is_media_url(url):
                logger.debug("images_from_generation: skipping media URL %s", url)
                continue
            try:
                images.append(download_image(url))
            except Exception as exc:
                logger.error("Failed to download image from %s: %s", url, exc)

    return images


def images_to_batch_tensor(pil_images: List[Image.Image]) -> torch.Tensor:
    if not pil_images:
        return torch.zeros(1, 64, 64, 3, dtype=torch.float32)
    target_size = pil_images[0].size
    tensors = []
    for img in pil_images:
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        tensors.append(pil_to_tensor(img))
    return torch.cat(tensors, dim=0)


def extract_usage_info(data: dict) -> Tuple[float, str]:
    usage = data.get("usage") or {}
    cost_rub = float(usage.get("cost_rub", 0) or usage.get("cost", 0) or 0)
    parts = []
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        val = usage.get(key)
        if val:
            parts.append(f"{key}={val}")
    if cost_rub:
        parts.append(f"cost={cost_rub:.4f}₽")
    return cost_rub, "  ".join(parts) if parts else "no usage data"


def _log_usage(data: dict):
    usage = data.get("usage") or {}
    cost = float(usage.get("cost_rub", 0) or usage.get("cost", 0) or 0)
    logger.info("Polza.ai ✅  tokens=%s  cost=%.4f ₽", usage.get("total_tokens", "—"), cost)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Models List                                                     ║
# ╚═══════════════════════════════════════════════════════════════════╝

def get_models(
    model_type: str | None = None,
    include_providers: bool = False,
    api_key: str | None = None,
) -> List[dict]:
    params: Dict[str, Any] = {}
    if model_type:
        params["type"] = model_type
    if include_providers:
        params["include_providers"] = "true"

    headers: Dict[str, str] = {}
    key = (api_key or "").strip()
    if not key:
        try:
            key = resolve_api_key("")
        except ValueError:
            key = ""
    if key:
        headers = _headers(key)
        headers.pop("Content-Type", None)

    url = f"{API_BASE}/v1/models"
    try:
        resp = requests.get(url, params=params, headers=headers or None, timeout=15)
    except requests.exceptions.Timeout:
        raise PolzaAPIError(408, "Таймаут запроса списка моделей")
    except requests.exceptions.ConnectionError:
        raise PolzaAPIError(503, "Нет соединения с polza.ai")

    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        raise PolzaAPIError(resp.status_code, msg)

    return resp.json().get("data", [])


def get_model_options(
    model_type: str | None = None,
    require_input_modality: str | None = None,
) -> List[str]:
    models = get_models(model_type=model_type)

    if require_input_modality:
        wanted = require_input_modality.lower()

        def _supports_modality(model: dict) -> bool:
            arch = model.get("architecture") or {}
            inputs = arch.get("input_modalities")
            if isinstance(inputs, list):
                if any(str(mod).strip().lower() == wanted for mod in inputs):
                    return True

            modality = arch.get("modality")
            if isinstance(modality, str) and "->" in modality:
                lhs = modality.split("->", 1)[0]
                parts = [part.strip().lower() for part in lhs.split("+")]
                return wanted in parts
            return False

        models = [m for m in models if _supports_modality(m)]

    options = [m.get("id", "") for m in models if m.get("id")]
    options.sort(key=str.lower)
    return options