# ComfyUI — Polza.ai Nodes 🤖

Пакет нод для [ComfyUI](https://github.com/comfyanonymous/ComfyUI),
предоставляющий доступ к **300+ AI-моделям** через единый API
[Polza.ai](https://polza.ai).

## Ноды

| Нода | Описание |
|---|---|
| 💬 **Polza Chat** | Chat Completions — GPT-4o, Claude, Gemini, DeepSeek и сотни других |
| 👁️ **Polza Vision** | Мультимодальный анализ изображений (image + text → text) |
| 🎨 **Polza Text‑to‑Image** | OpenAI-совместимая генерация: gpt-image-1, DALL·E 3/2 |
| 🖼️ **Polza Media Image** | Продвинутая генерация: Seedream, Nano Banana, Flux, Grok и др. + img2img |
| 📝 **Polza Show Text** | Утилита для отображения текста прямо в графе |

## Установка

### Через ComfyUI Manager
1. Откройте **ComfyUI Manager** → **Install Custom Nodes**
2. Найдите **ComfyUI-Polza**
3. Установите и перезапустите ComfyUI

### Вручную
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/your-name/ComfyUI-Polza.git
cd ComfyUI-Polza
pip install -r requirements.txt
```

## Настройка API-ключа

Получите ключ на [polza.ai](https://polza.ai).  Три способа указать:

1. **Переменная окружения** *(рекомендуется)*:
   ```bash
   export POLZA_API_KEY="pk-your-key-here"
   ```

2. **Файл конфигурации** — создайте `config.json` в папке ноды:
   ```json
   {"api_key": "pk-your-key-here"}
   ```

3. **Прямой ввод** — поле `api_key` в каждой ноде

## Примеры workflow

### 🎨 Text-to-Image (OpenAI-совместимый)

```
[🎨 Polza Text-to-Image]
  model: gpt-image-1
  prompt: "Космический пейзаж с планетами"
  size: 1024x1024
  quality: high
      ↓ images
[Preview Image]
```

### 🖼️ Media Image (продвинутый)

```
[🖼️ Polza Media Image]
  model: seedream-3
  prompt: "Киберпанк город ночью"
  aspect_ratio: 16:9
  quality: high
  image_resolution: 2K
      ↓ images
[Save Image]
```

### 🖼️ Image-to-Image

```
[Load Image] → image → [🖼️ Polza Media Image]
                          model: seedream-3
                          prompt: "Сделай ярче, добавь закат"
                          strength: 0.7
                              ↓ images
                        [Preview Image]
```

### 💬 Chat → 🎨 Image (цепочка)

```
[💬 Polza Chat]
  model: openai/gpt-4o
  prompt: "Придумай описание для картины"
      ↓ text
[🎨 Polza Text-to-Image]
  model: gpt-image-1
      ↓ images
[Preview Image]
```

### 👁️ Vision → 🖼️ Image (описание и перерисовка)

```
[Load Image] → image → [👁️ Polza Vision]
                          prompt: "Опиши стиль этого изображения"
                              ↓ text
                        [🖼️ Polza Media Image]
                          model: seedream-3
                          prompt: ← (из Vision)
                              ↓ images
                        [Save Image]
```

## Поддерживаемые модели

### Текст / Чат
| Провайдер | Модели |
|---|---|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4.1, o1, o3, o3-mini, o4-mini |
| Anthropic | claude-sonnet-4-5, claude-4-sonnet, claude-3.5-haiku |
| Google | gemini-2.5-pro, gemini-2.5-flash |
| DeepSeek | deepseek-chat, deepseek-reasoner |

### Изображения
| Модель | Нода | Описание |
|---|---|---|
| gpt-image-1 | 🎨 / 🖼️ | GPT Image (OpenAI) |
| dall-e-3 | 🎨 | DALL·E 3 (OpenAI) |
| seedream-3 | 🖼️ | Seedream 3 (ByteDance) |
| seedream-4-5 | 🖼️ | Seedream 4.5 |
| nano-banana | 🖼️ | Nano Banana |
| flux-1-1-ultra | 🖼️ | Flux Ultra |
| grok-2-image | 🖼️ | Grok Imagine (xAI) |

Полный список: [polza.ai/models](https://polza.ai/models)

## Асинхронная генерация

Генерация изображений может занимать время. Ноды автоматически:

1. Отправляют запрос к API
2. Если ответ не готов мгновенно — переходят в режим polling
3. Каждые 4 секунды проверяют статус (до 10 минут)
4. При завершении — скачивают и возвращают результат

Прогресс отображается в логах ComfyUI.

## Лицензия

MIT
