from datetime import datetime, timezone, timedelta
import asyncio

from aiogram import types
from aiogram.filters import Command
from aiogram.types import ChatPermissions

from bot_instance import bot, dp
from config import OWNER_ID
from constants import DIV, WARN_LIMIT, WARN_MUTE_HOURS
from db import (
    get_user, create_user, update_user, add_warn, remove_warn,
    add_reputation, get_top_balance, get_top_messages, get_top_reputation,
    get_rep_level, RESIN_MAX,
    add_protected_user, remove_protected_user, get_protected_owner,
)
from helpers import esc, is_chat_admin, _ensure_user


@dp.message(Command("addmoney"))
async def cmd_addmoney(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /addmoney Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid)
    if not user:
        await message.answer("❌ Нет пользователя")
        return
    await update_user(tid, balance=user["balance"] + amount)
    await message.answer(f"✅ +{amount} монет. Баланс: {user['balance'] + amount}")


@dp.message(Command("setmoney"))
async def cmd_setmoney(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /setmoney Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid)
    if not user:
        await message.answer("❌ Нет")
        return
    await update_user(tid, balance=amount)
    await message.answer(f"✅ Баланс = {amount}")


@dp.message(Command("addrep"))
async def cmd_addrep(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /addrep Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid)
    if not user:
        await message.answer("❌ Нет")
        return
    await add_reputation(tid, amount)
    await message.answer(f"✅ +{amount} репутации. Всего: {(user['reputation'] or 0) + amount}")


@dp.message(Command("addresin"))
async def cmd_addresin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /addresin Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid)
    if not user:
        await message.answer("❌ Нет")
        return
    nr = min(RESIN_MAX, (user["resin"] or 0) + amount)
    await update_user(tid, resin=nr)
    await message.answer(f"✅ Смола: {nr}/{RESIN_MAX}")


@dp.message(Command("warn"))
async def cmd_warn(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Только в группе.")
        return
    if not await is_chat_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ Только админы.")
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение нарушителя.")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        await message.answer("❌ Себе нельзя.")
        return
    if target.is_bot:
        await message.answer("❌ Боту нельзя.")
        return
    user = await get_user(target.id)
    if not user:
        await create_user(target.id)
        user = await get_user(target.id)
    warns = await add_warn(target.id, 1)
    mention = f'<a href="tg://user?id={target.id}">{esc(target.first_name)}</a>'
    if warns >= WARN_LIMIT:
        mu = int((datetime.now(timezone.utc) + timedelta(hours=WARN_MUTE_HOURS)).timestamp())
        await update_user(target.id, muted_until=mu, warns=0)
        try:
            await bot.restrict_chat_member(chat_id=message.chat.id, user_id=target.id,
                permissions=ChatPermissions(can_send_messages=False), until_date=mu)
        except Exception as e:
            await message.answer(f"⚠️ Мут не удался: {e}")
        await message.answer(f"🚫 {mention} получил 3 варна и замучен на 24 часа!", parse_mode="HTML")
    else:
        await message.answer(f"⚠️ {mention}: {warns}/{WARN_LIMIT}", parse_mode="HTML")


@dp.message(Command("unwarn"))
async def cmd_unwarn(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    if not await is_chat_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение.")
        return
    target = message.reply_to_message.from_user
    warns = await remove_warn(target.id, 1)
    await message.answer(f"✅ Снято. Осталось: {warns}")


@dp.message(Command("mute"))
async def cmd_mute(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    if not await is_chat_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение и напиши /mute <мин>")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /mute <мин>")
        return
    minutes = int(parts[1])
    if minutes <= 0 or minutes > 10080:
        await message.answer("❌ 1-10080")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        await message.answer("❌ Себе")
        return
    mu = int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp())
    await update_user(target.id, muted_until=mu)
    try:
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False), until_date=mu)
    except Exception as e:
        await message.answer(f"⚠️ {e}")
        return
    mention = f'<a href="tg://user?id={target.id}">{esc(target.first_name)}</a>'
    await message.answer(f"🔇 {mention} замучен на {minutes} мин.", parse_mode="HTML")


@dp.message(Command("unmute"))
async def cmd_unmute(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    if not await is_chat_admin(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение.")
        return
    target = message.reply_to_message.from_user
    await update_user(target.id, muted_until=0)
    try:
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=target.id, permissions=ChatPermissions(
            can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True,
            can_send_videos=True, can_send_video_notes=True, can_send_voice_notes=True, can_send_polls=True,
            can_send_other_messages=True, can_add_web_page_previews=True,
            can_change_info=False, can_invite_users=True, can_pin_messages=False))
    except Exception as e:
        await message.answer(f"⚠️ {e}")
        return
    await message.answer(f"🔊 Размучен.", parse_mode="HTML")


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    tb = await get_top_balance(5)
    tm = await get_top_messages(5)
    tr = await get_top_reputation(5)
    lines = [f"📊 СТАТИСТИКА\n{DIV}\n", "💰 ТОП-5 БАЛАНС"]
    for i, u in enumerate(tb, 1):
        lines.append(f"{i}. {esc(u['character_name'] or '?')} — {u['balance']}")
    lines.append("\n💬 ТОП-5 СООБЩЕНИЯ")
    for i, u in enumerate(tm, 1):
        lines.append(f"{i}. {esc(u['character_name'] or '?')} — {u['messages_count']}")
    lines.append("\n🎖️ ТОП-5 РЕПУТАЦИЯ")
    for i, u in enumerate(tr, 1):
        lines.append(f"{i}. {esc(u['character_name'] or '?')} — ур. {get_rep_level(u['reputation'] or 0)}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("protect"))
async def cmd_protect(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец.")
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь реплаем на сообщение того, кого хочешь защитить.")
        return
    target = message.reply_to_message.from_user
    if target.id == OWNER_ID:
        await message.answer("❌ Себя защищать не надо.")
        return
    if target.is_bot:
        await message.answer("❌ Бота нельзя.")
        return
    await _ensure_user(target.id)
    await add_protected_user(target.id, message.from_user.id)
    await message.answer(f"✅ {esc(target.first_name)} теперь под защитой. "
                        f"Никто кроме тебя не сможет предложить ему отношения.")


@dp.message(Command("unprotect"))
async def cmd_unprotect(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец.")
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь реплаем на сообщение того, с кого снять защиту.")
        return
    target = message.reply_to_message.from_user
    owner = await get_protected_owner(target.id)
    if not owner:
        await message.answer(f"❌ {esc(target.first_name)} не под защитой.")
        return
    await remove_protected_user(target.id)
    await message.answer(f"✅ Защита с {esc(target.first_name)} снята.")