from datetime import datetime, timezone

from aiogram import types, F
from aiogram.filters import Command

from bot_instance import dp
from callbacks import MenuCB
from config import CREATOR_USERNAME
from constants import DIV, WARN_LIMIT, REP_PER_MESSAGE, REP_PER_BOARD_TASK, REP_PER_DUNGEON, \
    REP_PER_WORLD_BOSS_KILL, REP_PER_GUILD_BOSS_KILL, REP_PER_GUILD_CREATE, REP_PER_DONATE_UNIT, REP_PER_DONATE_MAX
from db import (
    get_user, update_user, get_guild, get_rep_level, get_rep_progress,
    update_resin, RESIN_MAX, get_food_buff, get_total_bonuses,
)
from helpers import (
    esc, user_display_name, find_region_by_character,
    get_reputation_bonuses, get_reputation_title,
    edit_or_send, _ensure_user,
)
from keyboards import main_menu_kb, profile_kb, adventurers_kb, reputation_kb
from characters import get_character_image
from handlers.chat_list import update_chat_list


@dp.callback_query(MenuCB.filter(F.action == "menu"))
async def cb_menu(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    name = esc(user_display_name(user))
    text = f"🌟 ГЛАВНОЕ МЕНЮ\n{DIV}\n\nПривет, {name}!\nКуда отправимся сегодня?\n\n{DIV}\n\n🧭 Меня создал {CREATOR_USERNAME}"
    await edit_or_send(query, text, main_menu_kb(query.from_user.id))


@dp.callback_query(MenuCB.filter(F.action == "profile"))
async def cb_profile(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    name = esc(user_display_name(user))
    gtext = "Мужской" if user["gender"] == "male" else ("Женский" if user["gender"] == "female" else "Не указан")
    if user["partner_id"]:
        status = "💍 В браке" if user["is_married"] else "💕 В отношениях"
        partner_line = f"❤️ {esc(user['partner_name'])} · {status}"
        if user["child_id"]:
            partner_line += f"\n👶 {esc(user['child_name'])}"
    else:
        partner_line = "❤️ Свободен(а)"
    if user["guild_id"]:
        g = await get_guild(user["guild_id"])
        if g:
            guild_line = f"🏰 {esc(g['name'])} · 👑 {esc(user['guild_rank'])}"
        else:
            guild_line = "🏰 Без гильдии"
    else:
        guild_line = "🏰 Без гильдии"
    earn_art, _ = await get_total_bonuses(query.from_user.id)
    rep_earn, _, _ = get_reputation_bonuses(user["reputation"])
    fn, fv = await get_food_buff(query.from_user.id)
    total_earn = earn_art + rep_earn + fv
    rep_level = get_rep_level(user["reputation"])
    rep_progress = (user["reputation"] or 0) % 500
    rinfo = find_region_by_character(user["character_name"])
    rname = rinfo[1] if rinfo else "Тейвата"
    rep_title = get_reputation_title(user["reputation"], rname)
    resin = await update_resin(query.from_user.id)
    parts = [
        f"🎴 ПРОФИЛЬ ПУТЕШЕСТВЕННИКА", DIV, "",
        f"🎭 {name} · ⚧ {gtext}", "",
        DIV, "",
        f"💰 Баланс: {user['balance']}",
        f"💧 Смола: {resin} / {RESIN_MAX}", "",
        DIV, "",
        f"🎖️ Репутация: {rep_level} / 10",
        f"📈 Прогресс: {rep_progress} / 500",
        f"{rep_title}", "",
        DIV, "",
        partner_line,
        guild_line,
    ]
    if total_earn or fn or user["warns"]:
        parts += ["", DIV, ""]
        if total_earn:
            parts.append(f"📊 Бонусы: +{total_earn}%")
        if fn:
            parts.append(f"🍳 {fn}: +{fv}%")
        if user["warns"]:
            parts.append(f"⚠️ Варны: {user['warns']} / {WARN_LIMIT}")
    text = "\n".join(parts)
    if user["character_name"]:
        image = get_character_image(user["character_name"])
        await edit_or_send(query, text, profile_kb(query.from_user.id), image_url=image)
    else:
        await edit_or_send(query, text, profile_kb(query.from_user.id), image_url="")


@dp.callback_query(MenuCB.filter(F.action == "freerole"))
async def cb_freerole(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user or not user["character_name"]:
        await query.answer("У тебя нет персонажа.", show_alert=True)
        return
    old = user["character_name"]
    await update_user(query.from_user.id, character_name="")
    
    # ВСПЛЫВАЮЩЕЕ ПРЕДУПРЕЖДЕНИЕ
    await query.answer("⚠️ Внимание! Ты освободил роль. Вернуть её (или взять другую) можно будет только купив Смену персонажа в Лавке за 1000 монет.", show_alert=True)
    
    chat_id = query.message.chat.id if query.message else 0
    if chat_id:
        await update_chat_list(chat_id)
    
    await cb_profile(query, MenuCB(action="profile", owner_id=query.from_user.id))


@dp.callback_query(MenuCB.filter(F.action == "adventurers"))
async def cb_adventurers(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    name = esc(user_display_name(user))
    text = (f"🏛️ ГИЛЬДИЯ ИСКАТЕЛЕЙ\n{DIV}\n\nДобро пожаловать, {name}!\n\n"
            f"{DIV}\n\n⚔ Подземелья\n📋 Доска занятости\n🎒 Артефакты\n"
            f"🐉 Мировые боссы\n🏰 Гильдии\n🎖 Репутация")
    await edit_or_send(query, text, adventurers_kb(query.from_user.id))


@dp.callback_query(MenuCB.filter(F.action == "reputation"))
async def cb_reputation(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    rep = user["reputation"] or 0
    level, cur, need = get_rep_progress(rep)
    rinfo = find_region_by_character(user["character_name"])
    rname = rinfo[1] if rinfo else "Тейвата"
    title = get_reputation_title(rep, rname)
    if level >= 10:
        pt = "Максимум!"
    else:
        filled = cur * 10 // 500
        pt = f"{'█' * filled}{'░' * (10 - filled)}   {cur} / 500"
    text = (f"🎖️ РЕПУТАЦИЯ\n{DIV}\n\n{title}\n\n{DIV}\n\n"
            f"📊 Уровень: {level} / 10\n"
            f"✨ Очки: {rep}\n"
            f"📈 {pt}\n\n"
            f"{DIV}\n\n"
            f"🎁 БОНУСЫ\n\n"
            f"• 3 ур. → +5% к заработку\n"
            f"• 5 ур. → -10% в лавке\n"
            f"• 7 ур. → +10% к дропу\n"
            f"• 10 ур. → 🏆 Герой региона\n\n"
            f"{DIV}\n\n"
            f"📚 ГДЕ ПОЛУЧИТЬ\n\n"
            f"💬 Сообщения: +{REP_PER_MESSAGE}\n"
            f"📋 Доска: +{REP_PER_BOARD_TASK}\n"
            f"⚔ Подземелья: +{REP_PER_DUNGEON}\n"
            f"🐉 Мировой босс: +{REP_PER_WORLD_BOSS_KILL}\n"
            f"🏰 Босс гильдии: +{REP_PER_GUILD_BOSS_KILL}\n"
            f"🏛 Создание гильдии: +{REP_PER_GUILD_CREATE} (1 раз)\n"
            f"💛 /donate: +1 за {REP_PER_DONATE_UNIT} (макс {REP_PER_DONATE_MAX})")
    await edit_or_send(query, text, reputation_kb(query.from_user.id))


@dp.message(Command("freerole"))
async def cmd_freerole(message: types.Message):
    user = await _ensure_user(message.from_user.id)
    if not user["character_name"]:
        await message.answer("У тебя нет персонажа.")
        return
    old = user["character_name"]
    await update_user(message.from_user.id, character_name="")
    
    await message.answer(f"✅ Роль «{esc(old)}» освобождена.\n\n⚠️ <b>Внимание!</b> Вернуть её (или взять другую) можно будет только купив Смену персонажа в Лавке за 1000 монет.", parse_mode="HTML")
    
    await update_chat_list(message.chat.id)