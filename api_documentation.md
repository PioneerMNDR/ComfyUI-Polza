# API Documentation

> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# POST Chat Completions

> Основной эндпоинт для генерации текста и диалогов

Поддерживает текстовые диалоги, мультимодальные запросы (текст + изображения + аудио + видео + файлы), вызов функций и потоковую передачу.

## Возможности

* **Агрегация провайдеров** — автоматический выбор оптимального провайдера
* **Биллинг в рублях** — точный учет стоимости
* **Reasoning Tokens** — поддержка моделей с рассуждениями
* **Streaming** — потоковая передача через SSE
* **Tool Calling** — вызов внешних функций
* **Мультимодальность** — обработка текста, изображений, аудио, видео и файлов

## Параметры запроса

### Обязательные

| Параметр | Тип    | Описание                                                  |
| -------- | ------ | --------------------------------------------------------- |
| `model`  | string | ID модели из [списка моделей](/api-reference/models/list) |

### Контент

| Параметр   | Тип    | Описание                                         |
| ---------- | ------ | ------------------------------------------------ |
| `messages` | array  | Массив сообщений диалога (рекомендуется)         |
| `prompt`   | string | Простой текстовый промпт (альтернатива messages) |

### Параметры генерации

| Параметр                | Тип           | По умолчанию | Описание                                        |
| ----------------------- | ------------- | ------------ | ----------------------------------------------- |
| `max_tokens`            | integer       | Без лимита   | Максимум токенов в ответе                       |
| `max_completion_tokens` | integer       | Без лимита   | Альтернатива max\_tokens                        |
| `temperature`           | float (0-2)   | 1.0          | Температура (0=детерминированный, 2=креативный) |
| `top_p`                 | float (0-1)   | 1.0          | Nucleus sampling                                |
| `top_k`                 | integer       | —            | Top-K sampling                                  |
| `frequency_penalty`     | float (-2..2) | 0            | Штраф за повторение слов                        |
| `presence_penalty`      | float (-2..2) | 0            | Штраф за повторение токенов                     |
| `stop`                  | string/array  | —            | Стоп-последовательности                         |
| `seed`                  | integer       | —            | Seed для воспроизводимости                      |

### Специальные возможности

| Параметр             | Тип           | Описание                                                 |
| -------------------- | ------------- | -------------------------------------------------------- |
| `stream`             | boolean       | Включить streaming (SSE)                                 |
| `reasoning`          | object        | Настройки reasoning tokens                               |
| `tools`              | array         | Доступные функции для вызова                             |
| `tool_choice`        | string/object | Выбор инструмента: "none", "auto", "required"            |
| `response_format`    | object        | Формат ответа: text, json\_object, json\_schema, grammar |
| `web_search_options` | object        | Встроенный веб-поиск                                     |
| `provider`           | object        | Конфигурация роутинга по провайдерам                     |
| `plugins`            | array         | Подключение плагинов                                     |
| `modalities`         | array         | Выходные модальности: "text", "image", "audio"           |
| `audio`              | object        | Конфигурация аудио-вывода (voice, format)                |
| `user`               | string        | Идентификатор конечного пользователя                     |

## Структура сообщений

### Базовый формат

```json  theme={null}
{
  "role": "user|assistant|system|developer|tool",
  "content": "Текст сообщения"
}
```

### Мультимодальные сообщения

```json  theme={null}
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Что на этом изображении?"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
  ]
}
```

### Другие типы контента

```json  theme={null}
// Аудио вход
{"type": "input_audio", "input_audio": {"data": "base64...", "format": "mp3"}}

// Видео вход
{"type": "video_url", "video_url": {"url": "https://example.com/video.mp4"}}

// Файл
{"type": "file", "file": {"filename": "doc.pdf", "file_data": "data:application/pdf;base64,..."}}
```

### Системные сообщения с кешированием

```json  theme={null}
{
  "role": "system",
  "content": [
    {
      "type": "text",
      "text": "Длинная системная инструкция...",
      "cache_control": {"type": "ephemeral"}
    }
  ]
}
```

## Примеры

<CodeGroup>
  ```bash cURL theme={null}
  curl -X POST "https://polza.ai/api/v1/chat/completions" \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "openai/gpt-4o",
      "messages": [{"role": "user", "content": "Привет!"}]
    }'
  ```

  ```python Python theme={null}
  from openai import OpenAI

  client = OpenAI(
      base_url="https://polza.ai/api/v1",
      api_key="YOUR_API_KEY"
  )

  response = client.chat.completions.create(
      model="anthropic/claude-sonnet-4-5-20250929",
      messages=[{"role": "user", "content": "Объясни квантовую механику"}]
  )

  print(response.choices[0].message.content)
  print(f"Стоимость: {response.usage.cost_rub} руб.")
  ```

  ```typescript TypeScript theme={null}
  import OpenAI from 'openai';

  const client = new OpenAI({
      baseURL: 'https://polza.ai/api/v1',
      apiKey: 'YOUR_API_KEY'
  });

  const response = await client.chat.completions.create({
      model: 'openai/gpt-4o',
      messages: [{role: 'user', content: 'Напиши историю'}],
      stream: true
  });

  for await (const chunk of response) {
      process.stdout.write(chunk.choices[0]?.delta?.content || '');
  }
  ```
</CodeGroup>

## Ответ

### Успешный ответ (200)

```json  theme={null}
{
  "id": "gen_581761234567890123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "openai/gpt-4o",
  "provider": "OpenAI",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Текст ответа"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175,
    "cost_rub": 0.04131306,
    "cost": 0.04131306,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 0
    }
  }
}
```

### Streaming (SSE)

При `stream: true` ответ приходит в формате Server-Sent Events:

```
data: {"id":"gen_123","object":"chat.completion.chunk","created":1703001234,"model":"openai/gpt-4o","choices":[{"index":0,"delta":{"role":"assistant","content":"Привет"}}]}

data: {"id":"gen_123","object":"chat.completion.chunk","created":1703001234,"model":"openai/gpt-4o","choices":[{"index":0,"delta":{"content":" мир"}}]}

data: {"id":"gen_123","object":"chat.completion.chunk","created":1703001234,"model":"openai/gpt-4o","choices":[],"usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30,"cost_rub":0.015,"cost":0.015}}

data: [DONE]
```

## Tool Calling

### Определение функций

```json  theme={null}
{
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Получить текущую погоду",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {"type": "string"}
        },
        "required": ["city"]
      }
    }
  }],
  "tool_choice": "auto"
}
```

### Ответ модели с вызовом функции

```json  theme={null}
{
  "tool_calls": [{
    "id": "call_123",
    "function": {"name": "get_weather", "arguments": "{\"city\": \"Москва\"}"}
  }]
}
```

## Response Format

### JSON Schema (структурированный вывод)

```json  theme={null}
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "my_schema",
      "schema": {
        "type": "object",
        "properties": {
          "answer": {"type": "string"},
          "confidence": {"type": "number"}
        }
      },
      "strict": true
    }
  }
}
```

Поддерживаемые типы: `text`, `json_object`, `json_schema`, `grammar` (GBNF).

## Reasoning Tokens

Для моделей с рассуждениями (o1, o3, DeepSeek-R1 и другие):

```json  theme={null}
{
  "model": "openai/o1-preview",
  "messages": [{"role": "user", "content": "Реши: 2x + 5 = 13"}],
  "reasoning": {
    "effort": "high",
    "max_tokens": 1000
  }
}
```

### Параметры reasoning

| Параметр     | Тип     | Описание                                                |
| ------------ | ------- | ------------------------------------------------------- |
| `effort`     | string  | Уровень усилий: xhigh, high, medium, low, minimal, none |
| `max_tokens` | integer | Максимум токенов на рассуждения                         |
| `summary`    | string  | Детализация: auto, concise, detailed                    |
| `enabled`    | boolean | Включить/выключить рассуждения                          |
| `exclude`    | boolean | Скрыть рассуждения из ответа                            |


## OpenAPI

