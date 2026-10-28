from datetime import datetime, timezone

import aiosqlite
from aiogram import types
from aiogram.filters import Command

from bot_instance import dp
from config import DB_PATH, OWNER_ID
from constants import (
    DIV, CALL_COOLDOWN, CALL_MAX_MENTIONS, CALL_EMOJIS,
)
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
                await message.reply(f"⏳ Слишком часто. Подожди {m} мин. {s} сек.", reply_markup=back_kb(message.from_user.id))
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
            "SELECT user_id, character_name FROM users "
            "WHERE character_name IS NOT NULL AND character_name != '' AND chat_id = ? "
            "AND (IFNULL(call_opt_out, 0) = 0 OR user_id = ?) "
            "ORDER BY user_id",
            (chat_id, message.from_user.id)
        ) as cur:
            rows = await cur.fetchall()
    if not rows:
        text = (f"📢 ПОЗЫВНОЙ\n{DIV}\n\n{esc(call_text)}\n\n{DIV}\n\n"
                f"Упоминать некого — все отключили уведомления.")
        await message.answer(text, parse_mode="HTML", reply_markup=back_kb(message.from_user.id))
        return
    total = len(rows)
    shown = rows[:CALL_MAX_MENTIONS]
    mentions = []
    n_emoji = len(CALL_EMOJIS)
    for i, r in enumerate(shown):
        emoji = CALL_EMOJIS[i % n_emoji]
        mentions.append(f'<a href="tg://user?id={r["user_id"]}">{emoji}</a>')
    mentions_line = " ".join(mentions)
    if total > CALL_MAX_MENTIONS:
        mentions_line += f"\n…и ещё {total - CALL_MAX_MENTIONS} чел."
    text = f"📢 ПОЗЫВНОЙ\n{DIV}\n\n{esc(call_text)}\n\n{DIV}\n\n{mentions_line}"
    try:
        await message.answer(text, parse_mode="HTML", reply_markup=back_kb(message.from_user.id))
    except Exception as e:
        await message.reply(f"⚠️ Не смог отправить позывной: {e}")


@dp.message(Command("calloff"))
async def cmd_calloff(message: types.Message):
    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)
    if user.get("call_opt_out"):
        await message.answer("🔕 Уведомления позывного уже отключены.\n\nВернуть: /callon", reply_markup=back_kb(message.from_user.id))
        return
    await update_user(message.from_user.id, chat_id, call_opt_out=1)
    await message.answer(f"🔕 Готово!\n{DIV}\n\nТеперь я не буду упоминать тебя в /call.\n\nВернуть: /callon", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("callon"))
async def cmd_callon(message: types.Message):
    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)
    if not user.get("call_opt_out"):
        await message.answer("🔔 Уведомления позывного и так включены.\n\nОтключить: /calloff", reply_markup=back_kb(message.from_user.id))
        return
    await update_user(message.from_user.id, chat_id, call_opt_out=0)
    await message.answer(f"🔔 Возвращаю тебя в список упоминаний.\n{DIV}\n\nЕсли снова захочешь отключить: /calloff", reply_markup=back_kb(message.from_user.id))