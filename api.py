"""
Polza.ai API client for ComfyUI nodes.

Endpoints covered:
  • POST /v1/chat/completions     — chat / text
  • POST /v2/images/generations   — OpenAI-compat image gen
  • POST /v1/media                — universal media (image/video/audio)
  • GET  /v1/media/{id}           — async task polling

Key resolution:  node input → env POLZA_API_KEY → config.json
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
REQUEST_TIMEOUT = 180          # single HTTP request timeout (seconds)
POLL_TIMEOUT    = 600          # max total wait for async generation
POLL_INTERVAL   = 4            # seconds between status checks
IMAGE_DOWNLOAD_TIMEOUT = 60


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Exceptions                                                      ║
# ╚═══════════════════════════════════════════════════════════════════╝

class PolzaAPIError(Exception):
    """Non-200 response from Polza.ai."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[HTTP {status_code}] {message}")


class PolzaTimeoutError(PolzaAPIError):
    """Generation did not finish within the polling window."""

    def __init__(self, media_id: str):
        super().__init__(408, f"Генерация {media_id} не завершилась за {POLL_TIMEOUT}s")
        self.media_id = media_id


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  API key resolution                                              ║
# ╚═══════════════════════════════════════════════════════════════════╝

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def resolve_api_key(node_key: str = "") -> str:
    """
    Resolve the API key:
      1. Direct node input
      2. POLZA_API_KEY env var
      3. config.json
    """
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
        "Укажите его одним из способов:\n"
        "  1. В поле «api_key» ноды\n"
        "  2. Переменная окружения  POLZA_API_KEY\n"
        "  3. Файл config.json:  {\"api_key\": \"pk-...\"}"
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
    """Generic POST request → parsed JSON."""
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
            detail = resp.json()
            msg = detail.get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        raise PolzaAPIError(resp.status_code, msg)

    return resp.json()


def _get(api_key: str, path: str, timeout: int = 30) -> dict:
    """Generic GET request → parsed JSON."""
    url = f"{API_BASE}{path}"

    try:
        resp = requests.get(url, headers=_headers(api_key), timeout=timeout)
    except requests.exceptions.Timeout:
        raise PolzaAPIError(408, "Таймаут запроса")
    except requests.exceptions.ConnectionError:
        raise PolzaAPIError(503, "Нет соединения с polza.ai")

    if resp.status_code != 200:
        try:
            detail = resp.json()
            msg = detail.get("error", {}).get("message", resp.text)
        except Exception:
            msg = resp.text
        raise PolzaAPIError(resp.status_code, msg)

    return resp.json()


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Chat Completions   POST /v1/chat/completions                   ║
# ╚═══════════════════════════════════════════════════════════════════╝

def chat_completion(api_key: str, **kwargs: Any) -> dict:
    payload = {k: v for k, v in kwargs.items() if v is not None}
    data = _post(api_key, "/v1/chat/completions", payload)
    _log_usage(data)
    return data


def extract_response(data: dict):
    """Extract text, reasoning, cost_rub, total_tokens from chat response."""
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}

    text      = msg.get("content") or ""
    reasoning = msg.get("reasoning") or ""
    usage     = data.get("usage") or {}
    cost_rub  = float(usage.get("cost_rub", 0) or 0)
    tokens    = int(usage.get("total_tokens", 0) or 0)

    return text, reasoning, cost_rub, tokens


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Image Generation   POST /v2/images/generations                  ║
# ╚═══════════════════════════════════════════════════════════════════╝

def image_generation(api_key: str, **kwargs: Any) -> dict:
    """
    OpenAI-compatible image generation.

    Returns EITHER:
      • completed:  {created, data: [{url, b64_json, revised_prompt}], usage}
      • pending:    {id, status: "pending", model, created}

    If pending, automatically polls until completion.
    """
    payload = {k: v for k, v in kwargs.items() if v is not None}
    data = _post(api_key, "/v2/images/generations", payload, timeout=REQUEST_TIMEOUT)

    # ── Check if response is pending (timeout > 120s on server side) ──
    if data.get("status") in ("pending", "processing"):
        media_id = data["id"]
        logger.info("Polza.ai ⏳ Image generation pending → polling %s", media_id)
        data = poll_until_complete(api_key, media_id)

    _log_usage(data)
    return data


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Media API   POST /v1/media   +   GET /v1/media/{id}            ║
# ╚═══════════════════════════════════════════════════════════════════╝

def media_create(api_key: str, **kwargs: Any) -> dict:
    """
    Create a media generation task (always async).
    Returns MediaStatusPresenter with status="pending".
    Automatically polls until completion.
    """
    payload = {k: v for k, v in kwargs.items() if v is not None}
    data = _post(api_key, "/v1/media", payload)

    media_id = data.get("id")
    status = data.get("status", "")

    if status == "completed":
        _log_usage(data)
        return data

    if not media_id:
        raise PolzaAPIError(500, "Ответ Media API не содержит id задачи")

    logger.info("Polza.ai ⏳ Media task created → %s  polling…", media_id)
    completed = poll_until_complete(api_key, media_id)
    _log_usage(completed)
    return completed


def media_status(api_key: str, media_id: str) -> dict:
    """GET /v1/media/{id} — check generation status."""
    return _get(api_key, f"/v1/media/{media_id}")