````yaml POST /v1/chat/completions
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/chat/completions:
    post:
      tags:
        - Чат
      summary: Создать chat completion
      operationId: ChatController_createChatCompletion[1]
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ChatCompletionRequestDto'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatCompletionPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    ChatCompletionRequestDto:
      type: object
      properties:
        model:
          type: string
          description: Идентификатор модели для использования
          example: openai/gpt-4o
        prompt:
          type: string
          description: >-
            Текстовый промпт (альтернатива messages). Если указан, будет
            преобразован в messages с role=user
          example: Напиши стихотворение про кота
        messages:
          description: >-
            Массив сообщений для отправки модели (обязателен если не указан
            prompt)
          example:
            - role: system
              content: Ты полезный ассистент
            - role: user
              content: Привет! Как дела?
          type: array
          items:
            $ref: '#/components/schemas/MessageDto'
        max_tokens:
          type: number
          description: Максимальное количество токенов для генерации
          example: 1000
          minimum: 1
        max_completion_tokens:
          type: number
          description: >-
            Максимальное количество токенов для completion (альтернатива
            max_tokens)
          example: 1000
          minimum: 1
        temperature:
          type: number
          description: >-
            Температура сэмплинга (0-2). Более высокие значения делают вывод
            более случайным
          example: 1
          minimum: 0
          maximum: 2
        top_p:
          type: number
          description: 'Nucleus sampling: вероятностная масса для рассмотрения (0-1)'
          example: 1
          minimum: 0
          maximum: 1
        frequency_penalty:
          type: number
          description: Штраф за частоту использования токенов (-2 до 2)
          example: 0
          minimum: -2
          maximum: 2
        presence_penalty:
          type: number
          description: Штраф за присутствие токенов (-2 до 2)
          example: 0
          minimum: -2
          maximum: 2
        response_format:
          type: object
          description: Формат ответа модели
        provider:
          description: Настройки провайдера для роутинга и фильтрации
          allOf:
            - $ref: '#/components/schemas/ProviderDto'
        tools:
          description: Определения инструментов (tools) для function calling
          type: array
          items:
            $ref: '#/components/schemas/ToolDefinitionDto'
        tool_choice:
          type: object
          description: 'Выбор инструмента: none, auto, required или named function'
          example: auto
        reasoning:
          description: Настройки reasoning для reasoning моделей
          allOf:
            - $ref: '#/components/schemas/ReasoningDto'
        plugins:
          type: array
          description: Плагины для расширения функциональности
        web_search_options:
          description: Настройки встроенного веб-поиска (для моделей с нативной поддержкой)
          allOf:
            - $ref: '#/components/schemas/WebSearchOptionsDto'
        user:
          type: string
          description: >-
            Уникальный идентификатор конечного пользователя для отслеживания и
            предотвращения злоупотреблений
          example: user-123
        stop:
          description: Последовательности, при которых модель прекращает генерацию
          example:
            - |+

          oneOf:
            - type: string
            - type: array
              items:
                type: string
        seed:
          type: number
          description: Seed для детерминированной генерации (best-effort)
          example: 42
        'n':
          type: number
          description: Количество вариантов ответа (1-10)
          example: 1
          minimum: 1
          maximum: 10
        stream:
          type: boolean
          description: Включить потоковую передачу ответа
          example: false
        logprobs:
          type: boolean
          description: Возвращать log probabilities для output токенов
          example: false
        top_logprobs:
          type: number
          description: >-
            Количество наиболее вероятных токенов для возврата (0-20). Требует
            logprobs: true
          example: 5
          minimum: 0
          maximum: 20
        logit_bias:
          type: object
          description: Смещение вероятностей токенов по их ID (-100 до 100)
          example:
            '50256': -100
        parallel_tool_calls:
          type: boolean
          description: Разрешить параллельный вызов нескольких tools
          example: true
        image_config:
          type: object
          description: Настройки обработки изображений
          example:
            quality: high
            size: 512
        modalities:
          type: array
          description: Типы вывода модели
          example:
            - text
            - audio
          items:
            type: string
            enum:
              - text
              - image
              - audio
        audio:
          type: object
          description: >-
            Настройки аудио выхода для моделей с поддержкой аудио (gpt-audio и
            др.)
          properties:
            voice:
              type: string
              example: alloy
              description: Голос для генерации аудио
            format:
              type: string
              example: pcm16
              description: Формат аудио
      required:
        - model
        - messages
    ChatCompletionPresenter:
      type: object
      properties:
        id:
          type: string
          description: Уникальный идентификатор генерации
          example: gen_581761234567890123
        object:
          type: string
          description: Тип объекта
          example: chat.completion
        created:
          type: number
          description: Временная метка создания (Unix timestamp)
          example: 1703001234
        model:
          type: string
          description: ID модели, которая сгенерировала ответ
          example: openai/gpt-4o
        choices:
          description: Массив вариантов ответа
          type: array
          items:
            $ref: '#/components/schemas/ChoicePresenter'
        system_fingerprint:
          type: string
          description: System fingerprint от провайдера
          example: fp_29330a9688
        usage:
          description: Информация об использовании токенов
          allOf:
            - $ref: '#/components/schemas/UsagePresenter'
      required:
        - id
        - object
        - created
        - model
        - choices
    MessageDto:
      type: object
      properties:
        role:
          type: string
          description: Роль отправителя сообщения
          enum:
            - user
            - assistant
            - system
            - developer
            - tool
          example: user
        content:
          type: object
          description: >-
            Содержимое сообщения (строка, массив частей контента или null для
            assistant с tool_calls)
          example: Привет, как дела?
          nullable: true
        name:
          type: string
          description: Имя отправителя (опционально)
          example: Иван
        tool_call_id:
          type: string
          description: ID вызова инструмента (только для role=tool)
          example: call_abc123
        tool_calls:
          description: Массив вызовов инструментов (только для role=assistant)
          type: array
          items:
            $ref: '#/components/schemas/ToolCallDto'
        refusal:
          type: object
          description: >-
            Текст отказа модели от выполнения запроса (только для
            role=assistant)
          example: Я не могу помочь с этим запросом
          nullable: true
        reasoning:
          type: object
          description: Reasoning текст для моделей с reasoning (только для role=assistant)
          example: Для решения этой задачи мне нужно...
          nullable: true
        annotations:
          type: array
          description: >-
            Аннотации из ответа провайдера (для кэширования парсинга PDF и
            других документов)
          items:
            type: object
      required:
        - role
        - content
    ProviderDto:
      type: object
      properties:
        allow_fallbacks:
          type: boolean
          description: Разрешить использование резервных провайдеров
          example: true
        order:
          description: Упорядоченный список slug провайдеров для использования
          example:
            - OpenAI
            - Anthropic
          type: array
          items:
            type: string
        only:
          description: Список разрешенных slug провайдеров
          example:
            - OpenAI
            - Google
          type: array
          items:
            type: string
        ignore:
          description: Список игнорируемых slug провайдеров
          example:
            - DeepInfra
          type: array
          items:
            type: string
        sort:
          type: string
          description: Критерий сортировки провайдеров
          enum:
            - price
            - throughput
            - latency
          example: price
        max_price:
          description: Максимальные цены для запроса
          allOf:
            - $ref: '#/components/schemas/ProviderMaxPriceDto'
    ToolDefinitionDto:
      type: object
      properties:
        type:
          type: string
          description: Тип инструмента
          example: function
          enum:
            - function
        function:
          description: Определение функции
          allOf:
            - $ref: '#/components/schemas/ToolFunctionDto'
      required:
        - type
        - function
    ReasoningDto:
      type: object
      properties:
        effort:
          type: string
          description: Уровень усилий reasoning модели
          enum:
            - xhigh
            - high
            - medium
            - low
            - minimal
            - none
          example: medium
        summary:
          type: string
          description: Уровень детализации резюме reasoning
          enum:
            - auto
            - concise
            - detailed
            - none
          example: auto
        enabled:
          type: boolean
          description: >-
            Включить/выключить reasoning. По умолчанию определяется из effort
            или max_tokens
          example: true
        max_tokens:
          type: number
          description: Максимальное количество токенов для reasoning (стиль Anthropic)
          example: 2000
        exclude:
          type: boolean
          description: >-
            Скрыть reasoning из ответа (модель будет использовать reasoning, но
            не вернёт его)
          example: false
    WebSearchOptionsDto:
      type: object
      properties:
        search_context_size:
          type: string
          description: Размер контекста поиска для моделей со встроенным веб-поиском
          enum:
            - low
            - medium
            - high
          example: medium
    ChoicePresenter:
      type: object
      properties:
        index:
          type: number
          description: Индекс выбора в массиве choices
          example: 0
        message:
          description: Сообщение от модели
          allOf:
            - $ref: '#/components/schemas/MessagePresenter'
        finish_reason:
          type: string
          description: Причина завершения генерации
          example: stop
          enum:
            - stop
            - length
            - content_filter
            - error
            - tool_calls
          nullable: true
        reasoning_details:
          type: array
          description: Детали reasoning процесса (для reasoning моделей)
        logprobs:
          description: Log probabilities для токенов
          nullable: true
          allOf:
            - $ref: '#/components/schemas/ChatMessageTokenLogprobsPresenter'
      required:
        - index
        - message
        - finish_reason
    UsagePresenter:
      type: object
      properties:
        prompt_tokens:
          type: number
          description: Количество токенов в промпте
          example: 10
        completion_tokens:
          type: number
          description: Количество токенов в ответе
          example: 50
        total_tokens:
          type: number
          description: Общее количество токенов (prompt + completion)
          example: 60
        completion_tokens_details:
          description: Детализация токенов completion
          nullable: true
          allOf:
            - $ref: '#/components/schemas/CompletionTokensDetailsPresenter'
        prompt_tokens_details:
          description: Детализация токенов промпта
          nullable: true
          allOf:
            - $ref: '#/components/schemas/PromptTokensDetailsPresenter'
        server_tool_use:
          description: Использование серверных инструментов (web search)
          nullable: true
          allOf:
            - $ref: '#/components/schemas/ServerToolUsePresenter'
        cost_rub:
          type: object
          description: Стоимость запроса в рублях (списано с баланса клиента)
          example: 0.04131306
          nullable: true
        cost:
          type: object
          description: Стоимость запроса в рублях (alias для cost_rub)
          example: 0.04131306
          nullable: true
        plugins:
          type: object
          description: Детализация серверных плагинов
          example:
            masker:
              operations:
                - operation: mask
                  latency_ms: 15
                  cost_rub: 0.001
                - operation: unmask
                  latency_ms: 8
                  cost_rub: 0
              total_cost_rub: 0.001
          nullable: true
        plugin_post_process_error:
          type: boolean
          description: >-
            Ошибка post-process плагинов (ответ возвращён в замаскированном
            виде)
          example: true
      required:
        - prompt_tokens
        - completion_tokens
        - total_tokens
    ToolCallDto:
      type: object
      properties:
        id:
          type: string
          description: Уникальный идентификатор вызова инструмента
          example: call_abc123xyz
        type:
          type: string
          description: Тип вызова инструмента
          enum:
            - function
          example: function
        function:
          description: Информация о вызываемой функции
          allOf:
            - $ref: '#/components/schemas/ToolCallFunctionDto'
      required:
        - id
        - type
        - function
    ProviderMaxPriceDto:
      type: object
      properties:
        prompt:
          type: number
          description: Максимальная цена за промпт токены (RUB за миллион токенов)
          example: 10
        completion:
          type: number
          description: Максимальная цена за completion токены (RUB за миллион токенов)
          example: 20
        image:
          type: number
          description: Максимальная цена за изображение (RUB за штуку)
          example: 5
        audio:
          type: number
          description: Максимальная цена за аудио (RUB за миллион токенов)
          example: 15
        request:
          type: number
          description: Максимальная цена за запрос (RUB за запрос)
          example: 1
    ToolFunctionDto:
      type: object
      properties:
        name:
          type: string
          description: Название функции
          example: get_weather
        description:
          type: string
          description: Описание функции
          example: Получить текущую погоду для указанного местоположения
        parameters:
          type: object
          description: JSON Schema параметров функции
          example:
            type: object
            properties:
              location:
                type: string
                description: Название города
              unit:
                type: string
                enum:
                  - celsius
                  - fahrenheit
            required:
              - location
        strict:
          type: boolean
          description: Строгое соответствие схеме
          example: false
      required:
        - name
    MessagePresenter:
      type: object
      properties:
        role:
          type: string
          description: Роль отправителя сообщения
          example: assistant
        content:
          type: object
          description: Содержимое сообщения
          example: Привет! Я хорошо, спасибо что спросили. Чем могу помочь?
          nullable: true
        name:
          type: object
          description: Имя отправителя
          example: Ассистент
          nullable: true
        tool_calls:
          description: Вызовы инструментов (tool calls)
          type: array
          items:
            $ref: '#/components/schemas/ToolCallPresenter'
        refusal:
          type: object
          description: Отказ модели от выполнения запроса
          example: null
          nullable: true
        reasoning:
          type: object
          description: Reasoning текст (для reasoning моделей)
          example: null
          nullable: true
        audio:
          type: object
          description: Аудио данные (для моделей с audio output)
          properties:
            id:
              type: string
              description: ID аудио
            data:
              type: string
              description: Base64-encoded аудио данные
            transcript:
              type: string
              description: Текстовая расшифровка
            expires_at:
              type: number
              description: Unix timestamp истечения
        annotations:
          type: array
          description: Аннотации (ссылки на источники от web search)
          items:
            type: object
      required:
        - role
        - content
    ChatMessageTokenLogprobsPresenter:
      type: object
      properties:
        content:
          description: Log probabilities для контента
          nullable: true
          type: array
          items:
            $ref: '#/components/schemas/ChatMessageTokenLogprobPresenter'
        refusal:
          description: Log probabilities для refusal
          nullable: true
          type: array
          items:
            $ref: '#/components/schemas/ChatMessageTokenLogprobPresenter'
      required:
        - content
        - refusal
    CompletionTokensDetailsPresenter:
      type: object
      properties:
        reasoning_tokens:
          type: object
          description: Токены reasoning (для reasoning моделей)
          example: 100
          nullable: true
        audio_tokens:
          type: object
          description: Аудио токены в ответе
          example: 0
          nullable: true
        image_tokens:
          type: object
          description: Токены изображений в ответе
          example: 0
          nullable: true
        accepted_prediction_tokens:
          type: object
          description: Принятые токены предсказаний
          example: 0
          nullable: true
        rejected_prediction_tokens:
          type: object
          description: Отклоненные токены предсказаний
          example: 0
          nullable: true
    PromptTokensDetailsPresenter:
      type: object
      properties:
        cached_tokens:
          type: number
          description: Кэшированные токены
          example: 0
        audio_tokens:
          type: number
          description: Аудио токены в промпте
          example: 0
        video_tokens:
          type: number
          description: Видео токены в промпте
          example: 0
    ServerToolUsePresenter:
      type: object
      properties:
        web_search_requests:
          type: number
          description: Количество вызовов веб-поиска
          example: 1
    ToolCallFunctionDto:
      type: object
      properties:
        name:
          type: string
          description: Имя вызываемой функции
          example: get_weather
        arguments:
          type: string
          description: JSON-строка с аргументами функции
          example: '{"location": "Moscow", "unit": "celsius"}'
      required:
        - name
        - arguments
    ToolCallPresenter:
      type: object
      properties:
        id:
          type: string
          description: ID вызова функции
          example: call_abc123
        type:
          type: string
          description: Тип вызова
          example: function
        function:
          description: Информация о функции
          allOf:
            - $ref: '#/components/schemas/ToolCallFunctionPresenter'
      required:
        - id
        - type
        - function
    ChatMessageTokenLogprobPresenter:
      type: object
      properties:
        token:
          type: string
          description: Токен
          example: hello
        logprob:
          type: number
          description: Log probability токена
          example: -0.5
        bytes:
          type: object
          description: Байты токена
          example:
            - 104
            - 101
            - 108
            - 108
            - 111
          nullable: true
        top_logprobs:
          description: Топ наиболее вероятных токенов с их вероятностями
          type: array
          items:
            $ref: '#/components/schemas/ChatMessageTokenLogprobTopItemPresenter'
      required:
        - token
        - logprob
        - bytes
        - top_logprobs
    ToolCallFunctionPresenter:
      type: object
      properties:
        name:
          type: string
          description: Название функции
          example: get_weather
        arguments:
          type: string
          description: Аргументы функции в JSON формате
          example: '{"location": "Moscow"}'
      required:
        - name
        - arguments
    ChatMessageTokenLogprobTopItemPresenter:
      type: object
      properties:
        token:
          type: string
          description: Токен
          example: hello
        logprob:
          type: number
          description: Log probability токена
          example: -0.5
        bytes:
          type: object
          description: Байты токена
          example:
            - 104
            - 101
            - 108
            - 108
            - 111
          nullable: true
      required:
        - token
        - logprob
        - bytes
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <POLZA_AI_API_KEY>

