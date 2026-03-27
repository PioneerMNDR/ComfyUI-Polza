"""
📝 PolzaShowText — utility node to display text in the graph.
"""

from __future__ import annotations


class PolzaShowText:
    """
    Display any STRING value directly inside the node.
    Useful for previewing LLM responses without leaving the graph.
    """

    CATEGORY     = "🤖 Polza.ai/utils"
    FUNCTION     = "execute"
    OUTPUT_NODE  = True

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)

    DESCRIPTION = "Отображает текст прямо в ноде.  Подключите выход любой текстовой ноды."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
            },
        }

    def execute(self, text: str) -> dict:
        return {
            "ui":     {"text": [text]},
            "result": (text,),
        }
