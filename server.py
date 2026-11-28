import uvicorn
import hashlib
import hmac
import os
from urllib.parse import unquote
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from bot_instance import bot
from config import BOT_TOKEN, OWNER_ID, PRICE_ROLE_CHANGE, PRICE_REST, PRICE_CLEAN
from db import get_user, update_user, save_application, get_trusted_admins, fetch_all

app = FastAPI()

# Разрешаем запросы (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- ВАЛИДАЦИЯ TELEGRAM ---
def verify_telegram_data(init_data: str) -> dict:
    try:
        parsed_data = dict(unquote(x).split('=') for x in init_data.split('&'))
        if "hash" not in parsed_data:
            return None

        hash_val = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash == hash_val:
            # Возвращаем ID пользователя
            import json
            user_data = json.loads(parsed_data["user"])
            return user_data
    except Exception as e:
        print(f"Ошибка валидации: {e}")
    return None


# --- API ЭНДПОИНТЫ ---

class ApplicationData(BaseModel):
    initData: str
    age: str
    experience: str
    about: str
    timezone: str
    source: str
    activity: str


class BuyData(BaseModel):
    initData: str
    item: str


@app.post("/api/apply")
async def apply_form(data: ApplicationData):
    user_info = verify_telegram_data(data.initData)
    if not user_info:
        raise HTTPException(status_code=403, detail="Invalid auth")

    user_id = user_info['id']
    chat_id = 0  # Для Mini App можно сохранять анкеты с chat_id = 0 (глобально)

    # Сохраняем в БД
    await save_application(
        user_id, chat_id, "Не выбран", data.age, data.experience, data.about,
        data.timezone, "Нет", "", data.activity, data.source
    )
    await update_user(user_id, chat_id, first_seen=1)  # Заглушка

    # Отправляем админам
    admins = await get_trusted_admins()
    if OWNER_ID not in admins: admins.append(OWNER_ID)

    text = (
        f"📩 <b>НОВАЯ АНКЕТА (Mini App)</b>\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🎂 Возраст: {data.age}\n"
        f"📖 Опыт: {data.experience[:200]}\n"
        f"🌟 О себе: {data.about[:200]}\n"
        f"📢 Источник: {data.source}"
    )
    for admin in admins:
        try:
            await bot.send_message(admin, text, parse_mode="HTML")
        except:
            pass

    return {"status": "ok", "message": "Анкета отправлена!"}


@app.get("/api/profile")
async def get_profile(init_data: str):
    user_info = verify_telegram_data(init_data)
    if not user_info:
        raise HTTPException(status_code=403, detail="Invalid auth")

    user_id = user_info['id']
    user = await get_user(user_id, 0)

    if not user:
        return {"name": user_info.get('first_name', 'Игрок'), "balance": 0, "rank": "Новичок",
                "is_admin": user_id == OWNER_ID}

    is_admin = user_id == OWNER_ID or user.get("admin_rank") not in (None, "", "Игрок")

    return {
        "name": user.get("character_name") or user_info.get('first_name', 'Игрок'),
        "balance": user.get("balance", 0),
        "reputation": user.get("reputation", 0),
        "is_admin": is_admin
    }


@app.post("/api/buy")
async def buy_item(data: BuyData):
    user_info = verify_telegram_data(data.initData)
    if not user_info: raise HTTPException(status_code=403)

    user_id = user_info['id']
    user = await get_user(user_id, 0)

    price = PRICE_ROLE_CHANGE if data.item == "role" else 1000  # Пример

    if user["balance"] < price:
        return {"status": "error", "message": "Недостаточно монет!"}

    await update_user(user_id, 0, balance=user["balance"] - price)
    # Здесь можно добавить выдачу роли и т.д.

    return {"status": "ok", "message": "Успешно куплено!"}


@app.get("/api/admin/apps")
async def get_admin_apps(init_data: str):
    user_info = verify_telegram_data(init_data)
    if not user_info: raise HTTPException(status_code=403)

    user_id = user_info['id']
    if user_id != OWNER_ID: return {"apps": []}

    apps = await fetch_all("SELECT user_id, age, experience, source FROM applications WHERE status = 'pending'")
    return {"apps": apps}


# Раздаем статику (HTML, CSS, JS)
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("server:app", host="0.0.0.0", port=port)