"""
💬 PolzaChat — Chat Completion node for ComfyUI.
Supports 300+ models via Polza.ai aggregator.
"""

from __future__ import annotations

import logging
from typing import Tuple

from .api import resolve_api_key, chat_completion, extract_response, PolzaAPIError

logger = logging.getLogger("PolzaAI")

# ── Dropdown options ──────────────────────────────────────────────────

REASONING_EFFORTS = ["none", "minimal", "low", "medium", "high", "xhigh"]
RESPONSE_FORMATS  = ["text", "json_object"]


class PolzaChat:
    """
    Chat completion via Polza.ai.

    Supports GPT‑4o, Claude, Gemini, DeepSeek, LLaMA, Qwen
    and hundreds of other models through a single API.

    Leave «api_key» empty to use the POLZA_API_KEY env var
    or config.json.
    """

    # ── ComfyUI metadata ─────────────────────────────────────────────

    CATEGORY     = "🤖 Polza.ai"
    FUNCTION     = "execute"
    OUTPUT_NODE  = True

    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "INT")
    RETURN_NAMES = ("text",   "reasoning", "cost_rub", "total_tokens")

    DESCRIPTION = (
        "Генерация текста через Polza.ai Chat Completions API.\n"
        "Поддержка 300+ моделей, reasoning, JSON‑режим."
    )

    # ── Inputs ────────────────────────────────────────────────────────

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("STRING", {
                    "default": "openai/gpt-4o",
                    "tooltip": (
                        "ID модели: openai/gpt-4o, anthropic/claude-sonnet-4-5-20250929, "
                        "google/gemini-2.5-flash-preview, deepseek/deepseek-chat …"
                    ),
                }),
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Введите запрос…",
                    "dynamicPrompts": True,
                    "tooltip": "Текст запроса (user message)",
                }),
            },
            "optional": {
                "api_key": ("STRING", {
                    "default": "",
                    "tooltip": "API‑ключ Polza.ai.  Пусто → POLZA_API_KEY / config.json",
                }),
                "system_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Системный промпт (необязательно)…",
                    "tooltip": "Системная инструкция (role=system)",
                }),
                "temperature": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0, "max": 2.0, "step": 0.05,
                    "tooltip": "0 = детерминированный, 2 = максимально креативный",
                }),
                "max_tokens": ("INT", {
                    "default": 2048,
                    "min": 1, "max": 128000, "step": 64,
                    "tooltip": "Лимит токенов в ответе",
                }),
                "top_p": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": "Nucleus sampling",
                }),
                "frequency_penalty": ("FLOAT", {
                    "default": 0.0,
                    "min": -2.0, "max": 2.0, "step": 0.1,
                    "tooltip": "Штраф за повторение слов",
                }),
                "presence_penalty": ("FLOAT", {
                    "default": 0.0,
                    "min": -2.0, "max": 2.0, "step": 0.1,
                    "tooltip": "Штраф за повторение токенов",
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0, "max": 2147483647,
                    "tooltip": "Seed для воспроизводимости (0 = случайный)",
                }),
                "reasoning_effort": (REASONING_EFFORTS, {
                    "default": "none",
                    "tooltip": "Уровень рассуждений (для o1, o3, DeepSeek‑R1 и др.)",
                }),
                "response_format": (RESPONSE_FORMATS, {
                    "default": "text",
                    "tooltip": "Формат ответа: text или json_object",
                }),
            },
        }

    # ── Always re‑run (API calls are non‑deterministic) ──────────────

    @classmethod
    def IS_CHANGED(cls, **kwargs):  # noqa: N802
        return float("nan")

    # ── Main logic ────────────────────────────────────────────────────

    def execute(
        self,
        model: str,
        prompt: str,
        api_key: str = "",
        system_prompt: str = "",
        temperature: float = 1.0,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        seed: int = 0,
        reasoning_effort: str = "none",
        response_format: str = "text",
    ) -> dict:

        # ── resolve key ──────────────────────────────────────────────
        try:
            key = resolve_api_key(api_key)
        except ValueError as exc:
            err = str(exc)
            return {"ui": {"text": [err]}, "result": (err, "", 0.0, 0)}

        # ── build messages ────────────────────────────────────────────
        messages: list[dict] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt})

        # ── build params ─────────────────────────────────────────────
        params: dict = {
            "model":       model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
            "top_p":       top_p,
            "stream":      False,
        }

        if frequency_penalty != 0.0:
            params["frequency_penalty"] = frequency_penalty
        if presence_penalty != 0.0:
            params["presence_penalty"] = presence_penalty
        if seed > 0:
            params["seed"] = seed
        if response_format != "text":
            params["response_format"] = {"type": response_format}
        if reasoning_effort != "none":
            params["reasoning"] = {"effort": reasoning_effort}

        # ── call API ─────────────────────────────────────────────────
        try:
            data = chat_completion(key, **params)
        except (PolzaAPIError, Exception) as exc:
            err = f"❌ {exc}"
            logger.error("Polza Chat error: %s", exc)
            return {"ui": {"text": [err]}, "result": (err, "", 0.0, 0)}

        text, reasoning, cost_rub, total_tokens = extract_response(data)

        # ── preview (first 500 chars) ────────────────────────────────
        preview = text[:500] + ("…" if len(text) > 500 else "")
        ui_lines = [preview]
        if reasoning:
            ui_lines.append(f"\n💭 Reasoning: {reasoning[:300]}…")
        ui_lines.append(f"\n📊 {total_tokens} tok · {cost_rub:.4f} ₽")

        return {
            "ui":     {"text": ui_lines},
            "result": (text, reasoning, cost_rub, total_tokens),
        }
