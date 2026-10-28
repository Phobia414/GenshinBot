from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp
from callbacks import MenuCB, TopCB
from constants import DIV
from db import (
    get_top_balance, get_top_messages, get_top_reputation,
    get_all_guilds, get_rep_level,
)
from helpers import esc, edit_or_send
from keyboards import tops_kb


@dp.callback_query(MenuCB.filter(F.action == "tops"))
async def cb_tops(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    text = f"🏆 ТОПЫ\n{DIV}\n\nВыбери категорию:"
    await edit_or_send(query, text, tops_kb(query.from_user.id))


def _render_top(users, value_key, title):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = [f"🏆 {title}\n{DIV}\n"]
    for i, u in enumerate(users, 1):
        medal = medals.get(i, f"{i}.")
        name = esc(u.get("character_name") or "?")
        val = u.get(value_key, 0)
        lines.append(f"{medal} {name} — {val}")
    text = "\n".join(lines)
    # Защита от превышения лимита Telegram (4096 символов)
    if len(text) > 3800:
        text = text[:3800] + "\n\n… (список обрезан из-за лимита Telegram)"
    return text


@dp.callback_query(TopCB.filter(F.action == "balance"))
async def cb_top_bal(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    # Запрашиваем Топ-50
    top = await get_top_balance(chat_id, 50)
    text = _render_top(top, "balance", "ТОП-50 ПО БАЛАНСУ")
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(TopCB.filter(F.action == "messages"))
async def cb_top_msg(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    top = await get_top_messages(chat_id, 50)
    text = _render_top(top, "messages_count", "ТОП-50 ПО СООБЩЕНИЯМ")
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(TopCB.filter(F.action == "reputation"))
async def cb_top_rep(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    top = await get_top_reputation(chat_id, 50)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = [f"🏆 ТОП-50 ПО РЕПУТАЦИИ\n{DIV}\n"]
    for i, u in enumerate(top, 1):
        medal = medals.get(i, f"{i}.")
        name = esc(u.get("character_name") or "?")
        lvl = get_rep_level(u.get("reputation") or 0)
        lines.append(f"{medal} {name} — ур. {lvl}")
    text = "\n".join(lines)
    if len(text) > 3800:
        text = text[:3800] + "\n\n… (список обрезан)"

    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(TopCB.filter(F.action == "guilds"))
async def cb_top_guilds(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    guilds = await get_all_guilds(chat_id, 50)
    if not guilds:
        text = f"🏰 ТОП-50 ГИЛЬДИЙ\n{DIV}\n\n(пока никого)"
    else:
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = [f"🏰 ТОП-50 ГИЛЬДИЙ\n{DIV}\n"]
        for i, g in enumerate(guilds, 1):
            medal = medals.get(i, f"{i}.")
            lines.append(f"{medal} {esc(g['name'])}")
            lines.append(f"   💰 {g['treasury']} · 👥 {g['members']}")
        text = "\n".join(lines)
        if len(text) > 3800:
            text = text[:3800] + "\n\n… (список обрезан)"

    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup())