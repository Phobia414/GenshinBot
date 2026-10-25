from datetime import datetime, timezone

from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiosqlite

from bot_instance import dp
from callbacks import MenuCB, GuildCB
from config import DB_PATH
from constants import DIV, GUILD_CREATE_PRICE, REP_PER_GUILD_CREATE, REP_PER_DONATE_UNIT, REP_PER_DONATE_MAX
from db import (
    get_user, update_user, get_guild, get_guild_by_name, create_guild,
    update_guild, get_all_guilds, get_guild_members,
)
from helpers import esc, user_display_name, edit_or_send, _ensure_user, _gain_rep
from keyboards import guild_menu_kb, guild_list_kb, back_kb


@dp.callback_query(MenuCB.filter(F.action == "guild"))
async def cb_guild(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    has = bool(user["guild_id"])
    is_owner = False
    if has:
        g = await get_guild(user["guild_id"])
        if g and g["owner_id"] == query.from_user.id:
            is_owner = True
    if has:
        g = await get_guild(user["guild_id"])
        text = (f"🏰 ГИЛЬДИЯ «{esc(g['name']).upper()}»\n{DIV}\n\n"
                f"{esc(user_display_name(user))}\n"
                f"Ранг: {esc(user['guild_rank'])}\n"
                f"Вклад: {user['guild_contribution']}")
    else:
        text = (f"🏰 ГИЛЬДИИ\n{DIV}\n\n{esc(user_display_name(user))}, ты пока\nбез гильдии.\n\n"
                f"Создай за 700 или вступи.\n\n"
                f"🎖️ За создание: +{REP_PER_GUILD_CREATE} репутации\n(начисляется один раз)")
    await edit_or_send(query, text, guild_menu_kb(query.from_user.id, has, is_owner))


@dp.callback_query(GuildCB.filter(F.action == "create"))
async def cb_guild_create(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if user["guild_id"]:
        await query.answer("❌ Ты уже в гильдии!", show_alert=True)
        return
    if user["balance"] < GUILD_CREATE_PRICE:
        await query.answer(f"❌ Нужно {GUILD_CREATE_PRICE}", show_alert=True)
        return
    if not user.get("guild_bonus_claimed"):
        rep_info = f"\n🎖️ Бонус: +{REP_PER_GUILD_CREATE} репутации"
    else:
        rep_info = "\n🎖️ Репутационный бонус уже был получен"
    text = (f"💰 СОЗДАНИЕ ГИЛЬДИИ\n{DIV}\n\n"
            f"Стоимость: {GUILD_CREATE_PRICE} монет{rep_info}\n\n"
            f"Напиши:\n/createguild Название")
    await edit_or_send(query, text, back_kb(query.from_user.id))


@dp.callback_query(GuildCB.filter(F.action == "list"))
async def cb_guild_list(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    guilds = await get_all_guilds()
    if not guilds:
        text = f"📜 СПИСОК ГИЛЬДИЙ\n{DIV}\n\nПока нет гильдий."
        await edit_or_send(query, text, guild_list_kb(query.from_user.id, []))
        return
    text = f"📜 СПИСОК ГИЛЬДИЙ\n{DIV}\n\nТоп по казне:"
    await edit_or_send(query, text, guild_list_kb(query.from_user.id, guilds))


@dp.callback_query(GuildCB.filter(F.action == "join"))
async def cb_guild_join(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if user["guild_id"]:
        await query.answer("❌ Ты уже в гильдии!", show_alert=True)
        return
    g = await get_guild(callback_data.guild_id)
    if not g:
        await query.answer("❌ Не найдено", show_alert=True)
        return
    await update_user(query.from_user.id, guild_id=g["guild_id"], guild_rank="Участник", guild_contribution=0)
    text = f"🎉 ДОБРО ПОЖАЛОВАТЬ!\n{DIV}\n\nТы вступил(а) в\n«{esc(g['name'])}»!"
    await edit_or_send(query, text, back_kb(query.from_user.id))


@dp.callback_query(GuildCB.filter(F.action == "info"))
async def cb_guild_info(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["guild_id"]:
        await query.answer("❌ Ты не в гильдии.", show_alert=True)
        return
    g = await get_guild(user["guild_id"])
    if not g:
        await query.answer("❌ Не найдено", show_alert=True)
        return
    members = await get_guild_members(g["guild_id"])
    created = datetime.fromtimestamp(g["created_at"], timezone.utc).strftime("%d.%m.%Y")
    text = (f"🏰 ГИЛЬДИЯ «{esc(g['name']).upper()}»\n{DIV}\n\n"
            f"👑 Лидер: {esc(g['owner_name'])}\n"
            f"📅 Создана: {created}\n\n"
            f"{DIV}\n\n"
            f"👥 Участники: {len(members)}\n"
            f"💰 Казна: {g['treasury']}\n"
            f"📊 Очки недели: {g['week_points']}")
    await edit_or_send(query, text, guild_menu_kb(query.from_user.id, True, g["owner_id"] == query.from_user.id))


@dp.callback_query(GuildCB.filter(F.action == "members"))
async def cb_guild_members(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["guild_id"]:
        await query.answer("❌ Ты не в гильдии.", show_alert=True)
        return
    members = await get_guild_members(user["guild_id"])
    lines = [f"👥 СОСТАВ ГИЛЬДИИ ({len(members)})\n{DIV}\n"]
    for m in members[:50]:
        nm = esc(m['character_name'] or 'Игрок')
        lines.append(f"• {nm} — {esc(m['guild_rank'])}\n  вклад: {m['guild_contribution']}")
    if len(members) > 50:
        lines.append(f"\n… ещё {len(members) - 50}")
    text = "\n".join(lines)
    if len(text) > 3800:
        text = text[:3800] + "\n…"
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="guild", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(GuildCB.filter(F.action == "treasury"))
async def cb_guild_treasury(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["guild_id"]:
        await query.answer("❌ Ты не в гильдии.", show_alert=True)
        return
    g = await get_guild(user["guild_id"])
    text = (f"💰 КАЗНА ГИЛЬДИИ\n{DIV}\n\n«{esc(g['name'])}»\n\n{g['treasury']} монет\n\n"
            f"{DIV}\n\nПополнить:\n/donate Сумма\n\n"
            f"🎖️ За каждые {REP_PER_DONATE_UNIT} монет: +1 репутации")
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="guild", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(GuildCB.filter(F.action == "leave"))
async def cb_guild_leave(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["guild_id"]:
        await query.answer("❌ Не в гильдии.", show_alert=True)
        return
    g = await get_guild(user["guild_id"])
    if g and g["owner_id"] == query.from_user.id:
        await query.answer("❌ Владелец не может выйти. Используй /disbandguild", show_alert=True)
        return
    await update_user(query.from_user.id, guild_id=0, guild_rank="Участник", guild_contribution=0)
    text = f"👋 ПОКА!\n{DIV}\n\nТы вышел(ла) из гильдии."
    await edit_or_send(query, text, back_kb(query.from_user.id))


@dp.callback_query(GuildCB.filter(F.action == "manage"))
async def cb_guild_manage(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id:
        await query.answer("❌ Только лидер.", show_alert=True)
        return
    text = f"⚙️ УПРАВЛЕНИЕ ГИЛЬДИЕЙ\n{DIV}\n\n• /disbandguild — распустить\n• /donate Сумма — казна"
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="guild", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup())


@dp.message(Command("createguild"))
async def cmd_createguild(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Только в группе.")
        return
    user = await _ensure_user(message.from_user.id)
    if user["guild_id"]:
        await message.answer("❌ Ты уже в гильдии.")
        return
    if user["balance"] < GUILD_CREATE_PRICE:
        await message.answer(f"❌ Нужно {GUILD_CREATE_PRICE} монет.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используй: /createguild Название")
        return
    name = parts[1].strip()[:32]
    if await get_guild_by_name(name):
        await message.answer(f"❌ Гильдия «{esc(name)}» уже существует.")
        return
    gid = await create_guild(name, message.from_user.id, user["character_name"] or "Игрок")
    await update_user(message.from_user.id, balance=user["balance"] - GUILD_CREATE_PRICE,
                      guild_id=gid, guild_rank="Лидер")
    if not user.get("guild_bonus_claimed"):
        await update_user(message.from_user.id, guild_bonus_claimed=1)
        await _gain_rep(message.from_user.id, message.chat.id, REP_PER_GUILD_CREATE, message.from_user.first_name)
        rep_line = f"\n🎖️ +{REP_PER_GUILD_CREATE} репутации"
    else:
        rep_line = "\n🎖️ Бонус за создание уже получен ранее"
    await message.answer(
        f"🏰 ГИЛЬДИЯ СОЗДАНА!\n{DIV}\n\n«{esc(name)}»\nТы — Лидер.\n\n-{GUILD_CREATE_PRICE} монет{rep_line}")


@dp.message(Command("donate"))
async def cmd_donate(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Только в группе.")
        return
    user = await _ensure_user(message.from_user.id)
    if not user["guild_id"]:
        await message.answer("❌ Ты не в гильдии.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /donate Сумма")
        return
    amount = int(parts[1])
    if amount <= 0:
        await message.answer("❌ Сумма > 0.")
        return
    if user["balance"] < amount:
        await message.answer("❌ Не хватает.")
        return
    g = await get_guild(user["guild_id"])
    await update_user(message.from_user.id, balance=user["balance"] - amount,
                      guild_contribution=user["guild_contribution"] + amount)
    await update_guild(g["guild_id"], treasury=g["treasury"] + amount)
    rep_gain = min(REP_PER_DONATE_MAX, (amount // REP_PER_DONATE_UNIT))
    if rep_gain > 0:
        await _gain_rep(message.from_user.id, message.chat.id, rep_gain, message.from_user.first_name)
    await message.answer(f"💛 Ты внёс(ла) {amount} монет.\n🎖️ Репутация: +{rep_gain}")


@dp.message(Command("disbandguild"))
async def cmd_disbandguild(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Только в группе.")
        return
    user = await _ensure_user(message.from_user.id)
    if not user["guild_id"]:
        await message.answer("❌ Ты не в гильдии.")
        return
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != message.from_user.id:
        await message.answer("❌ Только лидер.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET guild_id = 0, guild_rank = 'Участник', guild_contribution = 0 WHERE guild_id = ?",
            (g["guild_id"],))
        await db.execute("DELETE FROM guilds WHERE guild_id = ?", (g["guild_id"],))
        await db.commit()
    await message.answer(f"🏰 Гильдия «{esc(g['name'])}» распущена.")