````

> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# POST Images Generations

> Генерация изображений (OpenAI-совместимый API)

OpenAI-совместимый эндпоинт для генерации изображений. Поддерживает формат запросов GPT image models, DALL-E 3, DALL-E 2.

<Info>
  Этот эндпоинт совместим с OpenAI SDK и подходит для быстрой миграции существующего кода.
  Если вы разрабатываете новый софт — рекомендуем использовать [Media API](/api-reference/media/create), который предоставляет единый интерфейс для всех медиа-операций.
</Info>

<Note>
  Этот эндпоинт доступен по пути `/v2/images/generations`. При использовании OpenAI SDK с `base_url="https://polza.ai/api/v1"` запросы автоматически направляются на правильный путь.
</Note>

## Параметры

### Обязательные

| Параметр | Тип    | Описание                                               |
| -------- | ------ | ------------------------------------------------------ |
| `model`  | string | Модель для генерации (например, gpt-image-1, dall-e-3) |
| `prompt` | string | Текстовое описание изображения                         |

### Опциональные

| Параметр          | Тип            | По умолчанию | Описание                                |
| ----------------- | -------------- | ------------ | --------------------------------------- |
| `n`               | integer (1-10) | 1            | Количество изображений                  |
| `size`            | string         | auto         | Размер изображения                      |
| `quality`         | string         | auto         | Качество генерации                      |
| `response_format` | string         | url          | Формат ответа: url, b64\_json           |
| `style`           | string         | vivid        | Стиль: vivid, natural (только DALL-E 3) |
| `user`            | string         | —            | Идентификатор конечного пользователя    |

### size

Размер генерируемого изображения:

| Значение    | Описание                                      |
| ----------- | --------------------------------------------- |
| `auto`      | Провайдер сам определит размер (по умолчанию) |
| `256x256`   | Маленький квадрат                             |
| `512x512`   | Средний квадрат                               |
| `1024x1024` | Большой квадрат                               |
| `1536x1024` | Горизонтальный                                |
| `1024x1536` | Вертикальный                                  |
| `1792x1024` | Широкий горизонтальный                        |
| `1024x1792` | Высокий вертикальный                          |

### quality

Качество генерации:

| Значение   | Описание                            |
| ---------- | ----------------------------------- |
| `auto`     | Автоматический выбор (по умолчанию) |
| `low`      | Низкое качество (быстрее)           |
| `medium`   | Среднее качество                    |
| `high`     | Высокое качество                    |
| `standard` | Стандартное (для DALL-E)            |
| `hd`       | HD качество (для DALL-E 3)          |

## Примеры

<CodeGroup>
  ```bash cURL theme={null}
  curl -X POST "https://polza.ai/api/v2/images/generations" \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gpt-image-1",
      "prompt": "Космический пейзаж с планетами",
      "size": "1024x1024",
      "quality": "high"
    }'
  ```

  ```python Python theme={null}
  from openai import OpenAI

  client = OpenAI(
      base_url="https://polza.ai/api/v1",
      api_key="YOUR_API_KEY"
  )

  response = client.images.generate(
      model="gpt-image-1",
      prompt="Футуристический город на закате",
      size="1792x1024",
      quality="high",
      n=1
  )

  print(response.data[0].url)
  ```
</CodeGroup>

## Поведение при таймауте

Генерация выполняется синхронно с таймаутом **120 секунд**.

### Успешная генерация (до 120 сек)

Возвращается объект с результатом:

```json  theme={null}
{
  "created": 1706123456,
  "data": [
    {
      "url": "https://cdn.polza.ai/...",
      "revised_prompt": "Улучшенный промпт..."
    }
  ],
  "usage": {
    "input_tokens": 10,
    "output_tokens": 0,
    "total_tokens": 10,
    "cost_rub": 2.50,
    "cost": 2.50
  }
}
```

### Таймаут (более 120 сек)

Если генерация не успевает завершиться за 120 секунд, запрос автоматически переходит в асинхронный режим:

```json  theme={null}
{
  "id": "gen_abc123...",
  "status": "pending",
  "model": "dall-e-3",
  "created": 1706123456
}
```

Используйте [`GET /v1/media/{id}`](/api-reference/media/status) для проверки статуса. Рекомендуется polling с интервалом 3-5 секунд.

## Статусы генерации

| Статус       | Описание              |
| ------------ | --------------------- |
| `pending`    | В очереди             |
| `processing` | Генерация выполняется |
| `completed`  | Готово                |
| `failed`     | Ошибка                |


## OpenAPI

````yaml POST /v2/images/generations
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v2/images/generations:
    post:
      tags:
        - Изображения
      summary: Создать генерацию изображения (OpenAI-совместимый API)
      operationId: ImagesController_createGeneration[1]
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ImageGenerationRequestDto'
      responses:
        '200':
          description: >-
            Успешная генерация изображения. При таймауте (>120 сек) возвращается
            ImagePendingResponsePresenter с taskId для проверки статуса через
            GET /v2/media/{id}
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ImageGenerationResponsePresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    ImageGenerationRequestDto:
      type: object
      properties:
        model:
          type: string
          description: ID модели для генерации изображений
          example: dall-e-3
        prompt:
          type: string
          description: >-
            Текстовое описание изображения для генерации (до 32000 символов для
            GPT image models, 4000 для dall-e-3)
          example: A white siamese cat sitting on a windowsill
        'n':
          type: number
          description: Количество генерируемых изображений (1-10, для dall-e-3 только 1)
          example: 1
          default: 1
          minimum: 1
          maximum: 10
        size:
          type: string
          description: Размер генерируемого изображения. auto для GPT image models
          enum:
            - auto
            - 256x256
            - 512x512
            - 1024x1024
            - 1536x1024
            - 1024x1536
            - 1792x1024
            - 1024x1792
          example: auto
          default: auto
        quality:
          type: string
          description: >-
            Качество изображения. auto/high/medium/low для GPT image models,
            hd/standard для DALL-E
          enum:
            - auto
            - low
            - medium
            - high
            - standard
            - hd
          example: auto
          default: auto
        response_format:
          type: string
          description: Формат ответа - URL или base64-encoded JSON
          enum:
            - url
            - b64_json
          example: url
          default: url
        style:
          type: string
          description: Стиль изображения (только для dall-e-3)
          enum:
            - vivid
            - natural
          example: vivid
          default: vivid
        output_format:
          type: string
          description: Формат выходного изображения (для gpt-image-1)
          enum:
            - png
            - jpeg
            - webp
          example: png
        background:
          type: string
          description: 'Фон изображения: transparent, opaque или auto (для gpt-image-1)'
          enum:
            - transparent
            - opaque
            - auto
          example: auto
        output_compression:
          type: number
          description: Степень сжатия выходного изображения (0-100, для gpt-image-1)
          example: 75
          minimum: 0
          maximum: 100
        user:
          type: string
          description: >-
            Уникальный идентификатор конечного пользователя для отслеживания и
            предотвращения злоупотреблений
          example: user-123
      required:
        - model
        - prompt
    ImageGenerationResponsePresenter:
      type: object
      properties:
        created:
          type: number
          description: Unix timestamp времени создания
          example: 1589478378
        data:
          description: Массив сгенерированных изображений
          type: array
          items:
            $ref: '#/components/schemas/ImageDataPresenter'
        usage:
          description: Информация об использовании ресурсов
          allOf:
            - $ref: '#/components/schemas/MediaUsagePresenter'
      required:
        - created
        - data
    ImageDataPresenter:
      type: object
      properties:
        url:
          type: string
          description: URL сгенерированного изображения (если response_format=url)
          example: https://oaidalleapiprodscus.blob.core.windows.net/...
        b64_json:
          type: string
          description: Base64-encoded изображение (если response_format=b64_json)
          example: iVBORw0KGgoAAAANSUhEUgAAAAUA...
        revised_prompt:
          type: string
          description: Пересмотренный промпт (для dall-e-3)
          example: >-
            A fluffy white siamese cat with blue eyes sitting peacefully on a
            wooden windowsill...
    MediaUsagePresenter:
      type: object
      properties:
        input_units:
          type: number
          description: Входные единицы (для edit mode)
          example: 1
        output_units:
          type: number
          description: Выходные единицы (сгенерированные)
          example: 1
        duration_seconds:
          type: number
          description: Длительность для видео/аудио (секунды)
          example: 5
        input_tokens:
          type: number
          description: Количество входных токенов
          example: 10
        output_tokens:
          type: number
          description: Количество выходных токенов
          example: 0
        total_tokens:
          type: number
          description: Общее количество токенов
          example: 10
        cost_rub:
          type: number
          description: Стоимость в рублях
          example: 1.5
        cost:
          type: number
          description: Стоимость в рублях (alias для cost_rub)
          example: 1.5
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <POLZA_AI_API_KEY>

````

