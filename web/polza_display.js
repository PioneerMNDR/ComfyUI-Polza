/**
 * Polza.ai — ComfyUI text display widget.
 * Shows LLM responses directly inside nodes that return ui.text.
 */

import { app } from "../../scripts/app.js";

const POLZA_TEXT_NODES = [
    "PolzaChat",
    "PolzaVision",
    "PolzaShowText",
];

/* ── Styling ────────────────────────────────────────────────────────── */

const DISPLAY_STYLE = `
    opacity: 0.9;
    font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", monospace;
    font-size: 11px;
    line-height: 1.45;
    background: rgba(0, 0, 0, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 8px 10px;
    color: #e2e2e2;
    resize: vertical;
    min-height: 60px;
    max-height: 400px;
    white-space: pre-wrap;
    word-break: break-word;
`;

/* ── Extension ──────────────────────────────────────────────────────── */

app.registerExtension({
    name: "polza.ai.text_display",

    async beforeRegisterNodeDef(nodeType, nodeData, _app) {
        if (!POLZA_TEXT_NODES.includes(nodeData.name)) return;

        const origOnExecuted = nodeType.prototype.onExecuted;

        nodeType.prototype.onExecuted = function (message) {
            origOnExecuted?.apply(this, arguments);

            if (!message?.text?.length) return;

            const displayText = message.text.join("\n");

            /* find or create the display widget */
            let widget = this.widgets?.find((w) => w.name === "__polza_output__");

            if (widget) {
                widget.value = displayText;
                if (widget.inputEl) widget.inputEl.value = displayText;
            } else {
                try {
                    widget = this.addWidget(
                        "text",              // type
                        "__polza_output__",   // name
                        displayText,          // default value
                        () => {},             // callback
                        { multiline: true, serialize: false }
                    );

                    if (widget.inputEl) {
                        widget.inputEl.readOnly = true;
                        widget.inputEl.style.cssText = DISPLAY_STYLE;
                    }
                } catch (e) {
                    console.warn("[Polza.ai] Could not create display widget:", e);
                    return;
                }
            }

            /* resize the node to fit */
            requestAnimationFrame(() => {
                try {
                    const sz = this.computeSize();
                    sz[0] = Math.max(sz[0], this.size?.[0] || 300, 300);
                    sz[1] = Math.max(sz[1], this.size?.[1] || 200);
                    this.setSize(sz);
                    app.graph.setDirtyCanvas(true, false);
                } catch (_) { /* ignore resize errors */ }
            });
        };
    },
});
