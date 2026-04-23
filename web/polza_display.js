/**
 * Polza.ai — ComfyUI text display widget.
 * Shows LLM responses directly inside nodes that return ui.text.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const POLZA_TEXT_NODES = [
    "PolzaChat",
    "PolzaVision",
    "PolzaShowText",
];

const POLZA_MODEL_NODES = {
    PolzaChat: "chat",
    PolzaVision: "vision",
    PolzaTextToImage: "t2i",
    PolzaMedia: "media",
};

const MODEL_PLACEHOLDER = "Click Load models";
const BUTTON_STYLE = {
    idle: {
        bg: "#2b6e5a",
        border: "#5fc7a9",
        text: "#f4fff9",
    },
    loading: {
        bg: "#7a5a1f",
        border: "#f0c36a",
        text: "#fff8ea",
    },
    error: {
        bg: "#7b2f35",
        border: "#f08a93",
        text: "#fff3f4",
    },
};

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
        const modelScope = POLZA_MODEL_NODES[nodeData.name];

        if (modelScope) {
            const origOnNodeCreated = nodeType.prototype.onNodeCreated;

            nodeType.prototype.onNodeCreated = function () {
                const result = origOnNodeCreated?.apply(this, arguments);
                setupModelLoader(this, modelScope);
                return result;
            };
        }

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


function getWidget(node, name) {
    return node.widgets?.find((widget) => widget.name === name);
}


function refreshNode(node) {
    requestAnimationFrame(() => {
        app.graph.setDirtyCanvas(true, true);
    });
}


function layoutNode(node) {
    requestAnimationFrame(() => {
        try {
            const currentSize = Array.isArray(node.size) ? [...node.size] : [300, 200];
            const computedSize = node.computeSize();
            node.setSize([
                Math.max(currentSize[0] || 300, 300),
                Math.max(currentSize[1] || 200, computedSize[1] || 200),
            ]);
        } catch (_) {
            // ignore resize errors
        }
        app.graph.setDirtyCanvas(true, true);
    });
}


function getWidgetIndex(node, name) {
    return node.widgets?.findIndex((widget) => widget.name === name) ?? -1;
}


function setButtonVisualState(button, state, label) {
    button._polzaState = state;
    button._polzaLabel = label;
    button.value = label;
    button.label = label;
    button.name = label;
}


function drawLoadModelsButton(ctx, node, width, posY, height) {
    const state = BUTTON_STYLE[this._polzaState] || BUTTON_STYLE.idle;
    const label = this._polzaLabel || this.name || "Load models";
    const marginX = 10;
    const marginY = 2;
    const radius = 7;
    const x = marginX;
    const y = posY + marginY;
    const w = width - marginX * 2;
    const h = height - marginY * 2;
    this._polzaBounds = { x, y, w, h };

    ctx.save();
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.fillStyle = state.bg;
    ctx.strokeStyle = state.border;
    ctx.lineWidth = 1;
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = state.text;
    ctx.font = "bold 12px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, x + w / 2, y + h / 2);
    ctx.restore();
}


function loadModelsButtonMouse(event, pos, node) {
    const bounds = this._polzaBounds;
    if (!bounds || this.disabled) {
        return false;
    }

    const inside =
        pos[0] >= bounds.x &&
        pos[0] <= bounds.x + bounds.w &&
        pos[1] >= bounds.y &&
        pos[1] <= bounds.y + bounds.h;

    if (event.type === "mousedown" || event.type === "pointerdown") {
        this._polzaPressed = inside;
        return inside;
    }

    if (event.type === "mouseup" || event.type === "pointerup" || event.type === "click") {
        const shouldTrigger = inside && this._polzaPressed;
        this._polzaPressed = false;
        if (shouldTrigger) {
            this.callback?.(this, node, pos, event);
            return true;
        }
    }

    if (event.type === "mouseleave" || event.type === "pointerleave") {
        this._polzaPressed = false;
    }

    return inside;
}


function setupModelLoader(node, scope) {
    const modelWidget = getWidget(node, "model");
    if (!modelWidget) return;

    if (node.widgets?.some((widget) => widget._polzaLoadModels)) {
        return;
    }

    modelWidget.options = modelWidget.options || {};
    modelWidget.options.values = [MODEL_PLACEHOLDER];
    modelWidget.value = MODEL_PLACEHOLDER;

    const button = node.addWidget("button", "Load models", null, async () => {
        const apiKey = `${getWidget(node, "api_key")?.value ?? ""}`.trim();
        const previousValue = `${modelWidget.value ?? ""}`.trim();

        button.disabled = true;
        setButtonVisualState(button, "loading", "Loading models...");
        refreshNode(node);

        try {
            const response = await api.fetchApi("/polza/models", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scope, api_key: apiKey }),
            });

            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data?.error || `HTTP ${response.status}`);
            }

            const models = Array.isArray(data?.models) ? data.models : [];
            if (!models.length) {
                throw new Error("No models returned");
            }

            modelWidget.options = modelWidget.options || {};
            modelWidget.options.values = models;
            modelWidget.value = models.includes(previousValue) && previousValue !== MODEL_PLACEHOLDER
                ? previousValue
                : models[0];

            button.disabled = false;
            setButtonVisualState(button, "idle", `Reload models (${models.length})`);
            layoutNode(node);
        } catch (error) {
            console.error("[Polza.ai] Failed to load models:", error);
            button.disabled = false;
            setButtonVisualState(button, "error", "Retry load models");
            layoutNode(node);
        }

        refreshNode(node);
    });

    button._polzaLoadModels = true;
    button.type = "custom";
    button.options = { ...(button.options || {}), serialize: false };
    button.draw = drawLoadModelsButton;
    button.mouse = loadModelsButtonMouse;
    button.computeSize = (width) => [width, 28];
    setButtonVisualState(button, "idle", "Load models");

    const modelIndex = getWidgetIndex(node, "model");
    const buttonIndex = node.widgets?.indexOf(button) ?? -1;
    if (modelIndex >= 0 && buttonIndex >= 0 && buttonIndex !== modelIndex + 1) {
        const [widget] = node.widgets.splice(buttonIndex, 1);
        node.widgets.splice(modelIndex + 1, 0, widget);
    }

    layoutNode(node);
}
