from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder  # <--- ДОБАВЛЕНО ДЛЯ КНОПОК

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
        return await edit_or_send(query, f"── 〔 🖼 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nТы оплатил смену!\nВыбери регион:",
                                  regions_kb(query.from_user.id), image_url="")

    name = esc(user_display_name(user))
    first_seen = user.get("first_seen") or int(datetime.now(timezone.utc).timestamp())
    days = (int(datetime.now(timezone.utc).timestamp()) - first_seen) // 86400 + 1

    region_display = "Тейват"
    if user.get("character_name"):
        from helpers import get_character_region
        r_key = get_character_region(user["character_name"])
        if r_key and r_key in REGIONS and r_key != "other":
            region_display = REGIONS[r_key].split(" ", 1)[1] if " " in REGIONS[r_key] else REGIONS[r_key]

    rep = user.get("reputation", 0) or 0
    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title: reg_name_for_title = reg_name_for_title.split(" ", 1)[1]
    rep_title = get_reputation_title(rep, reg_name_for_title)

    text = (
        f" ─ [ 🖼 ГЛАВНОЕ МЕНЮ ] ─\n\n"
        f"🍃 <b>{name}</b> · {region_display}\n\n"
        f"📊 Статус: {rep_title}\n\n"
        f"⏳ В Тейвате: <b>{days}</b> дн."
    )
    final_text = format_text(await get_local_setting("text_menu", chat_id, text), user, DIV)

    # ВОЗВРАЩЕНО: подстановка картинки персонажа, если нет кастомной
    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    image = await get_section_image("menu", fallback, chat_id)
    await edit_or_send(query, final_text, main_menu_kb(query.from_user.id), image_url=image)


