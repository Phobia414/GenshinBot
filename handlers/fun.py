import random
from datetime import datetime, timezone

from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from callbacks import MenuCB, FunCB, DuelCB
from config import OWNER_ID, PROPOSE_COOLDOWN
from constants import DIV
from db import get_user, update_user, get_setting
from helpers import (
    esc, edit_or_send, _ensure_user, extract_target, resolve_user_id, _now_ts, get_section_image
)
from keyboards import (
    fun_menu_kb, back_kb,
)
from state import _duel_cooldown


@dp.callback_query(MenuCB.filter(F.action == "fun"))
async def cb_fun(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    user = await get_user(query.from_user.id, chat_id)
    from helpers import user_display_name
    name = esc(user_display_name(user))

    default_text = f"🎲 РАЗВЛЕЧЕНИЯ\n{{div}}\n\n{{name}}, чем займёмся?\n\n{{div}}\n\n⚔ Дуэль"
    raw_text = await get_setting("text_fun", default_text)
    text = raw_text.replace("{name}", name).replace("{div}", DIV)

    image = await get_section_image("fun")
    await edit_or_send(query, text, fun_menu_kb(query.from_user.id), image_url=image)


@dp.callback_query(FunCB.filter(F.action == "duel_help"))
async def cb_duel_help(query: types.CallbackQuery, callback_data: FunCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="fun", owner_id=query.from_user.id))

    default_text = (
        f"⚔️ ДУЭЛЬ\n{{div}}\n\n"
        f"Ответь на сообщение игрока и напиши:\n"
        f"<code>/duel Сумма</code> или <code>Вызвать на дуэль Сумма</code>\n\n"
        f"Или укажи его @username:\n"
        f"<code>/duel @user Сумма</code>"
    )
    raw_text = await get_setting("text_duel_help", default_text)
    text = raw_text.replace("{div}", DIV)

    image = await get_section_image("fun")
    await edit_or_send(query, text, b.as_markup(), image_url=image)


async def start_duel_logic(message: types.Message, target_ref, display: str, bet: int):
    chat_id = message.chat.id
    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            await message.answer(f"❌ Не нашёл @{target_ref}. Пусть игрок напишет в чат с ботом.")
            return
    else:
        target_id = target_ref

    if target_id == message.from_user.id:
        await message.answer("❌ Себя нельзя.")
        return

    me = await _ensure_user(message.from_user.id, chat_id)
    other = await _ensure_user(target_id, chat_id)

    try:
        tg_target = await bot.get_chat(target_id)
        if getattr(tg_target, "is_bot", False):
            await message.answer("❌ Бота нельзя.")
            return
    except Exception:
        pass

    if not me["character_name"]:
        await message.answer("❌ Сначала выбери персонажа: /start")
        return
    if not other["character_name"]:
        await message.answer(f"❌ {esc(display)} ещё не выбрал персонажа.")
        return
    if me["balance"] < bet:
        await message.answer("❌ У тебя мало монет")
        return
    if other["balance"] < bet:
        await message.answer(f"❌ У {esc(display)} мало монет")
        return

    if message.from_user.id != OWNER_ID:
        key = ("duel", message.from_user.id, target_id, chat_id)
        now_ts = _now_ts()
        last = _duel_cooldown.get(key, 0)
        if now_ts - last < PROPOSE_COOLDOWN:
            left = int(PROPOSE_COOLDOWN - (now_ts - last))
            await message.answer(f"⏳ Ты уже вызывал(а) этого игрока. Подожди {left} сек.")
            return
        _duel_cooldown[key] = now_ts

    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять", callback_data=DuelCB(action="accept",
                                                    challenger_id=message.from_user.id,
                                                    target_id=target_id, bet=bet))
    b.button(text="❌ Отклонить", callback_data=DuelCB(action="decline",
                                                      challenger_id=message.from_user.id,
                                                      target_id=target_id, bet=bet))
    b.adjust(2)
    mention = f'<a href="tg://user?id={target_id}">{esc(display)}</a>'
    ch = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'

    await message.answer(
        f"⚔️ ВЫЗОВ НА ДУЭЛЬ\n{DIV}\n\n{mention}, {ch}\nвызывает тебя на дуэль!\n\n💰 Ставка: {bet}",
        reply_markup=b.as_markup(), parse_mode="HTML")


@dp.message(Command("duel"))
async def cmd_duel(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Дуэль работает только в группе.")
        return
    target_ref, display = extract_target(message)
    if target_ref is None:
        await message.answer("⚔️ Ответь на сообщение игрока и напиши /duel Сумма\n(или /duel @user Сумма)")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[-1].isdigit():
        await message.answer("Используй: /duel Сумма (ответом) или /duel @user Сумма")
        return
    bet = int(parts[-1])
    if bet <= 0:
        await message.answer("❌ Сумма > 0")
        return

    await start_duel_logic(message, target_ref, display, bet)


@dp.callback_query(DuelCB.filter())
async def cb_duel(query: types.CallbackQuery, callback_data: DuelCB):
    if query.from_user.id != callback_data.target_id:
        await query.answer("❌ Не для тебя!", show_alert=True)
        return
    chat_id = query.message.chat.id
    if callback_data.action == "decline":
        text = f"🕊️ ОТКЛОНЕНО\n{DIV}\n\nМирное решение!"
        await query.message.edit_text(text, reply_markup=back_kb(query.from_user.id))
        return
    ch = await get_user(callback_data.challenger_id, chat_id)
    tg = await get_user(callback_data.target_id, chat_id)
    if ch["balance"] < callback_data.bet or tg["balance"] < callback_data.bet:
        await query.answer("❌ Мало монет.", show_alert=True)
        return
    r1, r2 = random.randint(1, 100), random.randint(1, 100)
    while r1 == r2:
        r2 = random.randint(1, 100)
    if r1 > r2:
        await update_user(callback_data.challenger_id, chat_id, balance=ch["balance"] + callback_data.bet)
        await update_user(callback_data.target_id, chat_id, balance=tg["balance"] - callback_data.bet)
    else:
        await update_user(callback_data.target_id, chat_id, balance=tg["balance"] + callback_data.bet)
        await update_user(callback_data.challenger_id, chat_id, balance=ch["balance"] - callback_data.bet)
    text = f"⚔️ ДУЭЛЬ ЗАВЕРШЕНА\n{DIV}\n\n🎲 {r1} vs {r2}\n\n🏆 Победитель забирает {callback_data.bet}!"
    # ИСПРАВЛЕНО: Добавлена кнопка "Назад", чтобы сообщение не исчезло
    await query.message.edit_text(text, reply_markup=back_kb(query.from_user.id))