from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp
from callbacks import MenuCB, TopCB
from constants import DIV
from db import (
    get_top_balance, get_top_messages, get_top_reputation,
    get_all_guilds, get_rep_level, get_local_setting
)
from helpers import esc, edit_or_send, get_section_image


@dp.callback_query(MenuCB.filter(F.action == "tops"))
async def cb_tops(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    text = f"— [ 🏆 ТОПЫ ] —\n\nВыбери категорию:\n"
    chat_id = query.message.chat.id
    custom_img = await get_local_setting("image_tops", chat_id)
    await edit_or_send(query, text, tops_kb(query.from_user.id), image_url=custom_img or "")


def tops_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="⊱ 💰 По балансу ⊰", callback_data=TopCB(action="balance", owner_id=uid))
    b.button(text="⊱ 💬 По сообщениям ⊰", callback_data=TopCB(action="messages", owner_id=uid))
    b.button(text="⊱ 🎖 По репутации ⊰", callback_data=TopCB(action="reputation", owner_id=uid))
    b.button(text="⊱ 🏰 По гильдиям ⊰", callback_data=TopCB(action="guilds", owner_id=uid))
    b.button(text="⊱ ‹ Назад в меню ⊰", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def _render_top(users, value_key, title):
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = [f"— [ 🏆 {title} ] —\n"]
    for i, u in enumerate(users, 1):
        medal = medals.get(i, f"{i}.")
        name = esc(u.get("character_name") or "Неизвестный")
        val = u.get(value_key, 0)
        lines.append(f"{medal} {name} — {val}")
    if len(lines) > 1:
        text = "\n".join(lines)
    else:
        text = f"— [ 🏆 {title} ] —\n\nПока никого нет."
    if len(text) > 3800:
        text = text[:3800] + "\n\n… (список обрезан)"
    return text


@dp.callback_query(TopCB.filter(F.action == "balance"))
async def cb_top_bal(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id: return
    chat_id = query.message.chat.id
    top = await get_top_balance(chat_id, 50)
    text = _render_top(top, "balance", "ТОП-50 ПО БАЛАНСУ")
    b = InlineKeyboardBuilder().button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup(), image_url="")


@dp.callback_query(TopCB.filter(F.action == "messages"))
async def cb_top_msg(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id: return
    chat_id = query.message.chat.id
    top = await get_top_messages(chat_id, 50)
    text = _render_top(top, "messages_count", "ТОП-50 ПО СООБЩЕНИЯМ")
    b = InlineKeyboardBuilder().button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup(), image_url="")


@dp.callback_query(TopCB.filter(F.action == "reputation"))
async def cb_top_rep(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id: return
    chat_id = query.message.chat.id
    top = await get_top_reputation(chat_id, 50)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = [f"— [ 🏆 ТОП-50 ПО РЕПУТАЦИИ ] —\n"]
    for i, u in enumerate(top, 1):
        medal = medals.get(i, f"{i}.")
        name = esc(u.get("character_name") or "Неизвестный")
        lvl = get_rep_level(u.get("reputation") or 0)
        lines.append(f"{medal} {name} — ур. {lvl}")
    if len(lines) > 1:
        text = "\n".join(lines)
    else:
        text = f"— [ 🏆 ТОП-50 ПО РЕПУТАЦИИ ] —\n\nПока никого нет."
    if len(text) > 3800:
        text = text[:3800] + "\n\n… (список обрезан)"
    b = InlineKeyboardBuilder().button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup(), image_url="")


@dp.callback_query(TopCB.filter(F.action == "guilds"))
async def cb_top_guilds(query: types.CallbackQuery, callback_data: TopCB):
    if query.from_user.id != callback_data.owner_id: return
    chat_id = query.message.chat.id
    guilds = await get_all_guilds(chat_id, 50)

    # ИСПРАВЛЕНИЕ (Баг 8): Убираем гильдии, в которых 0 участников
    guilds = [g for g in guilds if g.get('members', 0) > 0]

    if not guilds:
        text = f"— [ 🏰 ТОП-50 ГИЛЬДИЙ ] —\n\n(пока никого)"
    else:
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        lines = [f"— [ 🏰 ТОП-50 ГИЛЬДИЙ ] —\n"]
        for i, g in enumerate(guilds, 1):
            medal = medals.get(i, f"{i}.")
            lines.append(f"{medal} {esc(g['name'])}")
            lines.append(f"💰 {g['treasury']} · 👥 {g['members']}")
            lines.append("")
        lines.pop()
        text = "\n".join(lines)
        if len(text) > 3800:
            text = text[:3800] + "\n\n… (список обрезан)"
    b = InlineKeyboardBuilder().button(text="‹ Назад", callback_data=MenuCB(action="tops", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup(), image_url="")