@dp.callback_query(MenuCB.filter(F.action == "profile"))
@inject_user
async def cb_profile(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    if user.get("char_change_paid") == 1:
        return await edit_or_send(query, f"── 〔 🖼 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nТы оплатил смену!\nВыбери регион:",
                                  regions_kb(query.from_user.id), image_url="")

    name = esc(user_display_name(user))
    g = await get_guild(user["guild_id"]) if user["guild_id"] else None
    guild_line = f"🏰 {esc(g['name'])}" if g else "Без гильдии"

    if user["partner_id"]:
        partner_line = f"❤️ {esc(user['partner_name'])}"
    else:
        partner_line = "❤️ Свободен(а)"

    resin = await update_resin(query.from_user.id, chat_id)
    rep = user["reputation"] or 0
    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title: reg_name_for_title = reg_name_for_title.split(" ", 1)[1]
    rep_title = get_reputation_title(rep, reg_name_for_title)

    text = (
        f"─ [ 🖼 ПРОФИЛЬ ] ─\n\n"
        f"🍃 {name}\n\n"
        f"💰 Баланс: <b>{user['balance']}</b>\n\n"
        f"💧 Смола: <b>{resin} / {RESIN_MAX}</b>\n\n"
        f"🎖️ Репутация: <b>{rep_title}</b>\n\n"
        f"{partner_line}\n\n"
        f"{guild_line}"
    )

    # ВОЗВРАЩЕНО: подстановка картинки персонажа, если нет кастомной
    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    image = await get_section_image("profile", fallback, chat_id)
    await edit_or_send(query, text, profile_kb(query.from_user.id), image_url=image)


# ==================== ОСВОБОЖДЕНИЕ РОЛИ (КНОПКА) ====================

@dp.callback_query(MenuCB.filter(F.action == "freerole"))
@inject_user
async def cb_freerole(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id or not user["character_name"]: return

    old = esc(user["character_name"])
    text = (
        f"─ [ ⚠️ ОСВОБОЖДЕНИЕ РОЛИ ] ─\n\n"
        f"Ты действительно хочешь освободить роль <b>{old}</b>?\n\n"
        f"⚠️ Вернуть её обратно можно будет только за <b>{PRICE_ROLE_CHANGE}</b> монет."
    )

    b = InlineKeyboardBuilder()
    b.button(text="⊱ ✅ Да, освободить ⊰", callback_data=MenuCB(action="freerole_confirm", owner_id=query.from_user.id))
    b.button(text="⊱ ❌ Отмена ⊰", callback_data=MenuCB(action="freerole_cancel", owner_id=query.from_user.id))
    b.adjust(1)

    await edit_or_send(query, text, b.as_markup(), image_url="")


@dp.callback_query(MenuCB.filter(F.action == "freerole_confirm"))
@inject_user
async def cb_freerole_confirm(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id or not user["character_name"]: return

    old = user["character_name"]
    await update_user(query.from_user.id, chat_id, character_name="", char_change_paid=0, search_rp_partner="")
    await query.answer(f"⚠️ Роль «{esc(old)}» освобождена. Вернуть можно за {PRICE_ROLE_CHANGE} монет.",
                       show_alert=True)

    if chat_id:
        await update_chat_list(chat_id)

    # Получаем СВЕЖИЕ данные пользователя из БД и передаем их
    updated_user = await get_user(query.from_user.id, chat_id)
    await cb_profile(query, MenuCB(action="profile", owner_id=query.from_user.id), user=updated_user, chat_id=chat_id)


@dp.callback_query(MenuCB.filter(F.action == "freerole_cancel"))
@inject_user
async def cb_freerole_cancel(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    await query.answer("Отменено.")
    # Передаем данные, которые уже есть
    await cb_profile(query, MenuCB(action="profile", owner_id=query.from_user.id), user=user, chat_id=chat_id)
# ==================== ОСВОБОЖДЕНИЕ РОЛИ (КОМАНДА) ====================

@dp.message(Command("freerole"))
async def cmd_freerole(message):
    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)
    if not user["character_name"]:
        return await message.answer("У тебя нет персонажа.")

    old = esc(user["character_name"])
    text = (
        f"─ [ ⚠️ ОСВОБОЖДЕНИЕ РОЛИ ] ─\n\n"
        f"Ты действительно хочешь освободить роль <b>{old}</b>?\n\n"
        f"⚠️ Вернуть её обратно можно будет только за <b>{PRICE_ROLE_CHANGE}</b> монет."
    )

    b = InlineKeyboardBuilder()
    b.button(text="⊱ ✅ Да, освободить ⊰",
             callback_data=MenuCB(action="freerole_confirm", owner_id=message.from_user.id))
    b.button(text="⊱ ❌ Отмена ⊰", callback_data=MenuCB(action="freerole_cancel", owner_id=message.from_user.id))
    b.adjust(1)

    await message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")


# ==================== ОСТАЛЬНЫЕ МЕНЮ ====================

@dp.callback_query(MenuCB.filter(F.action == "adventurers"))
@inject_user
async def cb_adventurers(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    text = (
        f"─ [ 🏛 ГИЛЬДИЯ ИСКАТЕЛЕЙ ] ─\n\n"
        f"🍃 Добро пожаловать,\n"
        f"<b>{esc(user_display_name(user))}</b>!\n\n"
        f"Выбери направление:"
    )
    image = await get_section_image("adventurers", chat_id=chat_id)
    await edit_or_send(query, text, adventurers_kb(query.from_user.id), image_url=image)


@dp.callback_query(MenuCB.filter(F.action == "reputation"))
@inject_user
async def cb_reputation(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    rep = user["reputation"] or 0
    level, cur, need = get_rep_progress(rep)

    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title: reg_name_for_title = reg_name_for_title.split(" ", 1)[1]

    title = get_reputation_title(rep, reg_name_for_title)
    pt = "Максимум!" if level >= 10 else f"{'█' * (cur * 10 // 500)}{'░' * (10 - (cur * 10 // 500))} {cur}/500"

    text = (
        f"─ [ 🎖️ РЕПУТАЦИЯ ] ─\n\n"
        f"{title}\n\n"
        f"📊 Уровень: <b>{level} / 10</b>\n\n"
        f"🌟 Очки: <b>{rep}</b>\n\n"
        f"📈 Прогресс: {pt}"
    )
    image = await get_section_image("reputation", chat_id=chat_id)
    await edit_or_send(query, text, reputation_kb(query.from_user.id), image_url=image)