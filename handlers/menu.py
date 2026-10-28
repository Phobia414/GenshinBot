from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command
from bot_instance import bot, dp
from callbacks import MenuCB
from config import CREATOR_USERNAME, PRICE_ROLE_CHANGE
from constants import DIV, WARN_LIMIT, REP_PER_MESSAGE, REP_PER_BOARD_TASK, REP_PER_DUNGEON, REP_PER_WORLD_BOSS_KILL, \
    REP_PER_GUILD_BOSS_KILL, REP_PER_GUILD_CREATE, REP_PER_DONATE_UNIT, REP_PER_DONATE_MAX
from db import get_user, update_user, get_guild, get_rep_level, get_rep_progress, update_resin, RESIN_MAX, \
    get_food_buff, get_total_bonuses, get_local_setting
from helpers import esc, user_display_name, find_region_by_character, get_reputation_bonuses, get_reputation_title, \
    edit_or_send, _ensure_user, get_section_image, inject_user, format_text
from keyboards import main_menu_kb, profile_kb, adventurers_kb, reputation_kb, regions_kb, back_kb
from characters import get_character_image, REGIONS
from handlers.chat_list import update_chat_list
from aiogram.types import FSInputFile


@dp.callback_query(MenuCB.filter(F.action == "menu"))
@inject_user
async def cb_menu(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    if user.get("char_change_paid") == 1:
        return await edit_or_send(query, f"🌸 ВЫБОР ПЕРСОНАЖА\n{DIV}\n\nТы оплатил смену!\nВыбери регион:",
                                  regions_kb(query.from_user.id))

    name = esc(user_display_name(user))
    days = (int(datetime.now(timezone.utc).timestamp()) - (user.get("first_seen") or 0)) // 86400

    region_display = "Тейват"
    if user.get("character_name"):
        from helpers import get_character_region
        r_key = get_character_region(user["character_name"])
        if r_key and r_key in REGIONS and r_key != "other":
            region_display = REGIONS[r_key].split(" ", 1)[1] if " " in REGIONS[r_key] else REGIONS[r_key]

    # --- ИСПРАВЛЕННЫЙ КОД: Получаем ранг репутации для статуса ---
    rep = user.get("reputation", 0) or 0
    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"

    if " " in reg_name_for_title:
        reg_name_for_title = reg_name_for_title.split(" ", 1)[1]

    rep_title = get_reputation_title(rep, reg_name_for_title)
    # ------------------------------------------------------

    text = (
        f"╓───────────────────────╖\n"
        f"   🎴 ГЛАВНОЕ МЕНЮ\n"
        f"╙───────────────────────╜\n\n"
        f"╭ 🍃 <b>{name}</b> · {region_display}\n"
        f"┆\n"
        f"├ 📊 Статус: {rep_title}\n"
        f"┆\n"
        f"╰ ⏳ В Тейвате: <b>{days}</b> дн."
    )
    final_text = format_text(await get_local_setting("text_menu", chat_id, text), user, DIV)
    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    await edit_or_send(query, final_text, main_menu_kb(query.from_user.id),
                       image_url=await get_section_image("menu", fallback, chat_id))


@dp.callback_query(MenuCB.filter(F.action == "profile"))
@inject_user
async def cb_profile(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    if user.get("char_change_paid") == 1:
        return await edit_or_send(query, f"🌸 ВЫБОР ПЕРСОНАЖА\n{DIV}\n\nТы оплатил смену!\nВыбери регион:",
                                  regions_kb(query.from_user.id))

    name = esc(user_display_name(user))
    g = await get_guild(user["guild_id"]) if user["guild_id"] else None
    guild_line = f"🏰 {esc(g['name'])}" if g else "🏰 Без гильдии"
    partner_line = f"❤️ {esc(user['partner_name'])}" if user["partner_id"] else "❤️ Свободен(а)"
    resin = await update_resin(query.from_user.id, chat_id)

    # --- ИСПРАВЛЕННЫЙ КОД: Ранг для профиля ---
    rep = user["reputation"] or 0
    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title:
        reg_name_for_title = reg_name_for_title.split(" ", 1)[1]
    rep_title = get_reputation_title(rep, reg_name_for_title)
    # ------------------------------------

    text = (
        f"╓───────────────────────╖\n"
        f"   🎴 ПРОФИЛЬ\n"
        f"╙───────────────────────╜\n\n"
        f"🍃 {name}\n\n"
        f"╭ 💰 Баланс: <b>{user['balance']}</b>\n"
        f"┆\n"
        f"├ 💎 Примогемы: <b>{user.get('primogems', 0)}</b>\n"
        f"┆\n"
        f"├ 💧 Смола: <b>{resin} / {RESIN_MAX}</b>\n"
        f"┆\n"
        f"├ 🎖️ Репутация: <b>{rep_title}</b>\n"
        f"┆\n"
        f"├ {partner_line}\n"
        f"┆\n"
        f"╰ {guild_line}"
    )
    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    await edit_or_send(query, text, profile_kb(query.from_user.id),
                       image_url=await get_section_image("profile", fallback, chat_id))


@dp.callback_query(MenuCB.filter(F.action == "freerole"))
@inject_user
async def cb_freerole(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id or not user["character_name"]: return
    old = user["character_name"]
    await update_user(query.from_user.id, chat_id, character_name="")
    await query.answer(f"⚠️ Роль «{old}» освобождена. Вернуть можно за {PRICE_ROLE_CHANGE} монет.", show_alert=True)
    if chat_id: await update_chat_list(chat_id)
    await cb_profile(query, MenuCB(action="profile", owner_id=query.from_user.id), user, chat_id)


@dp.callback_query(MenuCB.filter(F.action == "adventurers"))
@inject_user
async def cb_adventurers(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    text = f"╓───────────────────────╖\n   🏛 ГИЛЬДИЯ ИСКАТЕЛЕЙ\n╙───────────────────────╜\n\n🍃 Добро пожаловать, <b>{esc(user_display_name(user))}</b>!\n\n╞═══════════════════════╡\n\nВыбери направление:"
    await edit_or_send(query, text, adventurers_kb(query.from_user.id),
                       image_url=await get_section_image("adventurers", chat_id=chat_id))


@dp.callback_query(MenuCB.filter(F.action == "reputation"))
@inject_user
async def cb_reputation(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    rep = user["reputation"] or 0
    level, cur, need = get_rep_progress(rep)

    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title:
        reg_name_for_title = reg_name_for_title.split(" ", 1)[1]

    title = get_reputation_title(rep, reg_name_for_title)
    pt = "Максимум!" if level >= 10 else f"{'█' * (cur * 10 // 500)}{'░' * (10 - (cur * 10 // 500))} {cur}/500"

    text = (
        f"╓───────────────────────╖\n"
        f"   🎖️ РЕПУТАЦИЯ\n"
        f"╙───────────────────────╜\n\n"
        f"{title}\n\n"
        f"╭ 📊 Уровень: <b>{level} / 10</b>\n"
        f"┆\n"
        f"├ 🌟 Очки: <b>{rep}</b>\n"
        f"┆\n"
        f"╰ 📈 Прогресс: {pt}"
    )
    await edit_or_send(query, text, reputation_kb(query.from_user.id),
                       image_url=await get_section_image("reputation", chat_id=chat_id))


@dp.message(Command("freerole"))
async def cmd_freerole(message):
    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)
    if not user["character_name"]: return await message.answer("У тебя нет персонажа.")
    old = user["character_name"]
    await update_user(message.from_user.id, chat_id, character_name="")
    await message.answer(f"✅ Роль «{esc(old)}» освобождена.\n\n⚠️ Вернуть можно за {PRICE_ROLE_CHANGE} монет.",
                         parse_mode="HTML", reply_markup=back_kb(message.from_user.id))
    await update_chat_list(chat_id)