Built with [Mintlify](https://mintlify.com).
> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# POST Media

> Универсальный API генерации медиа (изображения, видео, аудио)

## О Media API

Универсальный эндпоинт для генерации медиа контента. Поддерживает различные модели и провайдеров через единый интерфейс.

### Общие параметры

| Параметр   | Тип     | Обязательный | Описание                                |
| ---------- | ------- | ------------ | --------------------------------------- |
| `model`    | string  | Да           | ID модели для генерации                 |
| `input`    | object  | Да           | Параметры генерации (зависят от модели) |
| `async`    | boolean | Нет          | Принудительный асинхронный режим        |
| `user`     | string  | Нет          | Идентификатор конечного пользователя    |
| `provider` | object  | Нет          | Конфигурация роутинга по провайдерам    |

### Передача файлов (URL и base64)

Для моделей, поддерживающих image-to-image или video-to-video, медиа файлы передаются в массиве `images` или `videos`. Каждый элемент — объект с полями:

| Поле   | Тип                   | Описание                                         |
| ------ | --------------------- | ------------------------------------------------ |
| `type` | `"url"` \| `"base64"` | Формат данных                                    |
| `data` | string                | URL файла или base64-строка (с data URI или без) |

#### Пример с base64

```bash  theme={null}
curl -X POST "https://polza.ai/api/v1/media" \
  -H "Authorization: Bearer <POLZA_AI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "seedream-3",
    "input": {
      "prompt": "Сделай изображение ярче и добавь закат на фоне",
      "images": [
        {
          "type": "base64",
          "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg..."
        }
      ]
    }
  }'
```

Можно комбинировать URL и base64 в одном запросе:

```json  theme={null}
{
  "model": "gpt-image-1",
  "input": {
    "prompt": "Объедини эти изображения в коллаж",
    "images": [
      { "type": "url", "data": "https://example.com/photo1.png" },
      { "type": "base64", "data": "data:image/jpeg;base64,/9j/4AAQSkZJRg..." }
    ]
  }
}
```

<Note>
  Base64 поддерживается как с data URI (`data:image/png;base64,...`), так и без — просто строка base64.
  Если провайдер не поддерживает base64 напрямую, файл автоматически загружается в хранилище и передаётся как URL.
</Note>

### Типы контента

* Изображения (Nano Banana, Seedream, GPT Image и др.)
* Видео (Veo, Wan, Kling, Seedance, Sora и др.)
* Аудио — синтез речи (TTS) и распознавание речи (STT)

### Хранение результатов

При генерации медиа контента Polza.ai автоматически:

1. **Скачивает результат** у AI провайдера на собственное хранилище
2. **Хранит файлы 7 дней** для повторного доступа
3. **Раздаёт через CDN** для быстрого доступа внутри России

<Note>
  После истечения 7 дней файлы автоматически удаляются.
  Для постоянного хранения используйте [Storage API](/api-reference/storage/upload) с политикой `PERMANENT`.
</Note>

***

## Руководства по моделям

Подробные примеры, параметры и особенности каждой модели — в руководствах:

<CardGroup cols={3}>
  <Card title="Видео" icon="video" href="/gaidy/veo-3-1">
    Veo 3.1, Wan 2.5/2.6, Kling, Seedance, Sora и другие модели видеогенерации
  </Card>

  <Card title="Изображения" icon="image" href="/gaidy/seedream-4-5">
    Seedream, Nano Banana, GPT Image, Flux, Grok Imagine и другие модели генерации изображений
  </Card>

  <Card title="Аудио" icon="volume-high" href="/gaidy/elevenlabs-tts-turbo">
    ElevenLabs TTS и другие модели синтеза и распознавания речи
  </Card>
</CardGroup>

***

## Ответ

Возвращает объект [Media Status](/api-reference/media/status) со статусом `pending`:

```json  theme={null}
{
  "id": "aig_abc123",
  "object": "media.generation",
  "status": "pending",
  "created": 1703001244,
  "model": "google/veo3"
}
```

Используйте [GET /v1/media/{id}](/api-reference/media/status) для проверки статуса и получения результата.


## OpenAPI

````yaml POST /v1/media
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/media:
    post:
      tags:
        - Медиа
      summary: Создать генерацию медиа
      operationId: MediaController_createGeneration[1]
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MediaRequestDto'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaStatusPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaRequestDto:
      type: object
      properties:
        model:
          type: string
          description: ID модели для генерации
          example: seedream-3
        input:
          description: Входные параметры генерации
          oneOf:
            - title: Изображение
              allOf:
                - $ref: '#/components/schemas/ImageInputDto'
            - title: Видео
              allOf:
                - $ref: '#/components/schemas/VideoInputDto'
            - title: Аудио (TTS)
              allOf:
                - $ref: '#/components/schemas/AudioInputDto'
            - title: Музыка
              allOf:
                - $ref: '#/components/schemas/MusicInputDto'
        provider:
          description: Настройки роутинга провайдеров
          allOf:
            - $ref: '#/components/schemas/ProviderDto'
        async:
          type: boolean
          description: >-
            Асинхронный режим генерации. При true возвращается taskId для опроса
            статуса
          example: false
          default: false
        user:
          type: string
          description: >-
            Уникальный идентификатор конечного пользователя для отслеживания и
            предотвращения злоупотреблений
          example: user-123
      required:
        - model
        - input
    MediaStatusPresenter:
      type: object
      properties:
        id:
          type: string
          description: Уникальный идентификатор генерации
          example: gen_581761234567890123
        object:
          type: string
          description: Тип объекта
          example: media.generation
        status:
          type: string
          description: Статус генерации
          enum:
            - pending
            - processing
            - completed
            - failed
            - cancelled
          example: pending
        created:
          type: number
          description: Временная метка создания (Unix timestamp)
          example: 1703001234
        model:
          type: string
          description: ID модели, которая генерирует контент
          example: google/gemini-2.5-flash-image
        completed_at:
          type: number
          description: Временная метка завершения (Unix timestamp)
          example: 1703001244
        data:
          description: Данные сгенерированного контента
          oneOf:
            - f0b5f590-8eb4-48fc-8015-8135c9728cb9
            - 0aa6ced1-d3d4-4d7c-93ed-d1a62b544056
            - 9e81fd8b-ea9e-4b31-b2cb-d89cab11ea4d
        usage:
          description: Информация об использовании ресурсов
          allOf:
            - $ref: '#/components/schemas/MediaUsagePresenter'
        error:
          description: Информация об ошибке (если failed)
          allOf:
            - $ref: '#/components/schemas/MediaErrorPresenter'
        content:
          type: string
          description: >-
            Текстовый ответ модели (если вернула текст вместо/вместе с
            изображением)
          example: Банан и яблоко — это фрукты.
        reasoning_summary:
          type: string
          description: Краткое резюме рассуждений модели
          example: Preparing image generation prompt with camera settings...
        warnings:
          description: Предупреждения (неподдерживаемые параметры и т.д.)
          example:
            - >-
              Параметр isEnhance не поддерживается OpenRouter и будет
              проигнорирован
          type: array
          items:
            type: string
      required:
        - id
        - object
        - status
        - created
        - model
    ImageInputDto:
      type: object
      properties:
        prompt:
          type: string
          description: Текстовое описание
          example: Космический корабль в стиле киберпанк
        aspect_ratio:
          type: string
          description: Соотношение сторон
          example: '16:9'
          enum:
            - '1:1'
            - '2:3'
            - '3:2'
            - '3:4'
            - '4:3'
            - '4:5'
            - '5:4'
            - '9:16'
            - '16:9'
            - '21:9'
            - auto
        images:
          description: Медиа файлы для обработки
          type: array
          items:
            $ref: '#/components/schemas/MediaFileDto'
        callBackUrl:
          type: string
          description: URL для callback уведомлений
        seed:
          type: number
          description: Зерно генерации для воспроизводимости
          example: 42
        watermark:
          type: string
          description: Текст водяного знака
          example: MyBrand
        image_resolution:
          type: string
          description: Разрешение изображения
          enum:
            - 1K
            - 2K
            - 4K
          example: 2K
        quality:
          type: string
          description: Качество
          enum:
            - basic
            - medium
            - high
          example: high
        output_format:
          type: string
          description: >-
            Формат выходного изображения (jpg автоматически преобразуется в
            jpeg)
          enum:
            - png
            - jpeg
            - webp
          example: png
        max_images:
          type: number
          description: Количество изображений
          example: 1
          minimum: 1
          maximum: 6
        isEnhance:
          type: boolean
          description: Улучшить промпт для более качественного результата (GPT-Image-1)
          example: false
        guidance_scale:
          type: number
          description: Масштаб управления генерацией (CFG scale)
          example: 2.5
        strength:
          type: number
          description: Сила трансформации для image-to-image (0-1)
          example: 0.8
        enable_safety_checker:
          type: boolean
          description: Включить проверку безопасности
          example: true
        upscale_factor:
          type: string
          description: Коэффициент увеличения (для upscale моделей)
          enum:
            - '1'
            - '2'
            - '4'
            - '8'
          example: '2'
        font_inputs:
          description: >-
            Входные шрифты для рендеринга текста (только Sourceful Riverflow V2
            Fast/Pro, макс. 2)
          type: array
          items:
            $ref: '#/components/schemas/FontInputDto'
        super_resolution_references:
          description: >-
            URL высококачественных референсов для super resolution (только
            Sourceful Riverflow, макс. 4)
          example:
            - https://example.com/reference1.jpg
          type: array
          items:
            type: string
      required:
        - prompt
    VideoInputDto:
      type: object
      properties:
        prompt:
          type: string
          description: Текстовое описание
          example: Космический корабль в стиле киберпанк
        aspect_ratio:
          type: string
          description: Соотношение сторон
          example: '16:9'
          enum:
            - '1:1'
            - '2:3'
            - '3:2'
            - '3:4'
            - '4:3'
            - '4:5'
            - '5:4'
            - '9:16'
            - '16:9'
            - '21:9'
            - auto
        images:
          description: Медиа файлы для обработки
          type: array
          items:
            $ref: '#/components/schemas/MediaFileDto'
        callBackUrl:
          type: string
          description: URL для callback уведомлений
        seed:
          type: number
          description: Зерно генерации для воспроизводимости
          example: 42
        watermark:
          type: string
          description: Текст водяного знака
          example: MyBrand
        duration:
          type: string
          description: Длительность видео
          enum:
            - 10s
            - 15s
          example: 10s
        resolution:
          type: string
          description: Разрешение видео
          enum:
            - 480p
            - 580p
            - 720p
            - 1080p
          example: 720p
        videos:
          description: Видео файлы для обработки
          type: array
          items:
            $ref: '#/components/schemas/MediaFileDto'
        multi_shots:
          type: boolean
          description: Режим мульти-шотов (Wan 2.6, Kling 3.0)
        sound:
          type: boolean
          description: Генерация звука (Kling 2.6, Kling 3.0)
        mode:
          type: string
          description: >-
            Режим генерации (std/pro для Kling 3.0, 720p/1080p для Motion
            Control)
        character_orientation:
          type: string
          description: Ориентация персонажа (Kling 2.6 Motion Control)
          enum:
            - image
            - video
        upscale_factor:
          type: string
          description: Коэффициент увеличения (для video upscale моделей)
          enum:
            - '1'
            - '2'
            - '4'
          example: '2'
      required:
        - prompt
    AudioInputDto:
      type: object
      properties:
        prompt:
          type: string
          description: Текст для синтеза речи
          example: Привет, как дела?
          maxLength: 5000
        text:
          type: string
          description: Текст для синтеза (алиас для prompt, имеет приоритет)
          example: Привет, как дела?
          maxLength: 5000
        voice:
          type: string
          description: Голос для синтеза
          example: Rachel
        stability:
          type: number
          description: Стабильность голоса (0-1)
          example: 0.5
        similarity_boost:
          type: number
          description: Усиление схожести (0-1)
          example: 0.75
        style:
          type: number
          description: Экспрессия стиля (0-1)
          example: 0
        speed:
          type: number
          description: Скорость речи (0.7-1.2)
          example: 1
        timestamps:
          type: boolean
          description: Включить временные метки слов
          example: false
        previous_text:
          type: string
          description: Предшествующий текст для контекста (до 5000 символов)
          maxLength: 5000
        next_text:
          type: string
          description: Последующий текст для контекста (до 5000 символов)
          maxLength: 5000
        language_code:
          type: string
          description: Код языка ISO 639-1 (только для Turbo 2.5)
          example: ru
        callBackUrl:
          type: string
          description: URL для callback уведомлений
      required:
        - prompt
    MusicInputDto:
      type: object
      properties:
        prompt:
          type: string
          description: >-
            Описание трека или текст песни (lyrics в custom mode). В обычном
            режиме — до 500 символов, в custom mode — до 5000
          example: Спокойная инструментальная музыка для медитации
          maxLength: 5000
        customMode:
          type: boolean
          description: Режим расширенной настройки (требует style и title)
          example: true
        instrumental:
          type: boolean
          description: Инструментальная музыка без вокала
          example: false
        style:
          type: string
          description: Жанр/стиль музыки (обязателен в custom mode)
          example: Pop, Electronic
          maxLength: 1000
        title:
          type: string
          description: Название трека (обязателен в custom mode)
          example: Peaceful Meditation
          maxLength: 80
        negativeTags:
          type: string
          description: Стили для исключения из генерации
          example: Heavy Metal, Screamo
        vocalGender:
          type: string
          description: Пол вокалиста
          enum:
            - m
            - f
          example: f
        styleWeight:
          type: number
          description: Сила следования стилю (0-1)
          example: 0.65
        weirdnessConstraint:
          type: number
          description: Уровень экспериментальности (0-1)
          example: 0.3
        audioWeight:
          type: number
          description: Баланс аудиофункций (0-1)
          example: 0.5
        personaId:
          type: string
          description: ID персоны для применения стиля
        version:
          type: string
          description: Версия модели Suno
          enum:
            - V5
            - V4_5ALL
            - V4_5PLUS
            - V4_5
            - V4
            - V3_5
          example: V5
        callBackUrl:
          type: string
          description: URL для callback уведомлений
      required:
        - prompt
    ProviderDto:
      type: object
      properties:
        allow_fallbacks:
          type: boolean
          description: Разрешить использование резервных провайдеров
          example: true
        order:
          description: Упорядоченный список slug провайдеров для использования
          example:
            - OpenAI
            - Anthropic
          type: array
          items:
            type: string
        only:
          description: Список разрешенных slug провайдеров
          example:
            - OpenAI
            - Google
          type: array
          items:
            type: string
        ignore:
          description: Список игнорируемых slug провайдеров
          example:
            - DeepInfra
          type: array
          items:
            type: string
        sort:
          type: string
          description: Критерий сортировки провайдеров
          enum:
            - price
            - throughput
            - latency
          example: price
        max_price:
          description: Максимальные цены для запроса
          allOf:
            - $ref: '#/components/schemas/ProviderMaxPriceDto'
    MediaUsagePresenter:
      type: object
      properties:
        input_units:
          type: number
          description: Входные единицы (для edit mode)
          example: 1
        output_units:
          type: number
          description: Выходные единицы (сгенерированные)
          example: 1
        duration_seconds:
          type: number
          description: Длительность для видео/аудио (секунды)
          example: 5
        input_tokens:
          type: number
          description: Количество входных токенов
          example: 10
        output_tokens:
          type: number
          description: Количество выходных токенов
          example: 0
        total_tokens:
          type: number
          description: Общее количество токенов
          example: 10
        cost_rub:
          type: number
          description: Стоимость в рублях
          example: 1.5
        cost:
          type: number
          description: Стоимость в рублях (alias для cost_rub)
          example: 1.5
    MediaErrorPresenter:
      type: object
      properties:
        code:
          type: string
          description: Код ошибки (FORBIDDEN, BAD_GATEWAY, REQUEST_TIMEOUT и т.д.)
          example: BAD_GATEWAY
        message:
          type: string
          description: Сообщение об ошибке на русском языке
          example: Ошибка генерации медиа контента
      required:
        - code
        - message
    MediaFileDto:
      type: object
      properties:
        type:
          type: string
          enum:
            - url
            - base64
          description: 'Тип данных: url или base64'
          example: url
        data:
          type: string
          description: URL или base64 данные изображения/видео
          example: https://example.com/image.png
      required:
        - type
        - data
    FontInputDto:
      type: object
      properties:
        font_url:
          type: string
          description: URL файла шрифта
          example: https://example.com/fonts/custom-font.ttf
        text:
          type: string
          description: Текст для рендеринга
          example: Hello World
      required:
        - font_url
        - text
    ProviderMaxPriceDto:
      type: object
      properties:
        prompt:
          type: number
          description: Максимальная цена за промпт токены (RUB за миллион токенов)
          example: 10
        completion:
          type: number
          description: Максимальная цена за completion токены (RUB за миллион токенов)
          example: 20
        image:
          type: number
          description: Максимальная цена за изображение (RUB за штуку)
          example: 5
        audio:
          type: number
          description: Максимальная цена за аудио (RUB за миллион токенов)
          example: 15
        request:
          type: number
          description: Максимальная цена за запрос (RUB за запрос)
          example: 1
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <POLZA_AI_API_KEY>

````

Built with [Mintlify](https://mintlify.com).
> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# GET Media Status

> Получение статуса генерации медиа

## Polling

Рекомендуется проверять статус с интервалом 3-5 секунд для изображений и 5-10 секунд для видео.

## Статусы

| Статус       | Описание                            |
| ------------ | ----------------------------------- |
| `pending`    | В очереди                           |
| `processing` | Генерация выполняется               |
| `completed`  | Готово — результат в поле `data`    |
| `failed`     | Ошибка — подробности в поле `error` |

## Ответ (completed)

```json  theme={null}
{
  "id": "aig_abc123",
  "object": "media.generation",
  "status": "completed",
  "created": 1703001244,
  "model": "google/gemini-2.5-flash-image",
  "data": {
    "url": "https://s3.polza.ai/f/205141/2026/03/aig_abc123.jpg"
  },
  "usage": {
    "output_units": 1,
    "cost_rub": 5.00,
    "cost": 5.00
  }
}
```

## Примеры polling

<CodeGroup>
  ```python Python theme={null}
  import requests
  import time

  def wait_for_media(api_key, media_id, interval=5, max_wait=300):
      url = f'https://polza.ai/api/v1/media/{media_id}'
      headers = {'Authorization': f'Bearer {api_key}'}
      elapsed = 0

      while elapsed < max_wait:
          response = requests.get(url, headers=headers)
          data = response.json()

          if data['status'] == 'completed':
              return data
          elif data['status'] == 'failed':
              raise Exception(f"Генерация не удалась: {data.get('error')}")

          time.sleep(interval)
          elapsed += interval

      raise TimeoutError("Превышено время ожидания")

  result = wait_for_media('YOUR_API_KEY', 'aig_abc123')
  print(f"Результат: {result['data']['url']}")
  ```

  ```javascript JavaScript theme={null}
  async function waitForMedia(apiKey, mediaId, interval = 5000, maxWait = 300000) {
    const url = `https://polza.ai/api/v1/media/${mediaId}`;
    let elapsed = 0;

    while (elapsed < maxWait) {
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${apiKey}` }
      });
      const data = await response.json();

      if (data.status === 'completed') return data;
      if (data.status === 'failed') throw new Error(`Ошибка: ${data.error}`);

      await new Promise(resolve => setTimeout(resolve, interval));
      elapsed += interval;
    }

    throw new Error('Превышено время ожидания');
  }
  ```
</CodeGroup>

<Note>
  Результаты хранятся 7 дней на CDN. Для постоянного хранения используйте [Storage API](/api-reference/storage/upload).
</Note>


## OpenAPI

````yaml GET /v1/media/{id}
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/media/{id}:
    get:
      tags:
        - Медиа
      summary: Получить статус генерации
      operationId: MediaController_getGenerationStatus[1]
      parameters:
        - name: id
          required: true
          in: path
          schema:
            type: string
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaStatusPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaStatusPresenter:
      type: object
      properties:
        id:
          type: string
          description: Уникальный идентификатор генерации
          example: gen_581761234567890123
        object:
          type: string
          description: Тип объекта
          example: media.generation
        status:
          type: string
          description: Статус генерации
          enum:
            - pending
            - processing
            - completed
            - failed
            - cancelled
          example: pending
        created:
          type: number
          description: Временная метка создания (Unix timestamp)
          example: 1703001234
        model:
          type: string
          description: ID модели, которая генерирует контент
          example: google/gemini-2.5-flash-image
        completed_at:
          type: number
          description: Временная метка завершения (Unix timestamp)
          example: 1703001244
        data:
          description: Данные сгенерированного контента
          oneOf:
            - f0b5f590-8eb4-48fc-8015-8135c9728cb9
            - 0aa6ced1-d3d4-4d7c-93ed-d1a62b544056
            - 9e81fd8b-ea9e-4b31-b2cb-d89cab11ea4d
        usage:
          description: Информация об использовании ресурсов
          allOf:
            - $ref: '#/components/schemas/MediaUsagePresenter'
        error:
          description: Информация об ошибке (если failed)
          allOf:
            - $ref: '#/components/schemas/MediaErrorPresenter'
        content:
          type: string
          description: >-
            Текстовый ответ модели (если вернула текст вместо/вместе с
            изображением)
          example: Банан и яблоко — это фрукты.
        reasoning_summary:
          type: string
          description: Краткое резюме рассуждений модели
          example: Preparing image generation prompt with camera settings...
        warnings:
          description: Предупреждения (неподдерживаемые параметры и т.д.)
          example:
            - >-
              Параметр isEnhance не поддерживается OpenRouter и будет
              проигнорирован
          type: array
          items:
            type: string
      required:
        - id
        - object
        - status
        - created
        - model
    MediaUsagePresenter:
      type: object
      properties:
        input_units:
          type: number
          description: Входные единицы (для edit mode)
          example: 1
        output_units:
          type: number
          description: Выходные единицы (сгенерированные)
          example: 1
        duration_seconds:
          type: number
          description: Длительность для видео/аудио (секунды)
          example: 5
        input_tokens:
          type: number
          description: Количество входных токенов
          example: 10
        output_tokens:
          type: number
          description: Количество выходных токенов
          example: 0
        total_tokens:
          type: number
          description: Общее количество токенов
          example: 10
        cost_rub:
          type: number
          description: Стоимость в рублях
          example: 1.5
        cost:
          type: number
          description: Стоимость в рублях (alias для cost_rub)
          example: 1.5
    MediaErrorPresenter:
      type: object
      properties:
        code:
          type: string
          description: Код ошибки (FORBIDDEN, BAD_GATEWAY, REQUEST_TIMEOUT и т.д.)
          example: BAD_GATEWAY
        message:
          type: string
          description: Сообщение об ошибке на русском языке
          example: Ошибка генерации медиа контента
      required:
        - code
        - message
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <POLZA_AI_API_KEY>

````

Built with [Mintlify](https://mintlify.com).
> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# POST Media Operations

> Выполнение операций над существующими медиа (extend, upscale)

## Операции над медиа

После генерации медиа контента можно выполнять дополнительные операции:

| Операция        | Описание                       | Тип         |
| --------------- | ------------------------------ | ----------- |
| `extend`        | Продление видео                | Асинхронная |
| `upscale_1080p` | Увеличение разрешения до 1080p | Синхронная  |
| `upscale_4k`    | Увеличение разрешения до 4K    | Синхронная  |

## Синхронные vs Асинхронные операции

### Синхронные операции (upscale)

Результат возвращается сразу в поле `data`:

```json  theme={null}
{
  "id": "aig_abc123",
  "object": "media.generation",
  "status": "completed",
  "created": 1703001244,
  "model": "google/gemini-2.5-flash-image",
  "data": {
    "url": "https://storage.polza.ai/video_1080p.mp4"
  }
}
```

### Асинхронные операции (extend)

Создаётся новая генерация со статусом `pending`:

```json  theme={null}
{
  "id": "aig_xyz789",
  "object": "media.generation",
  "status": "pending",
  "created": 1703001244,
  "model": "pending"
}
```

Для получения результата используйте [GET /v1/media/{id}](/api-reference/media/status) с новым ID.

### Параметр async

* `async: false` (по умолчанию) — ждёт результат до 120 секунд
* `async: true` — сразу возвращает ID новой генерации

## Примеры

### Продление видео (extend)

```bash  theme={null}
curl -X POST "https://polza.ai/api/v1/media/aig_abc123/operations" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "extend",
    "params": {
      "prompt": "Камера отдаляется, показывая панораму города"
    }
  }'
```

### Увеличение разрешения (upscale)

```bash  theme={null}
curl -X POST "https://polza.ai/api/v1/media/aig_abc123/operations" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "operation": "upscale_1080p"
  }'
```

## Параметры операции extend

| Параметр   | Тип    | Обязательный | Описание                          |
| ---------- | ------ | ------------ | --------------------------------- |
| `prompt`   | string | Да           | Промпт для продолжения видео      |
| `seeds`    | number | Нет          | Seed для воспроизводимости        |
| `duration` | number | Нет          | Длительность продления (3-10 сек) |

<Note>
  Операция extend создаёт новую генерацию с новым ID.
  Оригинальное видео не изменяется.
</Note>


## OpenAPI

````yaml POST /v1/media/{id}/operations
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/media/{id}/operations:
    post:
      tags:
        - Медиа
      summary: Выполнить операцию над медиа
      operationId: MediaController_executeOperation[1]
      parameters:
        - name: id
          required: true
          in: path
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MediaOperationRequestDto'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaStatusPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaOperationRequestDto:
      type: object
      properties:
        operation:
          type: string
          description: ID операции
          example: extend
          enum:
            - extend
            - upscale_1080p
            - upscale_4k
        params:
          type: object
          description: Параметры операции. Зависят от типа операции.
          example:
            prompt: Продолжение сцены
            seeds: 12345
        async:
          type: boolean
          description: >-
            Асинхронный режим. При true сразу возвращает ID операции, результат
            получить через GET /v2/media/:id
          example: false
          default: false
      required:
        - operation
    MediaStatusPresenter:
      type: object
      properties:
        id:
          type: string
          description: Уникальный идентификатор генерации
          example: gen_581761234567890123
        object:
          type: string
          description: Тип объекта
          example: media.generation
        status:
          type: string
          description: Статус генерации
          enum:
            - pending
            - processing
            - completed
            - failed
            - cancelled
          example: pending
        created:
          type: number
          description: Временная метка создания (Unix timestamp)
          example: 1703001234
        model:
          type: string
          description: ID модели, которая генерирует контент
          example: google/gemini-2.5-flash-image
        completed_at:
          type: number
          description: Временная метка завершения (Unix timestamp)
          example: 1703001244
        data:
          description: Данные сгенерированного контента
          oneOf:
            - f0b5f590-8eb4-48fc-8015-8135c9728cb9
            - 0aa6ced1-d3d4-4d7c-93ed-d1a62b544056
            - 9e81fd8b-ea9e-4b31-b2cb-d89cab11ea4d
        usage:
          description: Информация об использовании ресурсов
          allOf:
            - $ref: '#/components/schemas/MediaUsagePresenter'
        error:
          description: Информация об ошибке (если failed)
          allOf:
            - $ref: '#/components/schemas/MediaErrorPresenter'
        content:
          type: string
          description: >-
            Текстовый ответ модели (если вернула текст вместо/вместе с
            изображением)
          example: Банан и яблоко — это фрукты.
        reasoning_summary:
          type: string
          description: Краткое резюме рассуждений модели
          example: Preparing image generation prompt with camera settings...
        warnings:
          description: Предупреждения (неподдерживаемые параметры и т.д.)
          example:
            - >-
              Параметр isEnhance не поддерживается OpenRouter и будет
              проигнорирован
          type: array
          items:
            type: string
      required:
        - id
        - object
        - status
        - created
        - model
    MediaUsagePresenter:
      type: object
      properties:
        input_units:
          type: number
          description: Входные единицы (для edit mode)
          example: 1
        output_units:
          type: number
          description: Выходные единицы (сгенерированные)
          example: 1
        duration_seconds:
          type: number
          description: Длительность для видео/аудио (секунды)
          example: 5
        input_tokens:
          type: number
          description: Количество входных токенов
          example: 10
        output_tokens:
          type: number
          description: Количество выходных токенов
          example: 0
        total_tokens:
          type: number
          description: Общее количество токенов
          example: 10
        cost_rub:
          type: number
          description: Стоимость в рублях
          example: 1.5
        cost:
          type: number
          description: Стоимость в рублях (alias для cost_rub)
          example: 1.5
    MediaErrorPresenter:
      type: object
      properties:
        code:
          type: string
          description: Код ошибки (FORBIDDEN, BAD_GATEWAY, REQUEST_TIMEOUT и т.д.)
          example: BAD_GATEWAY
        message:
          type: string
          description: Сообщение об ошибке на русском языке
          example: Ошибка генерации медиа контента
      required:
        - code
        - message
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <POLZA_AI_API_KEY>

````

Built with [Mintlify](https://mintlify.com).
> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# POST Audio Transcriptions

> Транскрибация аудио в текст (Speech-to-Text)

<Info>
  Этот эндпоинт совместим с OpenAI SDK и подходит для быстрой миграции существующего кода.
  Если вы разрабатываете новый софт — рекомендуем использовать [Media API](/api-reference/media/create), который предоставляет единый интерфейс для всех медиа-операций.
</Info>

## Доступные модели

| Модель                 | ID                              | Описание                                  |
| ---------------------- | ------------------------------- | ----------------------------------------- |
| Whisper 1              | `openai/whisper-1`              | Классическая модель OpenAI (по умолчанию) |
| GPT-4o Transcribe      | `openai/gpt-4o-transcribe`      | Улучшенная транскрибация                  |
| GPT-4o Mini Transcribe | `openai/gpt-4o-mini-transcribe` | Быстрая версия                            |

## Параметры запроса

| Параметр                  | Тип     | Обязательный | Описание                                             |
| ------------------------- | ------- | ------------ | ---------------------------------------------------- |
| `file`                    | string  | Да           | Аудиофайл в формате base64 или URL                   |
| `model`                   | string  | Нет          | Модель транскрибации (по умолчанию openai/whisper-1) |
| `language`                | string  | Нет          | Код языка ISO-639-1 (например, "ru")                 |
| `temperature`             | number  | Нет          | Температура (0-1, по умолчанию 0)                    |
| `response_format`         | string  | Нет          | Формат ответа (по умолчанию json)                    |
| `prompt`                  | string  | Нет          | Подсказка для модели                                 |
| `timestamp_granularities` | array   | Нет          | Детализация: "word", "segment"                       |
| `stream`                  | boolean | Нет          | Потоковый режим                                      |
| `user`                    | string  | Нет          | Идентификатор конечного пользователя                 |

### Продвинутые параметры

| Параметр                   | Тип    | Описание                                               |
| -------------------------- | ------ | ------------------------------------------------------ |
| `chunking_strategy`        | object | Стратегия разбивки (для gpt-4o-transcribe)             |
| `include`                  | array  | Дополнительные данные: "logprobs"                      |
| `known_speaker_names`      | array  | Имена известных спикеров (макс. 4, для diarized\_json) |
| `known_speaker_references` | array  | Аудио-примеры голосов спикеров (data URLs)             |

### Форматы ответа

| Формат          | Описание                                 |
| --------------- | ---------------------------------------- |
| `json`          | Простой JSON с текстом (по умолчанию)    |
| `text`          | Только текст                             |
| `srt`           | Формат субтитров SRT                     |
| `vtt`           | Формат субтитров WebVTT                  |
| `verbose_json`  | Подробный JSON с сегментами и таймкодами |
| `diarized_json` | JSON с разметкой спикеров                |

## Поддерживаемые форматы

MP3, WAV, M4A, FLAC, OGG, WebM

<Note>
  Максимальный размер файла — 25 MB. Для больших файлов рекомендуется разбивать на части.
</Note>

## Примеры

<CodeGroup>
  ```bash cURL theme={null}
  curl -X POST "https://polza.ai/api/v1/audio/transcriptions" \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "openai/whisper-1",
      "file": "BASE64_ENCODED_AUDIO",
      "language": "ru"
    }'
  ```

  ```python Python theme={null}
  import requests
  import base64

  with open('audio.mp3', 'rb') as f:
      audio_base64 = base64.b64encode(f.read()).decode('utf-8')

  response = requests.post(
      'https://polza.ai/api/v1/audio/transcriptions',
      headers={'Authorization': 'Bearer YOUR_API_KEY'},
      json={
          'model': 'openai/whisper-1',
          'file': audio_base64,
          'language': 'ru'
      }
  )

  data = response.json()
  print(data['text'])
  ```

  ```javascript JavaScript theme={null}
  const fs = require('fs');

  const audioFile = fs.readFileSync('audio.mp3');
  const audioBase64 = audioFile.toString('base64');

  const response = await fetch('https://polza.ai/api/v1/audio/transcriptions', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer YOUR_API_KEY',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'whisper-1',
      file: audioBase64,
      language: 'ru'
    })
  });

  const data = await response.json();
  console.log(data.text);
  ```
</CodeGroup>

## Ответ (200)

```json  theme={null}
{
  "text": "Привет, это тестовая запись для проверки транскрибации.",
  "language": "ru",
  "duration": 5.32,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 2.5,
      "text": "Привет, это тестовая запись"
    },
    {
      "id": 1,
      "start": 2.5,
      "end": 5.32,
      "text": "для проверки транскрибации."
    }
  ],
  "usage": {
    "durationSeconds": 5.32,
    "cost_rub": 0.15,
    "cost": 0.15
  }
}
```

## Поля ответа

| Поле       | Описание                                                     |
| ---------- | ------------------------------------------------------------ |
| `text`     | Полный транскрибированный текст                              |
| `language` | Определённый язык                                            |
| `duration` | Длительность аудио в секундах                                |
| `segments` | Сегменты с таймкодами (для verbose\_json)                    |
| `words`    | Слова с таймкодами (при timestamp\_granularities: \["word"]) |
| `usage`    | Использование: durationSeconds, cost\_rub, cost              |


## OpenAPI

````yaml POST /v1/audio/transcriptions
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/audio/transcriptions:
    post:
      tags:
        - Аудио
      summary: Транскрибировать аудио в текст (STT)
      operationId: AudioSttController_createTranscription[3]
      parameters: []
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              $ref: '#/components/schemas/AudioTranscriptionDto'
          application/json:
            schema:
              $ref: '#/components/schemas/AudioTranscriptionDto'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AudioTranscriptionPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    AudioTranscriptionDto:
      type: object
      properties:
        file:
          type: string
          description: Аудио файл в формате base64 (data:audio/mp3;base64,...) или URL
          example: data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAA...
        model:
          type: string
          description: ID модели для транскрипции
          example: whisper-1
          default: whisper-1
        language:
          type: string
          description: 'Язык аудио в формате ISO-639-1 (например: ru, en, de)'
          example: ru
        prompt:
          type: string
          description: Промпт для улучшения контекста транскрипции
          example: Это разговор об искусственном интеллекте
        response_format:
          type: string
          description: Формат ответа
          enum:
            - json
            - text
            - srt
            - verbose_json
            - vtt
            - diarized_json
          default: json
        temperature:
          type: number
          description: Температура сэмплирования (0-1)
          example: 0
          minimum: 0
          maximum: 1
          default: 0
        timestamp_granularities:
          type: array
          description: Granularity для временных меток (только для verbose_json)
          example:
            - word
            - segment
          items:
            type: string
            enum:
              - word
              - segment
        user:
          type: string
          description: >-
            Уникальный идентификатор конечного пользователя для отслеживания и
            предотвращения злоупотреблений
          example: user-123
        chunking_strategy:
          description: >-
            Chunking strategy для разбивки аудио (обязателен для
            gpt-4o-transcribe-diarize при >30 сек)
          oneOf:
            - type: string
              enum:
                - auto
            - 14bc0900-17d0-410e-b84c-1b9035549e38
          example: auto
        include:
          type: array
          description: Дополнительная информация в ответе (logprobs)
          example:
            - logprobs
          items:
            type: string
            enum:
              - logprobs
        known_speaker_names:
          description: Имена известных спикеров (до 4)
          example:
            - agent
            - customer
          type: array
          items:
            type: array
        known_speaker_references:
          description: Аудио референсы для известных спикеров (data URLs)
          type: array
          items:
            type: array
        stream:
          type: boolean
          description: Стриминг ответа (не поддерживается для whisper-1)
          example: false
      required:
        - file
    AudioTranscriptionPresenter:
      type: object
      properties:
        text:
          type: string
          description: Транскрибированный текст
          example: Привет! Это тестовое сообщение.
        language:
          type: string
          description: Определенный язык аудио (ISO-639-1)
          example: ru
        duration:
          type: number
          description: Длительность аудио в секундах
          example: 10.5
        segments:
          description: Сегменты с таймстампами (для verbose_json)
          type: array
          items:
            $ref: '#/components/schemas/TranscriptionSegmentPresenter'
        words:
          description: Words с таймстампами (для verbose_json с word granularity)
          type: array
          items:
            $ref: '#/components/schemas/TranscriptionWordPresenter'
        model:
          type: string
          description: ID использованной модели
          example: whisper-1
        usage:
          type: object
          description: Информация об использовании
          example:
            durationSeconds: 10.5
            cost: 0.01
            cost_rub: 0.01
      required:
        - text
    TranscriptionSegmentPresenter:
      type: object
      properties:
        id:
          type: number
          description: ID сегмента
          example: 0
        seek:
          type: number
          description: Seek position
          example: 0
        start:
          type: number
          description: Время начала (секунды)
          example: 0
        end:
          type: number
          description: Время окончания (секунды)
          example: 5.5
        text:
          type: string
          description: Текст сегмента
          example: Привет, мир!
        tokens:
          description: Token IDs
          example:
            - 1
            - 2
            - 3
          type: array
          items:
            type: number
        temperature:
          type: number
          description: Температура
          example: 0
        avg_logprob:
          type: number
          description: Средняя log probability
          example: -0.5
        compression_ratio:
          type: number
          description: Compression ratio
          example: 1.2
        no_speech_prob:
          type: number
          description: Вероятность отсутствия речи
          example: 0.01
      required:
        - id
        - seek
        - start
        - end
        - text
        - tokens
        - temperature
        - avg_logprob
        - compression_ratio
        - no_speech_prob
    TranscriptionWordPresenter:
      type: object
      properties:
        word:
          type: string
          description: Слово
          example: Привет
        start:
          type: number
          description: Время начала (секунды)
          example: 0
        end:
          type: number
          description: Время окончания (секунды)
          example: 0.5
      required:
        - word
        - start
        - end
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <POLZA_AI_API_KEY>

````

Built with [Mintlify](https://mintlify.com).
> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# POST Audio Speech

> Синтез речи из текста (Text-to-Speech)

<Info>
  Этот эндпоинт совместим с OpenAI SDK и подходит для быстрой миграции существующего кода.
  Если вы разрабатываете новый софт — рекомендуем использовать [Media API](/api-reference/media/create), который предоставляет единый интерфейс для всех медиа-операций.
</Info>

## Доступные модели

| Модель          | ID                       | Описание                                 |
| --------------- | ------------------------ | ---------------------------------------- |
| TTS             | `openai/tts-1`           | OpenAI-совместимая модель (по умолчанию) |
| TTS HD          | `openai/tts-1-hd`        | Высокое качество                         |
| GPT-4o Mini TTS | `openai/gpt-4o-mini-tts` | Поддержка голосовых инструкций           |

## Доступные голоса

**OpenAI:** alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse

**ElevenLabs:** Rachel, Aria, Roger, Sarah, Laura, Charlie, George, Callum, River, Liam, Charlotte, Alice, Matilda, Will, Jessica, Eric, Chris, Brian, Daniel, Lily, Bill

## Параметры запроса

| Параметр          | Тип    | Обязательный | Описание                                                          |
| ----------------- | ------ | ------------ | ----------------------------------------------------------------- |
| `model`           | string | Нет          | Модель TTS (по умолчанию openai/tts-1)                            |
| `input`           | string | Да           | Текст для озвучки (макс. 5000 символов)                           |
| `voice`           | string | Да           | Имя голоса                                                        |
| `response_format` | string | Нет          | Формат: mp3, opus, aac, flac, wav, pcm (по умолчанию mp3)         |
| `speed`           | number | Нет          | Скорость речи (0.25-4.0, по умолчанию 1.0)                        |
| `instructions`    | string | Нет          | Инструкции для голоса (макс. 4096, только openai/gpt-4o-mini-tts) |
| `user`            | string | Нет          | Идентификатор конечного пользователя                              |

### Параметры ElevenLabs

| Параметр           | Тип          | Описание                                     |
| ------------------ | ------------ | -------------------------------------------- |
| `stability`        | number (0-1) | Стабильность голоса (меньше = экспрессивнее) |
| `similarity_boost` | number (0-1) | Схожесть с оригинальным голосом              |
| `style`            | number (0-1) | Эмоциональность                              |
| `timestamps`       | boolean      | Временные метки слов                         |
| `previous_text`    | string       | Текст перед текущим фрагментом (контекст)    |
| `next_text`        | string       | Текст после текущего фрагмента (контекст)    |
| `language_code`    | string       | Код языка (для ElevenLabs Turbo v2.5)        |

## Примеры

<CodeGroup>
  ```bash cURL theme={null}
  curl -X POST "https://polza.ai/api/v1/audio/speech" \
    -H "Authorization: Bearer YOUR_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "openai/tts-1",
      "input": "Привет! Это Polza.AI!",
      "voice": "alloy"
    }'
  ```

  ```python Python theme={null}
  import requests

  response = requests.post(
      'https://polza.ai/api/v1/audio/speech',
      headers={'Authorization': 'Bearer YOUR_API_KEY'},
      json={
          'model': 'openai/tts-1',
          'input': 'Привет! Это тестовое сообщение.',
          'voice': 'alloy'
      }
  )

  data = response.json()
  print(f"Аудио: {data['audio']}")
  print(f"Длительность: {data.get('duration')} сек")
  ```

  ```javascript JavaScript theme={null}
  const response = await fetch('https://polza.ai/api/v1/audio/speech', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer YOUR_API_KEY',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'openai/tts-1',
      input: 'Hello! This is a test message.',
      voice: 'nova'
    })
  });

  const data = await response.json();
  console.log(data.audio);
  ```
</CodeGroup>

## Ответ (200)

```json  theme={null}
{
  "audio": "https://cdn.polza.ai/audio/9a0127a1.mp3",
  "contentType": "audio/mpeg",
  "model": "openai/tts-1",
  "duration": 3.5,
  "usage": {
    "characters": 25,
    "cost_rub": 0.50,
    "cost": 0.50
  }
}
```

| Поле          | Тип    | Описание                                    |
| ------------- | ------ | ------------------------------------------- |
| `audio`       | string | URL или base64 аудио                        |
| `contentType` | string | MIME-тип (например, audio/mpeg)             |
| `model`       | string | Использованная модель                       |
| `duration`    | number | Длительность в секундах                     |
| `usage`       | object | Использование: characters, cost\_rub, cost  |
| `alignment`   | object | Временные метки слов (при timestamps: true) |

***

## Генерация звуковых эффектов

Также доступна генерация звуков по текстовому описанию через тот же эндпоинт.

### Параметры

| Параметр           | Тип     | Обязательный | Описание                     |
| ------------------ | ------- | ------------ | ---------------------------- |
| `model`            | string  | Да           | `elevenlabs/sound-effect-v2` |
| `input`            | string  | Да           | Описание звука на английском |
| `duration_seconds` | number  | Нет          | Длительность (0.5-10 сек)    |
| `loop`             | boolean | Нет          | Зацикленность                |
| `output_format`    | string  | Нет          | Формат аудио                 |
| `prompt_influence` | number  | Нет          | Влияние промпта              |

### Форматы вывода

* `mp3_22050_32` — MP3 22050Hz 32kbps
* `mp3_44100_32` — MP3 44100Hz 32kbps
* `mp3_44100_64` — MP3 44100Hz 64kbps
* `mp3_44100_128` — MP3 44100Hz 128kbps (рекомендуется)
* `mp3_44100_192` — MP3 44100Hz 192kbps

### Пример

```bash  theme={null}
curl -X POST "https://polza.ai/api/v1/audio/speech" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "elevenlabs/sound-effect-v2",
    "input": "sound of guitar strumming",
    "duration_seconds": 2.5,
    "loop": false,
    "output_format": "mp3_44100_128",
    "prompt_influence": 0.3
  }'
```

<Note>
  Описание звуковых эффектов должно быть на английском языке.
</Note>


## OpenAPI

````yaml POST /v1/audio/speech
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/audio/speech:
    post:
      tags:
        - Аудио
      summary: Сгенерировать речь из текста (TTS)
      operationId: AudioTtsController_createSpeech[3]
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AudioSpeechDto'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AudioSpeechPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    AudioSpeechDto:
      type: object
      properties:
        model:
          type: string
          description: ID модели для генерации речи
          example: tts-1
          default: tts-1
        input:
          type: string
          description: Текст для озвучивания (максимум 5000 символов)
          example: Привет! Это тестовое сообщение.
          maxLength: 5000
        voice:
          type: string
          description: >-
            Голос для генерации речи. Допустимые значения зависят от модели:
            OpenAI (alloy, ash, ballad, coral, echo, fable, onyx, nova, sage,
            shimmer, verse), ElevenLabs (Rachel, Aria, Roger, Sarah и др.)
          example: alloy
        instructions:
          type: string
          description: >-
            Инструкции для управления характеристиками голоса. Поддерживается
            только для gpt-4o-mini-tts, не работает с tts-1 и tts-1-hd
          example: Говори медленно и выразительно
          maxLength: 4096
        response_format:
          type: string
          description: Формат выходного аудио
          enum:
            - mp3
            - opus
            - aac
            - flac
            - wav
            - pcm
          default: mp3
        speed:
          type: number
          description: Скорость генерации речи (0.25 - 4.0)
          example: 1
          minimum: 0.25
          maximum: 4
          default: 1
        stream_format:
          type: string
          description: >-
            Формат потоковой передачи аудио. Не поддерживается для tts-1 и
            tts-1-hd
          enum:
            - sse
            - audio
        user:
          type: string
          description: >-
            Уникальный идентификатор конечного пользователя для отслеживания и
            предотвращения злоупотреблений
          example: user-123
        stability:
          type: number
          description: Стабильность голоса (0-1). Только для ElevenLabs
          example: 0.5
          minimum: 0
          maximum: 1
        similarity_boost:
          type: number
          description: Усиление схожести голоса (0-1). Только для ElevenLabs
          example: 0.75
          minimum: 0
          maximum: 1
        style:
          type: number
          description: Экспрессия стиля (0-1). Только для ElevenLabs
          example: 0
          minimum: 0
          maximum: 1
        timestamps:
          type: boolean
          description: Возвращать временные метки для каждого слова. Только для ElevenLabs
          example: false
        previous_text:
          type: string
          description: >-
            Предшествующий текст для улучшения непрерывности речи при
            конкатенации. Только для ElevenLabs
          maxLength: 5000
        next_text:
          type: string
          description: >-
            Последующий текст для улучшения непрерывности речи при конкатенации.
            Только для ElevenLabs
          maxLength: 5000
        language_code:
          type: string
          description: Код языка ISO 639-1. Только для ElevenLabs Turbo v2.5
          example: ru
          maxLength: 10
      required:
        - input
        - voice
    AudioSpeechPresenter:
      type: object
      properties:
        audio:
          type: string
          description: Base64-encoded аудио данные
          example: SUQzBAAAAAAAI1RTU0UAAA...
        contentType:
          type: string
          description: Content-Type аудио
          example: audio/mpeg
        model:
          type: string
          description: ID использованной модели
          example: tts-1
        duration:
          type: number
          description: Длительность аудио в секундах (если известна)
          example: 5.2
        usage:
          type: object
          description: Информация об использовании
          example:
            characters: 100
            cost: 0.01
            cost_rub: 0.01
        alignment:
          type: object
          description: 'Временные метки символов (при timestamps: true, ElevenLabs)'
      required:
        - audio
        - contentType
        - model
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <POLZA_AI_API_KEY>

````

Built with [Mintlify](https://mintlify.com).
> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# GET Models

> Получение списка доступных моделей

<Note>
  Этот эндпоинт не требует аутентификации и доступен всем пользователям.
</Note>

## Параметры запроса

| Параметр            | Тип     | Описание                                             |
| ------------------- | ------- | ---------------------------------------------------- |
| `type`              | string  | Фильтр по типу: chat, image, embedding, video, audio |
| `include_providers` | boolean | Включить массив провайдеров для каждой модели        |

## Примеры

<CodeGroup>
  ```bash Все модели theme={null}
  curl "https://polza.ai/api/v1/models"
  ```

  ```bash Только чат-модели theme={null}
  curl "https://polza.ai/api/v1/models?type=chat"
  ```

  ```bash С информацией о провайдерах theme={null}
  curl "https://polza.ai/api/v1/models?type=chat&include_providers=true"
  ```

  ```python Python theme={null}
  from openai import OpenAI

  client = OpenAI(
      base_url="https://polza.ai/api/v1",
      api_key="YOUR_API_KEY"
  )

  models = client.models.list()
  for model in models.data:
      print(model.id)
  ```
</CodeGroup>

## Поля модели

### Основные

| Поле             | Описание                               |
| ---------------- | -------------------------------------- |
| `id`             | Уникальный идентификатор для API       |
| `name`           | Человекочитаемое название              |
| `context_length` | Максимальная длина контекста в токенах |
| `created`        | Unix timestamp создания                |

### Архитектура

| Поле                | Описание                                               |
| ------------------- | ------------------------------------------------------ |
| `input_modalities`  | Поддерживаемые входные типы: text, image, audio, video |
| `output_modalities` | Поддерживаемые выходные типы: text, image, audio       |
| `tokenizer`         | Используемый токенизатор                               |
| `instruct_type`     | Тип инструкций                                         |

### Ценообразование (в рублях за токен)

| Поле                 | Описание              |
| -------------------- | --------------------- |
| `prompt`             | Входные токены        |
| `completion`         | Выходные токены       |
| `image`              | Обработка изображений |
| `internal_reasoning` | Reasoning токены      |
| `input_cache_read`   | Чтение из кеша        |
| `input_cache_write`  | Запись в кеш          |

## Примеры фильтрации

### Мультимодальные модели

```python  theme={null}
multimodal = [
    m for m in models
    if 'image' in m.get('architecture', {}).get('input_modalities', [])
]
```

### Модели с большим контекстом

```python  theme={null}
large_context = [
    m for m in models
    if m.get('context_length', 0) > 100000
]
```

### Модели конкретного провайдера

```python  theme={null}
anthropic = [m for m in models if m['id'].startswith('anthropic/')]
google = [m for m in models if m['id'].startswith('google/')]
meta = [m for m in models if m['id'].startswith('meta-llama/')]
```

## Использование ID моделей

ID модели напрямую используется в запросах:

```python  theme={null}
response = client.chat.completions.create(
    model="anthropic/claude-3-5-sonnet",
    messages=[{"role": "user", "content": "Привет!"}]
)
```


## OpenAPI

````yaml GET /v1/models
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/models:
    get:
      tags:
        - Модели
      summary: Получить список доступных моделей
      operationId: ModelsController_getModels[1]
      parameters:
        - name: type
          required: false
          in: query
          description: Фильтр по типу модели (chat, image, embedding и т.д.)
          schema:
            type: string
        - name: include_providers
          required: false
          in: query
          description: Включить массив провайдеров в ответ
          schema:
            type: boolean
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ModelListPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
components:
  schemas:
    ModelListPresenter:
      type: object
      properties:
        data:
          description: Список моделей
          type: array
          items:
            $ref: '#/components/schemas/PublicModelPresenter'
      required:
        - data
    PublicModelPresenter:
      type: object
      properties:
        id:
          type: string
          description: ID модели (slug)
          example: deepseek-r1
        name:
          type: string
          description: Название модели
          example: DeepSeek R1
        type:
          type: string
          description: Тип модели
          example: chat
          enum:
            - chat
            - embedding
            - image
            - audio
            - video
            - moderation
            - stt
            - tts
            - document
        short_description:
          type: object
          description: Краткое описание модели
          example: Мощная модель для генерации текста
        created:
          type: number
          description: Timestamp создания
          example: 1765987078
        architecture:
          description: Архитектура модели
          allOf:
            - $ref: '#/components/schemas/ModelArchitecturePresenter'
        top_provider:
          description: Информация о топ провайдере
          allOf:
            - $ref: '#/components/schemas/TopProviderPresenter'
        providers:
          description: Список провайдеров
          type: array
          items:
            $ref: '#/components/schemas/ModelProviderPresenter'
        endpoints:
          description: Поддерживаемые endpoints
          example:
            - /v1/chat/completions
          type: array
          items:
            type: string
        parameters:
          description: Параметры модели (для медиа)
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
        operations:
          description: Операции над результатом (для медиа)
          type: array
          items:
            $ref: '#/components/schemas/ModelOperationPresenter'
      required:
        - id
        - name
        - type
        - created
        - architecture
        - top_provider
        - endpoints
    ModelArchitecturePresenter:
      type: object
      properties:
        modality:
          type: object
          description: Основная модальность
          example: text+image->text
        input_modalities:
          description: Входные модальности
          example:
            - text
            - image
          type: array
          items:
            type: string
        output_modalities:
          description: Выходные модальности
          example:
            - text
          type: array
          items:
            type: string
        tokenizer:
          type: object
          description: Токенизатор
          example: GPT
        instruct_type:
          type: object
          description: Тип инструкций
          example: chatml
      required:
        - input_modalities
        - output_modalities
    TopProviderPresenter:
      type: object
      properties:
        is_moderated:
          type: boolean
          description: Модерируется ли контент
        context_length:
          type: object
          description: Длина контекста от провайдера
        max_completion_tokens:
          type: object
          description: Максимум токенов completion от провайдера
        pricing:
          description: Ценообразование
          allOf:
            - $ref: '#/components/schemas/ModelPricingPresenter'
        supported_parameters:
          description: Поддерживаемые параметры
          type: array
          items:
            type: string
        default_parameters:
          description: Параметры по умолчанию
          allOf:
            - $ref: '#/components/schemas/DefaultParametersPresenter'
        per_request_limits:
          description: Лимиты на запрос
          allOf:
            - $ref: '#/components/schemas/PerRequestLimitsPresenter'
        parameters:
          description: Параметры медиа-модели
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
      required:
        - is_moderated
        - pricing
    ModelProviderPresenter:
      type: object
      properties:
        name:
          type: string
          description: Название провайдера
          example: OpenRouter
        context_length:
          type: object
          description: Длина контекста от провайдера
        max_completion_tokens:
          type: object
          description: Максимум токенов completion от провайдера
        is_moderated:
          type: boolean
          description: Модерируется ли контент
        pricing:
          description: Ценообразование
          allOf:
            - $ref: '#/components/schemas/ModelPricingPresenter'
        supported_parameters:
          description: Поддерживаемые параметры
          type: array
          items:
            type: string
        default_parameters:
          description: Параметры по умолчанию
          allOf:
            - $ref: '#/components/schemas/DefaultParametersPresenter'
        per_request_limits:
          description: Лимиты на запрос
          allOf:
            - $ref: '#/components/schemas/PerRequestLimitsPresenter'
        parameters:
          description: Параметры медиа-модели
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
      required:
        - name
        - is_moderated
        - pricing
    ModelParametersPresenter:
      type: object
      properties:
        prompt:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        aspect_ratio:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        resolution:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        image_resolution:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        duration:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        output_format:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        seeds:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        watermark:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        images:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        videos:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        quality:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        voice:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        speed:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        stability:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        similarity_boost:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        style:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        timestamps:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        previous_text:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        next_text:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        language_code:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
    ModelOperationPresenter:
      type: object
      properties:
        id:
          type: string
          description: ID операции
          example: extend
        name:
          type: string
          description: Название операции
          example: Продление видео
        description:
          type: string
          description: Описание операции
        async:
          type: boolean
          description: Асинхронная операция (требует polling)
        pricing:
          description: Стоимость операции
          allOf:
            - $ref: '#/components/schemas/ModelPricingPresenter'
        parameters:
          description: Параметры операции
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
      required:
        - id
        - name
        - async
    ModelPricingPresenter:
      type: object
      properties:
        prompt_per_million:
          type: object
          description: Цена за 1M prompt токенов (RUB)
          example: '15.50'
        completion_per_million:
          type: object
          description: Цена за 1M completion токенов (RUB)
          example: '62.00'
        request_per_thousand:
          type: object
          description: Цена за 1K запросов (RUB)
        image_input_per_million:
          type: object
          description: Цена за 1M входных изображений (RUB)
        image_output_per_million:
          type: object
          description: Цена за 1M токенов сгенерированного изображения (RUB)
        audio_per_million:
          type: object
          description: Цена за 1M токенов аудио (RUB)
        web_search_per_thousand:
          type: object
          description: Цена за 1K web search запросов (RUB)
        internal_reasoning_per_million:
          type: object
          description: Цена за 1M reasoning токенов (RUB)
        input_cache_read_per_million:
          type: object
          description: Цена за 1M токенов чтения из кэша (RUB)
        input_cache_write_per_million:
          type: object
          description: Цена за 1M токенов записи в кэш (RUB)
        input_audio_cache_per_million:
          type: object
          description: Цена за 1M токенов кэшированного аудио (RUB)
        stt_per_minute:
          type: object
          description: Цена за 1 минуту Speech-to-Text (RUB)
        tts_per_million_characters:
          type: object
          description: Цена за 1M символов Text-to-Speech (RUB)
          example: '1800.00000000'
        video_per_second:
          type: object
          description: Цена за 1 секунду видео (RUB)
        per_request:
          type: object
          description: Цена за 1 запрос (RUB)
        tiers:
          description: Уровни цен для моделей с динамическим ценообразованием
          type: array
          items:
            $ref: '#/components/schemas/ClientTierPresenter'
        unitParam:
          type: object
          description: >-
            Параметр-множитель для tiers (например, duration). Если задан,
            cost_rub в tiers — ставка за единицу этого параметра
          example: duration
        currency:
          type: string
          description: Валюта цен
          example: RUB
      required:
        - currency
    DefaultParametersPresenter:
      type: object
      properties:
        temperature:
          type: object
          description: Temperature по умолчанию (0-2)
        top_p:
          type: object
          description: Top P по умолчанию (0-1)
        frequency_penalty:
          type: object
          description: Frequency penalty по умолчанию (-2-2)
    PerRequestLimitsPresenter:
      type: object
      properties:
        prompt_tokens:
          type: object
          description: Максимум prompt токенов на запрос
        completion_tokens:
          type: object
          description: Максимум completion токенов на запрос
    ModelParameterConstraintPresenter:
      type: object
      properties:
        required:
          type: boolean
          description: Обязательный параметр
        description:
          type: string
          description: Описание параметра
        max_length:
          type: number
          description: Максимальная длина строки
        min:
          type: number
          description: Минимальное значение
        max:
          type: number
          description: Максимальное значение
        default:
          type: object
          description: Значение по умолчанию
        values:
          description: Допустимые значения
          type: array
          items:
            type: string
    ClientTierPresenter:
      type: object
      properties:
        conditions:
          description: Условия применения уровня цены
          example:
            - image_resolution=4K
          type: array
          items:
            type: string
        cost_rub:
          type: string
          description: Цена для клиента в RUB
          example: '8.25'
      required:
        - conditions
        - cost_rub

````

Built with [Mintlify](https://mintlify.com).
> ## Documentation Index
> Fetch the complete documentation index at: https://polza.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# GET Balance

> Запрос текущего баланса аккаунта

## Примеры

<CodeGroup>
  ```bash cURL theme={null}
  curl "https://polza.ai/api/v1/balance" \
    -H "Authorization: Bearer YOUR_API_KEY"
  ```

  ```python Python theme={null}
  import requests

  response = requests.get(
      'https://polza.ai/api/v1/balance',
      headers={'Authorization': 'Bearer YOUR_API_KEY'}
  )

  data = response.json()
  print(f"Баланс: {data['amount']} руб.")
  ```

  ```javascript JavaScript theme={null}
  const response = await fetch('https://polza.ai/api/v1/balance', {
    headers: { 'Authorization': 'Bearer YOUR_API_KEY' }
  });

  const data = await response.json();
  console.log(`Баланс: ${data.amount} руб.`);
  ```
</CodeGroup>

## Ответ (200)

```json  theme={null}
{
  "amount": "9.28591714"
}
```

| Поле     | Тип    | Описание                |
| -------- | ------ | ----------------------- |
| `amount` | string | Текущий баланс в рублях |

## Мониторинг баланса

```python  theme={null}
import requests
import time

def check_balance(api_key, min_balance=100):
    response = requests.get(
        'https://polza.ai/api/v1/balance',
        headers={'Authorization': f'Bearer {api_key}'}
    )

    data = response.json()
    balance = float(data['amount'])

    if balance < min_balance:
        print(f"Внимание! Баланс низкий: {balance} руб.")

    return balance

# Проверка каждый час
while True:
    balance = check_balance('YOUR_API_KEY')
    print(f"Текущий баланс: {balance} руб.")
    time.sleep(3600)
```

<Note>
  Пополнить баланс можно в [консоли](https://polza.ai/dashboard) через банковскую карту, СБП или счёт для юридических лиц.
</Note>


## OpenAPI

````yaml GET /v1/balance
openapi: 3.0.0
info:
  title: Polza.ai API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://polza.ai/api
    description: Production
security: []
tags: []
paths:
  /v1/balance:
    get:
      tags:
        - V1Legacy
      operationId: V1LegacyController_getUserBalance[1]
      parameters: []
      responses:
        '200':
          description: ''

````

Built with [Mintlify](https://mintlify.com).