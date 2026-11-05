from datetime import datetime, timezone
from aiogram import types, F
from bot_instance import dp
from db import fetch_all
from helpers import esc


@dp.message(F.text.lower().startswith("!стат"))
async def cmd_stats(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("❌ Эта команда работает только в группах.")

    chat_id = message.chat.id
    text_lower = message.text.lower()

    if "недел" in text_lower:
        col_name = "msgs_week"
        title = "НЕДЕЛЮ"
    elif "месяц" in text_lower:
        col_name = "msgs_month"
        title = "МЕСЯЦ"
    else:
        return await message.answer("⚠️ Используй: <code>!статистика неделя</code> или <code>!статистика месяц</code>",
                                    parse_mode="HTML")

    users = await fetch_all(
        f"SELECT user_id, character_name, username, {col_name} as msgs, last_msg_time "
        f"FROM users WHERE chat_id = ? ORDER BY msgs DESC",
        (chat_id,)
    )

    if not users:
        return await message.answer("В этом чате пока нет игроков.")

    now = int(datetime.now(timezone.utc).timestamp())
    active_lines = []
    inactive_lines = []

    for u in users:
        msgs = u["msgs"] or 0
        if not u["character_name"] and not u["username"] and msgs == 0:
            continue

        name = esc(u["character_name"] or u["username"] or f"Игрок {u['user_id']}")
        last_time = u["last_msg_time"] or 0
        days_inactive = (now - last_time) // 86400

        if msgs > 0 or days_inactive < 1:
            active_lines.append(f"╭ {name} — <b>{msgs}</b> сообщ.")
        else:
            inactive_lines.append(f"╭ {name} — 💤 {days_inactive} дн. неактива")

    text = f"── 〔 📊 СТАТИСТИКА ЗА {title} 〕 ──\n\n"
    text += "<b>🔥 Активные участники:</b>\n"
    if active_lines:
        text += "\n".join(active_lines[:40])
        if len(active_lines) > 40:
            text += f"\n╰ ... и еще {len(active_lines) - 40} чел."
        else:
            text += "\n╰"
    else:
        text += "╭ Все молчат...\n╰"

    if inactive_lines:
        text += "\n\n<b>💤 Неактивные (от 1 дня):</b>\n"
        text += "\n".join(inactive_lines[:30])
        if len(inactive_lines) > 30:
            text += f"\n╰ ... и еще {len(inactive_lines) - 30} чел."
        else:
            text += "\n╰"

    if len(text) > 4000:
        text = text[:4000] + "\n\n... (список обрезан из-за лимита Telegram)"

    await message.answer(text, parse_mode="HTML")