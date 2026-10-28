from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command
from bot_instance import dp
from db import get_user, update_user, update_primogems
from constants import DIV
from keyboards import back_kb


@dp.message(Command("daily"))
async def cmd_daily(message: types.Message):
    chat_id = message.chat.id
    user = await get_user(message.from_user.id, chat_id)
    if not user:
        await message.answer("Напиши /start")
        return

    now = int(datetime.now(timezone.utc).timestamp())
    last = user.get("last_daily", 0)

    if now - last < 86400:
        left = 86400 - (now - last)
        h = left // 3600
        m = (left % 3600) // 60
        await message.answer(f"⏳ Ты уже получал награду. Возвращайся через {h} ч. {m} мин.", reply_markup=back_kb(message.from_user.id))
        return

    await update_user(message.from_user.id, chat_id, last_daily=now)
    await update_primogems(message.from_user.id, chat_id, 80)

    text = (
        f"🎁 **ЕЖЕДНЕВНАЯ НАГРАДА**\n{DIV}\n\n"
        f"Ты получил **80 Примогемов** 💎!\n\n"
        f"Заходи завтра!"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=back_kb(message.from_user.id))