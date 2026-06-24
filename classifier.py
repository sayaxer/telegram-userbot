"""AI классификация сообщений с Gemini"""

import json
from google import genai
from google.genai import types

_client = None

# Схема ответа AI
SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "is_order": {"type": "BOOLEAN"},
        "is_revision": {"type": "BOOLEAN"},
        "is_payment": {"type": "BOOLEAN"},
        "client_name": {"type": "STRING"},
        "client_username": {"type": "STRING"},
        "order_type": {"type": "STRING", "enum": ["ASO", "AI UGC", "Креативы", "Видео", "Лендинг", "Аппка", "Соцсети", "Брендинг", "Другое"]},
        "price": {"type": "INTEGER"},
        "currency": {"type": "STRING", "enum": ["USD", "EUR", "RUB"]},
        "deadline": {"type": "STRING"},
        "status": {
            "type": "STRING",
            "enum": ["new", "talk", "work", "edits", "done", "paid", "lost"],
        },
        "task_description": {"type": "STRING"},
        "brief_items": {
            "type": "OBJECT",
            "properties": {
                "vertical": {"type": "STRING"},
                "geo": {"type": "STRING"},
                "volume": {"type": "STRING"},
                "deadline": {"type": "STRING"},
                "budget": {"type": "STRING"},
            },
        },
        "missing_brief_items": {"type": "ARRAY", "items": {"type": "STRING"}},
        "revision_details": {"type": "STRING"},
        "payment_amount": {"type": "INTEGER"},
        "summary": {"type": "STRING"},
    },
    "required": ["is_order", "summary"],
}

PROMPT = """Ты — ассистент дизайн-студии. Анализируй сообщение из личного чата Telegram.

Определи:
1. Это заказ? (is_order)
2. Это правки к существующему заказу? (is_revision)
3. Это оплата? (is_payment)

Статусы:
- new — клиент написал, обсуждения ещё нет
- talk — обсуждаем ТЗ или цену
- work — договорились, заказ в работе
- edits — идут правки
- done — работа сдана
- paid — оплачено
- lost — отказ

Бриф должен содержать: vertical (ниша), geo (страна), volume (объём), deadline (срок), budget (бюджет).
Если чего-то нет — перечисли в missing_brief_items.

Для правок (is_revision=true): опиши что именно нужно изменить в revision_details.

Для оплаты (is_payment=true): укажи сумму в payment_amount.

Если это не про заказ (просто вопрос, болтовня) — is_order = false.

Сообщение:
"""


def classify(message: str, model: str, api_key: str) -> dict:
    """Классифицирует сообщение через AI"""
    global _client
    if _client is None:
        _client = genai.Client(api_key=api_key)
    
    resp = _client.models.generate_content(
        model=model,
        contents=PROMPT + message,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SCHEMA,
            temperature=0,
        ),
    )
    return json.loads(resp.text)
