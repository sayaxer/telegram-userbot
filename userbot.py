"""Telegram Userbot - читает личные сообщения и анализирует их через AI"""

import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from datetime import datetime
import asyncio
from classifier import classify
from supabase_client import save_telegram_message, update_deal_from_message

load_dotenv()

# Инициализация Pyrogram
app = Client(
    "userbot_session",
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH"),
    phone_number=os.getenv("PHONE_NUMBER")
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


@app.on_message(filters.private & filters.incoming)
async def handle_private_message(client: Client, message: Message):
    """Обрабатывает входящие личные сообщения"""
    
    # Пропускаем сообщения от себя
    if message.from_user.is_self:
        return
    
    # Получаем текст сообщения
    text = message.text or message.caption or ""
    if not text:
        return
    
    print(f"\n📩 Новое сообщение от {message.from_user.first_name} (@{message.from_user.username or 'no_username'})")
    print(f"Текст: {text[:100]}...")
    
    # Анализируем через AI
    try:
        ai_result = classify(text, GEMINI_MODEL, GEMINI_API_KEY)
        print(f"🤖 AI результат: {ai_result.get('summary', 'N/A')}")
        
        # Сохраняем сообщение в Supabase
        message_data = {
            "message_id": message.id,
            "chat_id": message.chat.id,
            "sender_id": message.from_user.id,
            "sender_name": message.from_user.first_name,
            "sender_username": message.from_user.username or "",
            "text": text,
            "date": message.date.isoformat(),
            "ai_analysis": ai_result,
            "processed": True
        }
        
        save_result = save_telegram_message(message_data)
        
        # Если это заказ, обновляем сделки
        if ai_result.get("is_order"):
            deal_result = update_deal_from_message(message_data, ai_result)
            print(f"📊 Сделка: {deal_result.get('action')}")
            if deal_result.get("deal_id"):
                print(f"   Deal ID: {deal_result['deal_id']}")
        
        # Отправляем уведомление о результатах
        if ai_result.get("is_order"):
            response = f"✅ Заказ распознан:\n"
            response += f"Клиент: {ai_result.get('client_name', 'N/A')}\n"
            response += f"Тип: {ai_result.get('order_type', 'N/A')}\n"
            response += f"Статус: {ai_result.get('status', 'N/A')}\n"
            response += f"Сумма: ${ai_result.get('price', 0)}\n"
            
            if ai_result.get("missing_brief_items"):
                response += f"\n⚠️ Не хватает в брифе: {', '.join(ai_result['missing_brief_items'])}"
            
            await message.reply(response)
        
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")
        await message.reply(f"❌ Ошибка: {e}")


@app.on_message(filters.group & filters.incoming)
async def handle_group_message(client: Client, message: Message):
    """Обрабатывает сообщения из приватных групп"""
    
    # Пропускаем свои сообщения
    if message.from_user and message.from_user.is_self:
        return
    
    text = message.text or message.caption or ""
    if not text:
        return
    
    # Проверяем, упоминают ли тебя
    mentions = ["@stas_royce", "Stas", "Стас"]
    if not any(mention.lower() in text.lower() for mention in mentions):
        return
    
    print(f"\n👥 Упоминание в группе {message.chat.title}")
    print(f"От: {message.from_user.first_name if message.from_user else 'Unknown'}")
    print(f"Текст: {text[:100]}...")
    
    try:
        ai_result = classify(text, GEMINI_MODEL, GEMINI_API_KEY)
        
        message_data = {
            "message_id": message.id,
            "chat_id": message.chat.id,
            "chat_title": message.chat.title,
            "sender_id": message.from_user.id if message.from_user else None,
            "sender_name": message.from_user.first_name if message.from_user else "Unknown",
            "sender_username": message.from_user.username if message.from_user else "",
            "text": text,
            "date": message.date.isoformat(),
            "ai_analysis": ai_result,
            "processed": True
        }
        
        save_telegram_message(message_data)
        
        if ai_result.get("is_order"):
            update_deal_from_message(message_data, ai_result)
            print(f"📊 Сделка обновлена из группы")
    
    except Exception as e:
        print(f"❌ Ошибка обработки группового сообщения: {e}")


async def main():
    """Запуск userbot"""
    print("🚀 Запуск Telegram Userbot...")
    print(f"📱 Телефон: {os.getenv('PHONE_NUMBER')}")
    print(f"🤖 AI модель: {GEMINI_MODEL}")
    
    await app.start()
    print("✅ Userbot запущен и слушает сообщения...")
    
    # Держим бота запущенным
    await asyncio.Event().wait()


if __name__ == "__main__":
    # Используем pyrogram.run() для совместимости с Render
    app.run(main())
