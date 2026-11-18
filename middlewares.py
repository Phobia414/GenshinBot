import asyncio
from aiogram import types
from bot_instance import dp
from config import OWNER_ID, CMD_COOLDOWN, CB_COOLDOWN
from db import get_user, update_user, add_known_group, get_setting, is_user_blocked
from helpers import _ensure_user, _now_ts
from state import _username_cache, _cb_cooldown, _cmd_cooldown
import state
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter


def _remember_username(tg_user):
    if tg_user and not tg_user.is_bot and tg_user.username:
        _username_cache[tg_user.username.lower()] = tg_user.id


@dp.message.middleware()
async def check_blocked_msg(handler, event: types.Message, data: dict):
    if event.from_user.id == OWNER_ID:
        return await handler(event, data)

    if await is_user_blocked(event.from_user.id):
        return
    return await handler(event, data)


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
async def check_subscription_middleware(handler, event: types.Message, data: dict):
    if event.chat.type not in ("group", "supergroup"):
        return await handler(event, data)

    if not event.from_user or event.from_user.is_bot:
        return await handler(event, data)

    if event.from_user.id == OWNER_ID:
        return await handler(event, data)

    sub_enabled = await get_setting("sub_enabled", "0")
    if sub_enabled != "1":
        return await handler(event, data)

    user = await get_user(event.from_user.id, event.chat.id)
    if not user:
        return await handler(event, data)

    if user.get("sub_passed") == 1 or (event.text and event.text.startswith("/start")):
        return await handler(event, data)

    try:
        await event.delete()
        from handlers.subscription import send_sub_message
        await send_sub_message(event, event.from_user.id, event.chat.id)
    except Exception as e:
        print(f"Ошибка в middleware подписки: {e}")
    return


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
async def check_blocked_cb(handler, event: types.CallbackQuery, data: dict):
    if event.from_user.id == OWNER_ID:
        return await handler(event, data)

    if await is_user_blocked(event.from_user.id):
        await event.answer("⛔ Вы заблокированы в боте.", show_alert=True)
        return
    return await handler(event, data)


@dp.callback_query.middleware()
async def check_user_character_middleware(handler, event: types.CallbackQuery, data: dict):
    cb_data = event.data or ""

    # 1. СПИСОК ИСКЛЮЧЕНИЙ
    allowed_prefixes = (
        "menu:gender_", "menu:regions", "reg:", "char:", "menu:tops", "top:",
        "menu:lists", "lists:", "cmd:", "apply_", "appr_", "newchar_",
        "sub:", "report_", "rep:", "a_ans_", "aapp:", "admin_"
    )

    if cb_data.startswith(allowed_prefixes):
        return await handler(event, data)

    # 2. ЕСЛИ ЭТО ЛИЧНЫЕ СООБЩЕНИЯ (ЛС) - ПРОПУСКАЕМ ПРОВЕРКУ
    if not event.message or event.message.chat.type not in ("group", "supergroup"):
        return await handler(event, data)

    # 3. Пропускаем кнопки, если человек в процессе анкеты
    state_obj: FSMContext = data.get("state")
    if state_obj:
        current_state = await state_obj.get_state()
        if current_state and (
                current_state.startswith("AdminApplyForm") or
                current_state.startswith("ApplyForm") or
                current_state.startswith("ReviewForm")
        ):
            return await handler(event, data)

    # 4. Основная проверка (только для групп)
    chat_id = event.message.chat.id
    user = await get_user(event.from_user.id, chat_id)

    if not user or not user.get("character_name"):
        if not cb_data.startswith("menu:menu"):
            await event.answer("❌ Сначала выбери персонажа: /start", show_alert=True)
            return

    return await handler(event, data)


@dp.callback_query.middleware()
async def auto_register_cb(handler, event: types.CallbackQuery, data: dict):
    chat_id = 0
    chat_type = "private"
    try:
        if event.message:
            chat_id = event.message.chat.id
            chat_type = event.message.chat.type
    except:
        pass

    if event.from_user and not event.from_user.is_bot:
        _remember_username(event.from_user)
        u = await _ensure_user(event.from_user.id, chat_id)
        if event.from_user.username and u and u.get("username") != event.from_user.username:
            await update_user(event.from_user.id, chat_id, username=event.from_user.username)

    if chat_type in ("group", "supergroup"):
        if event.from_user.id != OWNER_ID:
            sub_enabled = await get_setting("sub_enabled", "0")
            if sub_enabled == "1":
                u = await get_user(event.from_user.id, chat_id)
                if u and u.get("sub_passed") == 0:
                    cb_data = event.data or ""
                    if not cb_data.startswith(("sub:", "start", "report_")):
                        await event.answer("❌ Сначала подпишитесь на каналы! Напишите /start в группе.",
                                           show_alert=True)
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