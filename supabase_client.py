"""Модуль для работы с Supabase из Python"""

from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)


def save_telegram_message(message_data: dict) -> dict:
    """Сохраняет сообщение в таблицу telegram_messages"""
    try:
        result = supabase.table("telegram_messages").insert(message_data).execute()
        return {"success": True, "data": result.data[0] if result.data else None}
    except Exception as e:
        print(f"Error saving message: {e}")
        return {"success": False, "error": str(e)}


def update_deal_from_message(message_data: dict, ai_result: dict) -> dict:
    """Обновляет или создаёт сделку на основе сообщения"""
    try:
        # Ищем клиента по username или имени
        client_query = supabase.table("clients").select("*")
        
        if ai_result.get("client_username"):
            client_query = client_query.eq("contact", ai_result["client_username"])
        elif ai_result.get("client_name"):
            client_query = client_query.ilike("name", f"%{ai_result['client_name']}%")
        
        client_result = client_query.execute()
        client = client_result.data[0] if client_result.data else None
        
        # Если клиента нет, создаём
        if not client and ai_result.get("is_order"):
            new_client = {
                "name": ai_result.get("client_name", "Новый клиент"),
                "contact": ai_result.get("client_username", ""),
                "vertical": ai_result.get("brief_items", {}).get("vertical", "Другое"),
                "status": "new",
                "last_contact": message_data.get("date"),
                "note": ai_result.get("summary", "")
            }
            client_result = supabase.table("clients").insert(new_client).execute()
            client = client_result.data[0] if client_result.data else None
        
        # Если это заказ и клиент найден
        if ai_result.get("is_order") and client:
            # Ищем активную сделку этого клиента
            deal_query = supabase.table("deals").select("*").eq("client_id", client["id"]).in_("stage", ["lead", "qual", "offer", "work", "review"])
            deal_result = deal_query.execute()
            existing_deal = deal_result.data[0] if deal_result.data else None
            
            if ai_result.get("is_revision") and existing_deal:
                # Обновляем существующую сделку (правки)
                updated_deal = {
                    "stage": "work",
                    "next": f"Правки: {ai_result.get('revision_details', '')}",
                    "due": ai_result.get("deadline")
                }
                supabase.table("deals").update(updated_deal).eq("id", existing_deal["id"]).execute()
                return {"success": True, "action": "updated_deal", "deal_id": existing_deal["id"]}
            
            elif not existing_deal:
                # Создаём новую сделку
                new_deal = {
                    "client_id": client["id"],
                    "client": client["name"],
                    "vertical": ai_result.get("brief_items", {}).get("vertical", "iGaming"),
                    "service": ai_result.get("order_type", "ASO"),
                    "value": ai_result.get("price", 0),
                    "paid": ai_result.get("payment_amount", 0) if ai_result.get("is_payment") else 0,
                    "stage": ai_result.get("status", "lead"),
                    "assignee": None,
                    "next": ai_result.get("task_description", ""),
                    "due": ai_result.get("deadline"),
                    "lines": []
                }
                deal_result = supabase.table("deals").insert(new_deal).execute()
                return {"success": True, "action": "created_deal", "deal_id": deal_result.data[0]["id"] if deal_result.data else None}
        
        # Если это оплата
        if ai_result.get("is_payment") and client:
            # Находим последнюю сделку клиента
            deal_result = supabase.table("deals").select("*").eq("client_id", client["id"]).order("created_at", desc=True).limit(1).execute()
            if deal_result.data:
                deal = deal_result.data[0]
                new_paid = (deal.get("paid", 0) or 0) + ai_result.get("payment_amount", 0)
                supabase.table("deals").update({"paid": new_paid}).eq("id", deal["id"]).execute()
                return {"success": True, "action": "updated_payment", "deal_id": deal["id"]}
        
        return {"success": True, "action": "saved_message_only"}
    
    except Exception as e:
        print(f"Error updating deal: {e}")
        return {"success": False, "error": str(e)}
