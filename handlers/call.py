import asyncio
from datetime import datetime, timezone
import aiosqlite
from aiogram import types
from aiogram.filters import Command

from bot_instance import dp
from config import DB_PATH, OWNER_ID
from constants import DIV, CALL_COOLDOWN, CALL_MAX_MENTIONS
from helpers import esc, _ensure_user
from db import update_user
from keyboards import back_kb


@dp.message(Command("call"))
async def cmd_call(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Команда работает только в группе.")
        return
    chat_id = message.chat.id
    now = int(datetime.now(timezone.utc).timestamp())
    is_owner = message.from_user.id == OWNER_ID

    if not is_owner:
        from state import _call_cooldown
        last = _call_cooldown.get(chat_id, 0)
        if now - last < CALL_COOLDOWN:
            left = CALL_COOLDOWN - (now - last)
            m = left // 60
            s = left % 60
            if m > 0:
                await message.reply(f"⏳ Слишком часто. Подожди {m} мин. {s} сек.",
                                    reply_markup=back_kb(message.from_user.id))
            else:
                await message.reply(f"⏳ Слишком часто. Подожди {s} сек.", reply_markup=back_kb(message.from_user.id))
            return
        _call_cooldown[chat_id] = now

    parts = message.text.split(maxsplit=1)
    call_text = parts[1].strip() if len(parts) > 1 else "Сбор!"
    if len(call_text) > 300:
        call_text = call_text[:300] + "…"

    rows = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT user_id, character_name, username FROM users "
                "WHERE character_name IS NOT NULL AND character_name != '' AND chat_id = ? "
                "AND (IFNULL(call_opt_out, 0) = 0 OR user_id = ?) "
                "ORDER BY user_id",
                (chat_id, message.from_user.id)
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer(f"📢 ПОЗЫВНОЙ\n{DIV}\n\n{esc(call_text)}\n\n{DIV}\n\nУпоминать некого.")
        return

    # Ограничиваем общее число людей
    shown = rows[:CALL_MAX_MENTIONS]

    # Разбиваем на группы по 5 человек
    mentions = []
    for r in shown:
        if r["username"]:
            mentions.append(f"@{r['username']}")
        else:
            mentions.append(f'<a href="tg://user?id={r["user_id"]}">{esc(r["character_name"])}</a>')

    # Нарезаем список на куски по 5 штук
    chunks = [mentions[i:i + 5] for i in range(0, len(mentions), 5)]

    # Отправляем заголовок
    header_text = f"📢 <b>ПОЗЫВНОЙ</b>\n{DIV}\n\n{esc(call_text)}\n\n{DIV}\n"
    await message.answer(header_text, parse_mode="HTML", reply_markup=back_kb(message.from_user.id))

    # Отправляем теги пачками
    for chunk in chunks:
        chunk_text = ", ".join(chunk)
        await message.answer(chunk_text, parse_mode="HTML")
        await asyncio.sleep(1)  # Пауза 1 секунда, чтобы Telegram не посчитал это спамом


@dp.message(Command("calloff"))
async def cmd_calloff(message: types.Message):
    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)
    if user.get("call_opt_out"):
        await message.answer("🔕 Уведомления позывного уже отключены.\n\nВернуть: /callon",
                             reply_markup=back_kb(message.from_user.id))
        return
    await update_user(message.from_user.id, chat_id, call_opt_out=1)
    await message.answer(f"🔕 Готово!\n{DIV}\n\nТеперь я не буду упоминать тебя в /call.\n\nВернуть: /callon",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("callon"))
async def cmd_callon(message: types.Message):
    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)
    if not user.get("call_opt_out"):
        await message.answer("🔔 Уведомления позывного и так включены.\n\nОтключить: /calloff",
                             reply_markup=back_kb(message.from_user.id))
        return
    await update_user(message.from_user.id, chat_id, call_opt_out=0)
    await message.answer(f"🔔 Возвращаю тебя в список упоминаний.\n{DIV}\n\nЕсли снова захочешь отключить: /calloff",
                         reply_markup=back_kb(message.from_user.id))