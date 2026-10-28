import asyncio
from aiogram import types
from bot_instance import dp
from config import OWNER_ID, CMD_COOLDOWN, CB_COOLDOWN
from db import get_user, update_user, add_known_group
from helpers import _ensure_user, _now_ts
from state import _username_cache, _cb_cooldown, _cmd_cooldown
import state


def _remember_username(tg_user):
    if tg_user and not tg_user.is_bot and tg_user.username:
        _username_cache[tg_user.username.lower()] = tg_user.id


@dp.message.middleware()
async def auto_register_msg(handler, event: types.Message, data: dict):
    if event.chat.type in ("group", "supergroup"):
        state._known_groups.add(event.chat.id)
        await add_known_group(event.chat.id)
    if event.from_user and not event.from_user.is_bot:
        _remember_username(event.from_user)
        u = await _ensure_user(event.from_user.id, event.chat.id)
        if event.from_user.username and u and u.get("username") != event.from_user.username:
            await update_user(event.from_user.id, event.chat.id, username=event.from_user.username)
    return await handler(event, data)


@dp.message.middleware()
async def cmd_antispam(handler, event: types.Message, data: dict):
    if not event.text or not event.text.startswith("/"): return await handler(event, data)
    if event.from_user.id == OWNER_ID: return await handler(event, data)
    key = (event.from_user.id, event.chat.id)
    now_ts = _now_ts()
    last = _cmd_cooldown.get(key, 0)
    if now_ts - last < CMD_COOLDOWN:
        try:
            await event.reply(f"⏳ Слишком часто. Подожди {CMD_COOLDOWN:.1f} сек.")
        except:
            pass
        return
    _cmd_cooldown[key] = now_ts
    return await handler(event, data)


@dp.callback_query.middleware()
async def auto_register_cb(handler, event: types.CallbackQuery, data: dict):
    chat_id = 0
    try:
        chat_id = event.message.chat.id if event.message else 0
    except:
        pass

    if event.from_user and not event.from_user.is_bot:
        _remember_username(event.from_user)
        u = await _ensure_user(event.from_user.id, chat_id)
        if event.from_user.username and u and u.get("username") != event.from_user.username:
            await update_user(event.from_user.id, chat_id, username=event.from_user.username)

    allowed_prefixes = ("menu:gender_", "menu:regions", "reg:", "char:", "menu:tops", "top:", "menu:lists", "lists:",
                        "cmd:")
    cb_data = event.data or ""
    if not cb_data.startswith(allowed_prefixes):
        if event.from_user.id != OWNER_ID:
            u = await get_user(event.from_user.id, chat_id)
            if not u or not u["character_name"]:
                await event.answer("❌ Сначала выбери персонажа: /start", show_alert=True)
                return

    if event.from_user.id != OWNER_ID:
        key = (event.from_user.id, chat_id)
        now_ts = _now_ts()
        last = _cb_cooldown.get(key, 0)
        if now_ts - last < CB_COOLDOWN:
            try:
                await event.answer("⏳ Слишком быстро.", show_alert=False)
            except:
                pass
            return
        _cb_cooldown[key] = now_ts

    handler_task = asyncio.create_task(handler(event, data))

    async def delayed_answer():
        await asyncio.sleep(1.5)
        if not handler_task.done():
            try:
                await event.answer()
            except:
                pass

    delayed_task = asyncio.create_task(delayed_answer())
    try:
        return await handler_task
    finally:
        delayed_task.cancel()
        try:
            await event.answer()
        except:
            pass