def poll_until_complete(
    api_key: str,
    media_id: str,
    timeout: int = POLL_TIMEOUT,
    interval: int = POLL_INTERVAL,
) -> dict:
    """
    Poll GET /v1/media/{id} until status is completed or failed.
    Raises PolzaTimeoutError if timeout exceeded.
    """
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        data = media_status(api_key, media_id)
        status = data.get("status", "unknown")

        if status == "completed":
            logger.info("Polza.ai ✅ Generation %s completed (poll #%d)", media_id, attempt)
            return data

        if status == "failed":
            error = data.get("error", {})
            err_msg = error.get("message", "Неизвестная ошибка") if isinstance(error, dict) else str(error)
            raise PolzaAPIError(500, f"Генерация {media_id} завершилась ошибкой: {err_msg}")

        logger.info(
            "Polza.ai ⏳ %s status=%s  (poll #%d, %.0fs elapsed)",
            media_id, status, attempt, time.time() - (deadline - timeout),
        )
        time.sleep(interval)

    raise PolzaTimeoutError(media_id)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Image tensor helpers                                            ║
# ╚═══════════════════════════════════════════════════════════════════╝

def download_image(url: str) -> Image.Image:
    """Download image from URL → PIL Image (RGB)."""
    resp = requests.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT, stream=True)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    return img.convert("RGB")


def b64_to_pil(b64_string: str) -> Image.Image:
    """Decode base64 string → PIL Image (RGB)."""
    # Strip data URI prefix if present
    if "," in b64_string:
        b64_string = b64_string.split(",", 1)[1]
    raw = base64.b64decode(b64_string)
    img = Image.open(io.BytesIO(raw))
    return img.convert("RGB")


def pil_to_tensor(img: Image.Image) -> torch.Tensor:
    """PIL Image → ComfyUI IMAGE tensor [1, H, W, 3] float32 0-1."""
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


def tensor_to_b64(tensor: torch.Tensor, fmt: str = "PNG") -> str:
    """ComfyUI IMAGE tensor [B,H,W,C] → base64 string (first frame)."""
    if tensor.dim() == 4:
        tensor = tensor[0]
    arr = (tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format=fmt, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def images_from_generation(data: dict) -> List[Image.Image]:
    """
    Extract PIL images from a generation response.

    Works with both /v2/images/generations and /v1/media responses.
    Returns a list of PIL Images.
    """
    images: List[Image.Image] = []
    data_items = data.get("data") or []

    for item in data_items:
        if not isinstance(item, dict):
            continue

        # ── b64_json (inline base64) ─────────────────────────────────
        b64 = item.get("b64_json")
        if b64:
            images.append(b64_to_pil(b64))
            continue

        # ── url ──────────────────────────────────────────────────────
        url = item.get("url")
        if url:
            try:
                images.append(download_image(url))
            except Exception as exc:
                logger.error("Failed to download image from %s: %s", url, exc)
                continue

    return images


def images_to_batch_tensor(pil_images: List[Image.Image]) -> torch.Tensor:
    """
    List[PIL.Image] → batched tensor [B, H, W, 3].
    All images resized to match the first image's dimensions.
    """
    if not pil_images:
        # Return a 1x64x64 black image as fallback
        return torch.zeros(1, 64, 64, 3, dtype=torch.float32)

    target_size = pil_images[0].size  # (W, H)
    tensors = []

    for img in pil_images:
        if img.size != target_size:
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        tensors.append(pil_to_tensor(img))

    return torch.cat(tensors, dim=0)


def extract_usage_info(data: dict) -> Tuple[float, str]:
    """Extract cost_rub and a human-readable summary from usage."""
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


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Logging                                                         ║
# ╚═══════════════════════════════════════════════════════════════════╝

def _log_usage(data: dict):
    usage = data.get("usage") or {}
    cost = float(usage.get("cost_rub", 0) or usage.get("cost", 0) or 0)
    tokens = usage.get("total_tokens", "—")
    logger.info("Polza.ai ✅  tokens=%s  cost=%.4f ₽", tokens, cost)


# ╔═══════════════════════════════════════════════════════════════════╗
# ║  Models List   GET /v1/models                                     ║
# ╚═══════════════════════════════════════════════════════════════════╝

def get_models(model_type: str | None = None, include_providers: bool = False) -> List[dict]:
    """
    Fetch available models from Polza.ai API.
    
    Args:
        model_type: Filter by type (chat, image, embedding, video, audio)
        include_providers: Include provider details for each model
        
    Returns:
        List of model dictionaries with id, name, type, architecture, etc.
    """
    params = {}
    if model_type:
        params["type"] = model_type
    if include_providers:
        params["include_providers"] = "true"
    
    url = f"{API_BASE}/v1/models"
    logger.info("Fetching models from %s with params %s", url, params)
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])
    except requests.exceptions.Timeout:
        raise PolzaAPIError(408, "Таймаут при получении списка моделей")
    except requests.exceptions.ConnectionError:
        raise PolzaAPIError(503, "Нет соединения с polza.ai")
    except Exception as exc:
        logger.error("Error fetching models: %s", exc)
        raise PolzaAPIError(500, f"Ошибка получения моделей: {exc}")


def get_model_options(model_type: str | None = None) -> List[Tuple[str, str]]:
    """
    Get model options for ComfyUI dropdown.
    
    Returns list of (model_id, display_name) tuples.
    """
    models = get_models(model_type=model_type)
    
    options = []
    for model in models:
        model_id = model.get("id", "")
        model_name = model.get("name", model_id)
        options.append((model_id, model_name))
    
    # Sort alphabetically by display name
    options.sort(key=lambda x: x[1].lower())
    return options
