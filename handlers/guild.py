from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
import random

from bot_instance import bot, dp
from callbacks import MenuCB, GuildCB, GuildInviteCB
from config import DB_PATH
from constants import DIV, GUILD_CREATE_PRICE, REP_PER_GUILD_CREATE, REP_PER_DONATE_UNIT, REP_PER_DONATE_MAX, \
    ARTIFACT_SLOTS, RARITY_BONUS, SLOT_SHORT
from db import (
    get_user, update_user, get_guild, get_guild_by_name, create_guild,
    update_guild, get_all_guilds, get_guild_members, get_setting, get_local_setting,
    add_artifact, update_primogems, get_guild_craft_stats
)
from helpers import (
    esc, user_display_name, edit_or_send, _ensure_user, _gain_rep,
    get_section_image, inject_user, extract_target, resolve_user_id
)
from keyboards import (
    guild_menu_kb, guild_list_kb, back_kb, guild_manage_kb, guild_shop_kb,
    guild_craft_kb, guild_members_kb, guild_member_manage_kb
)


class GuildEdit(StatesGroup):
    waiting_for_desc = State()
    waiting_for_photo = State()


@dp.callback_query(MenuCB.filter(F.action == "guild"))
@inject_user
async def cb_guild(query: types.CallbackQuery, callback_data: MenuCB, user: dict, chat_id: int, state: FSMContext):
    await state.clear()
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    has = bool(user["guild_id"])
    is_owner = False

    if has:
        g = await get_guild(user["guild_id"])
        if g and g["owner_id"] == query.from_user.id:
            is_owner = True

        title_line = "\n🔥 НЕПОКОРНЫЕ 🔥" if g.get("is_unbroken") else ""
        desc_text = f"\n\n📜 Описание: {esc(g['description'])}" if g and g.get('description') else ""
        members = await get_guild_members(g['guild_id'])
        members_count = len(members)
        max_slots = g.get('max_members', 5)

        default_text = (
            f"— [ 🏰 ГИЛЬДИЯ ] —\n\n"
            f"🛡 <b>{esc(g['name']).upper()}</b>{title_line}\n\n"
            f"👑 Ранг: <b>{esc(user['guild_rank'])}</b>\n"
            f"💰 Личный вклад: <b>{user['guild_contribution']}</b>\n"
            f"💰 Казна: <b>{g['treasury']}</b>\n"
            f"📊 Уровень: <b>{g.get('level', 1)}</b>\n"
            f"👥 Слоты: <b>{members_count} / {max_slots}</b>{desc_text}"
        )
        raw_text = await get_local_setting("text_guild", chat_id, default_text)
        text = raw_text.replace("{name}", esc(user_display_name(user))).replace("{div}", DIV)
        img = g.get("image_url") if g and g.get("image_url") else await get_local_setting("image_guild", chat_id)
    else:
        default_text = (
            f"— [ 🏰 ГИЛЬДИИ ] —\n\n"
            f"🍃 {esc(user_display_name(user))}, ты пока без гильдии.\n\n"
            f"Создай за {GUILD_CREATE_PRICE} монет или вступи в существующую.\n\n"
            f"🎖️ За создание: +{REP_PER_GUILD_CREATE} репутации"
        )
        raw_text = await get_local_setting("text_guild", chat_id, default_text)
        text = raw_text.replace("{name}", esc(user_display_name(user))).replace("{div}", DIV)
        img = await get_local_setting("image_guild", chat_id)

    await edit_or_send(query, text, guild_menu_kb(query.from_user.id, has, is_owner), image_url=img or "")


async def render_guild_manage(query: types.CallbackQuery, user: dict, chat_id: int):
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id:
        await query.answer("❌ Только лидер.", show_alert=True)
        return
    text = (
        f"— [ ⚙️ УПРАВЛЕНИЕ ] —\n\n"
        f"🛡 <b>{esc(g['name'])}</b>\n\n"
        f"💡 /disbandguild — распустить\n"
        f"💡 /donate Сумма — пополнить казну\n"
        f"💡 /transfer_ally Сумма — передать союзу"
    )
    img = await get_local_setting("image_guild_manage", chat_id)
    await edit_or_send(query, text, guild_manage_kb(query.from_user.id), image_url=img or "")


@dp.callback_query(GuildCB.filter(F.action == "manage"))
@inject_user
async def cb_guild_manage(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int,
                          state: FSMContext):
    await state.clear()
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    await render_guild_manage(query, user, chat_id)


@dp.callback_query(F.data == "guild_manage_back")
@inject_user
async def cb_guild_manage_back(query: types.CallbackQuery, user: dict, chat_id: int, state: FSMContext):
    await state.clear()
    await render_guild_manage(query, user, chat_id)


async def render_guild_members(query: types.CallbackQuery, user: dict, chat_id: int):
    g = await get_guild(user["guild_id"])
    members = await get_guild_members(user["guild_id"])
    is_owner = g and g["owner_id"] == query.from_user.id
    text = f"— [ 👥 СОСТАВ ГИЛЬДИИ ] —\n\nНажми на участника, чтобы управлять им:\n\nВсего: {len(members)} чел."
    img = await get_local_setting("image_guild_members", chat_id)
    await edit_or_send(query, text, guild_members_kb(query.from_user.id, members, is_owner), image_url=img or "")


@dp.callback_query(GuildCB.filter(F.action == "members"))
@inject_user
async def cb_guild_members(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    await render_guild_members(query, user, chat_id)


@dp.callback_query(F.data == "gmem_back")
@inject_user
async def cb_gmem_back(query: types.CallbackQuery, user: dict, chat_id: int):
    await render_guild_members(query, user, chat_id)


async def render_gmem_view(query: types.CallbackQuery, user: dict, chat_id: int, target_id: int):
    g = await get_guild(user["guild_id"])
    target = await get_user(target_id, chat_id)
    if not target or target["guild_id"] != g["guild_id"]:
        await query.answer("❌ Участник не найден.", show_alert=True)
        return
    is_owner = g["owner_id"] == query.from_user.id
    text = (
        f"— [ 👤 УЧАСТНИК ] —\n\n"
        f"🎭 <b>{esc(target['character_name'])}</b>\n\n"
        f"👑 Ранг: <b>{esc(target['guild_rank'])}</b>\n"
        f"💰 Вклад: <b>{target['guild_contribution']}</b>"
    )
    await edit_or_send(query, text,
                       guild_member_manage_kb(query.from_user.id, target_id, is_owner, target['guild_rank']),
                       image_url="")


@dp.callback_query(F.data.startswith("gmem_view_"))
@inject_user
async def cb_gmem_view(query: types.CallbackQuery, user: dict, chat_id: int):
    target_id = int(query.data.replace("gmem_view_", ""))
    await render_gmem_view(query, user, chat_id, target_id)


@dp.callback_query(F.data.startswith("gmem_kick_"))
@inject_user
async def cb_gmem_kick(query: types.CallbackQuery, user: dict, chat_id: int):
    target_id = int(query.data.replace("gmem_kick_", ""))
    g = await get_guild(user["guild_id"])
    if g["owner_id"] != query.from_user.id:
        await query.answer("❌ Только лидер.", show_alert=True)
        return
    target = await get_user(target_id, chat_id)
    if target['guild_rank'] == "Лидер":
        await query.answer("❌ Нельзя кикнуть лидера.", show_alert=True)
        return
    await update_user(target_id, chat_id, guild_id=0, guild_rank="Участник", guild_contribution=0)
    await query.answer(f"✅ {target['character_name']} исключен из гильдии.", show_alert=True)
    await render_guild_members(query, user, chat_id)


@dp.callback_query(F.data.startswith("gmem_promote_"))
@inject_user
async def cb_gmem_promote(query: types.CallbackQuery, user: dict, chat_id: int):
    target_id = int(query.data.replace("gmem_promote_", ""))
    g = await get_guild(user["guild_id"])
    if g["owner_id"] != query.from_user.id: return
    await update_user(target_id, chat_id, guild_rank="Офицер")
    await query.answer("✅ Назначен офицером!", show_alert=True)
    await render_gmem_view(query, user, chat_id, target_id)


@dp.callback_query(F.data.startswith("gmem_demote_"))
@inject_user
async def cb_gmem_demote(query: types.CallbackQuery, user: dict, chat_id: int):
    target_id = int(query.data.replace("gmem_demote_", ""))
    g = await get_guild(user["guild_id"])
    if g["owner_id"] != query.from_user.id: return
    await update_user(target_id, chat_id, guild_rank="Участник")
    await query.answer("✅ Снят с должности.", show_alert=True)
    await render_gmem_view(query, user, chat_id, target_id)


async def render_guild_craft(query: types.CallbackQuery, user: dict, chat_id: int):
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id: return
    stats = await get_guild_craft_stats(g["guild_id"])
    members = await get_guild_members(g["guild_id"])
    count = max(5, len(members))
    req_m = count * 400
    req_s = count * 40
    req_r = count * 200
    req_p = count * 2
    req_b = count * 1
    text = (
        f"— [ ⚒ КРАФТ БАФФОВ ] —\n\n"
        f"Скрафти награду для всех участников (сгорает через 14 дней).\n\n"
        f"💬 Сообщения: {stats['m']} / {req_m}\n"
        f"🎭 Стикеры: {stats['s']} / {req_s}\n"
        f"↩️ Ответы: {stats['r']} / {req_r}\n"
        f"🖼 Фото: {stats['p']} / {req_p}\n"
        f"🐉 Убито боссов: {stats['b']} / {req_b}\n\n"
        f"🎁 Награда: Баффы на 14 дней + 500-1000 монет в казну + 50-100 💎\n"
        f"<i>(Любой 1 участник может нафармить это сам)</i>"
    )
    can = stats['m'] >= req_m and stats['s'] >= req_s and stats['r'] >= req_r and stats['p'] >= req_p and stats[
        'b'] >= req_b
    if not can: text += "\n\n❌ Недостаточно ресурсов."
    b = InlineKeyboardBuilder()
    if can:
        b.button(text="⊱ 🎭 Скрафтить Смену ⊰", callback_data="gcraft_do_char")
        b.button(text="⊱ 😴 Скрафтить Рест ⊰", callback_data="gcraft_do_rest")
        b.button(text="⊱ 🧹 Скрафтить Чистку ⊰", callback_data="gcraft_do_clean")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="guild_manage_back")
    b.adjust(1)
    img = await get_local_setting("image_guild_craft", chat_id)
    await edit_or_send(query, text, b.as_markup(), image_url=img or "")


@dp.callback_query(F.data == "guild_craft")
@inject_user
async def cb_guild_craft(query: types.CallbackQuery, user: dict, chat_id: int, state: FSMContext):
    await state.clear()
    await render_guild_craft(query, user, chat_id)


async def do_guild_craft(query: types.CallbackQuery, item_type: str, user: dict, chat_id: int):
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id: return
    stats = await get_guild_craft_stats(g["guild_id"])
    members = await get_guild_members(g["guild_id"])
    count = max(5, len(members))
    req_m = count * 400
    req_s = count * 40
    req_r = count * 200
    req_p = count * 2
    req_b = count * 1
    if stats['m'] < req_m or stats['s'] < req_s or stats['r'] < req_r or stats['p'] < req_p or stats['b'] < req_b:
        await query.answer("❌ Недостаточно ресурсов.", show_alert=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guild_member_stats SET msgs=0, stickers=0, replies=0, photos=0, bosses=0 WHERE guild_id = ?",
            (g["guild_id"],))
        await db.commit()
    expires = int(datetime.now(timezone.utc).timestamp()) + (14 * 86400)
    for m in members:
        if item_type == "char":
            await update_user(m["user_id"], chat_id, guild_char_exp=expires)
        elif item_type == "rest":
            await update_user(m["user_id"], chat_id, guild_rest_exp=expires)
        elif item_type == "clean":
            await update_user(m["user_id"], chat_id, guild_clean_exp=expires)
    reward_coins = random.randint(500, 1000)
    reward_primo = random.randint(50, 100)
    await update_guild(g["guild_id"], treasury=g["treasury"] + reward_coins)
    await update_primogems(query.from_user.id, chat_id, reward_primo)
    await query.answer(f"✅ Бафф выдан всем! В казну: +{reward_coins} монет. Вам: +{reward_primo} 💎", show_alert=True)
    await render_guild_craft(query, user, chat_id)


@dp.callback_query(F.data == "gcraft_do_char")
@inject_user
async def cb_craft_char(query: types.CallbackQuery, user: dict, chat_id: int):
    await do_guild_craft(query, "char", user, chat_id)


@dp.callback_query(F.data == "gcraft_do_rest")
@inject_user
async def cb_craft_rest(query: types.CallbackQuery, user: dict, chat_id: int):
    await do_guild_craft(query, "rest", user, chat_id)


@dp.callback_query(F.data == "gcraft_do_clean")
@inject_user
async def cb_craft_clean(query: types.CallbackQuery, user: dict, chat_id: int):
    await do_guild_craft(query, "clean", user, chat_id)


@dp.callback_query(F.data == "guild_shop")
@inject_user
async def cb_guild_shop(query: types.CallbackQuery, user: dict, chat_id: int, state: FSMContext):
    await state.clear()
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id:
        return await query.answer("❌ Только лидер.", show_alert=True)
    text = f"— [ 🛒 МАГАЗИН ГИЛЬДИИ ] —\n\n💰 Казна: {g['treasury']}\n\nВыбери товар:"
    img = await get_local_setting("image_guild_shop", chat_id)
    await edit_or_send(query, text, guild_shop_kb(query.from_user.id), image_url=img or "")


@dp.callback_query(F.data.startswith("gshop_buy_"))
@inject_user
async def cb_guild_shop_buy(query: types.CallbackQuery, user: dict, chat_id: int):
    action = query.data.replace("gshop_buy_", "")
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id:
        return await query.answer("❌ Только лидер.", show_alert=True)

    if action == "slots":
        cost = 5000
        if g["treasury"] < cost:
            return await query.answer("❌ Недостаточно монет в казне.", show_alert=True)

        current_bonus = g.get('bonus_slots', 0) or 0
        if current_bonus >= 5:
            return await query.answer("❌ Вы уже купили максимум дополнительных слотов (+5). Повышайте уровень гильдии!",
                                      show_alert=True)

        await update_guild(g["guild_id"], treasury=g["treasury"] - cost, bonus_slots=current_bonus + 5)
        await query.answer("✅ Куплено +5 слотов!", show_alert=True)

    elif action == "chest":
        cost = 3000
        if g["treasury"] < cost: return await query.answer("❌ Недостаточно монет в казне.", show_alert=True)
        await update_guild(g["guild_id"], treasury=g["treasury"] - cost)
        slot = random.choice(list(ARTIFACT_SLOTS.keys()))
        rarity = 5
        bonus_type = ARTIFACT_SLOTS[slot]["bonus_type"]
        bonus_value = RARITY_BONUS[rarity]
        name = f"{SLOT_SHORT.get(slot, slot)} [Гильдейский сундук] (5★)"
        art_id = await add_artifact(query.from_user.id, chat_id, slot, rarity, bonus_type, bonus_value, name)
        await query.answer("✅ Вы получили 5★ артефакт!", show_alert=True)
    elif action == "primo":
        cost = 10000
        if g["treasury"] < cost: return await query.answer("❌ Недостаточно монет в казне.", show_alert=True)
        await update_guild(g["guild_id"], treasury=g["treasury"] - cost)
        await update_primogems(query.from_user.id, chat_id, 160)
        await query.answer("✅ Куплено 160 примогемов!", show_alert=True)

    g = await get_guild(user["guild_id"])
    text = f"— [ 🛒 МАГАЗИН ГИЛЬДИИ ] —\n\n💰 Казна: {g['treasury']}\n\nВыбери товар:"
    img = await get_local_setting("image_guild_shop", chat_id)
    await edit_or_send(query, text, guild_shop_kb(query.from_user.id), image_url=img or "")


@dp.callback_query(F.data == "guild_edit_desc")
@inject_user
async def cb_guild_edit_desc(query: types.CallbackQuery, state: FSMContext, user: dict, chat_id: int):
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id: return
    await state.set_state(GuildEdit.waiting_for_desc)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="guild_manage_back")
    await edit_or_send(query, f"— [ 📝 ОПИСАНИЕ ] —\n\nОтправь новый текст описания (до 300 символов):",
                       b.as_markup(), image_url="")


@dp.message(GuildEdit.waiting_for_desc, F.text)
async def process_guild_desc(message: types.Message, state: FSMContext):
    desc = message.text.strip()[:300]
    user = await get_user(message.from_user.id, message.chat.id)
    g = await get_guild(user["guild_id"])
    if g and g["owner_id"] == message.from_user.id:
        await update_guild(g["guild_id"], description=desc)
        await message.answer("✅ Описание гильдии успешно обновлено!")
        b = InlineKeyboardBuilder()
        b.button(text="⊱ ‹ В управление ⊰", callback_data="guild_manage_back")
        await message.answer("Нажми кнопку ниже, чтобы вернуться.", reply_markup=b.as_markup())
    await state.clear()


@dp.callback_query(F.data == "guild_edit_photo")
@inject_user
async def cb_guild_edit_photo(query: types.CallbackQuery, state: FSMContext, user: dict, chat_id: int):
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != query.from_user.id: return
    await state.set_state(GuildEdit.waiting_for_photo)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="guild_manage_back")
    await edit_or_send(query,
                       f"— [ 🖼 ФОТО ГИЛЬДИИ ] —\n\nОтправь мне фотографию, которая будет гербом твоей гильдии.",
                       b.as_markup(), image_url="")


@dp.message(GuildEdit.waiting_for_photo, F.photo)
async def process_guild_photo(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id, message.chat.id)
    g = await get_guild(user["guild_id"])
    if g and g["owner_id"] == message.from_user.id:
        file_id = message.photo[-1].file_id
        await update_guild(g["guild_id"], image_url=file_id)
        await message.answer("✅ Фото гильдии успешно обновлено!")
        b = InlineKeyboardBuilder()
        b.button(text="⊱ ‹ В управление ⊰", callback_data="guild_manage_back")
        await message.answer("Нажми кнопку ниже, чтобы вернуться.", reply_markup=b.as_markup())
    await state.clear()


@dp.callback_query(GuildCB.filter(F.action == "create"))
@inject_user
async def cb_guild_create(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    if user["guild_id"]:
        await query.answer("❌ Ты уже в гильдии!", show_alert=True)
        return
    if user["balance"] < GUILD_CREATE_PRICE:
        await query.answer(f"❌ Нужно {GUILD_CREATE_PRICE}", show_alert=True)
        return
    if not user.get("guild_bonus_claimed"):
        rep_info = f"\n🎖️ Бонус: +{REP_PER_GUILD_CREATE} репутации"
    else:
        rep_info = "\n🎖️ Бонус за создание уже был получен"
    text = f"— [ 💰 СОЗДАНИЕ ГИЛЬДИИ ] —\n\nСтоимость: {GUILD_CREATE_PRICE} монет{rep_info}\n\nНапиши:\n/createguild Название"
    img = await get_local_setting("image_guild_create", chat_id)
    await edit_or_send(query, text, back_kb(query.from_user.id), image_url=img or "")


@dp.callback_query(GuildCB.filter(F.action == "list"))
@inject_user
async def cb_guild_list(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    guilds = await get_all_guilds(chat_id)
    if not guilds:
        text = f"— [ 📜 СПИСОК ГИЛЬДИЙ ] —\n\nПока нет гильдий."
    else:
        text = f"— [ 📜 СПИСОК ГИЛЬДИЙ ] —\n\nТоп по уровню и казне:\n\nВсего: {len(guilds)}"
    img = await get_local_setting("image_guild_list", chat_id)
    await edit_or_send(query, text, guild_list_kb(query.from_user.id, guilds), image_url=img or "")


@dp.callback_query(GuildCB.filter(F.action == "join"))
@inject_user
async def cb_guild_join(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    if user["guild_id"]:
        await query.answer("❌ Ты уже в гильдии!", show_alert=True)
        return
    g = await get_guild(callback_data.guild_id)
    if not g:
        await query.answer("❌ Не найдено", show_alert=True)
        return
    members = await get_guild_members(g["guild_id"])
    if len(members) >= g.get("max_members", 5):
        await query.answer("❌ В гильдии нет свободных мест!", show_alert=True)
        return
    await update_user(query.from_user.id, chat_id, guild_id=g["guild_id"], guild_rank="Участник", guild_contribution=0)
    text = f"— [ 🎉 ДОБРО ПОЖАЛОВАТЬ! ] —\n\nТы вступил(а) в\n\n«{esc(g['name'])}»!"
    await edit_or_send(query, text, back_kb(query.from_user.id), image_url="")


@dp.callback_query(GuildCB.filter(F.action == "info"))
@inject_user
async def cb_guild_info(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id: return
    if not user["guild_id"]:
        return await query.answer("❌ Ты не в гильдии.", show_alert=True)

    g = await get_guild(user["guild_id"])
    if not g:
        return await query.answer("❌ Не найдено", show_alert=True)

    members = await get_guild_members(g["guild_id"])
    created = datetime.fromtimestamp(g["created_at"], timezone.utc).strftime("%d.%m.%Y")

    text = (
        f"— [ 🏰 ГИЛЬДИЯ «{esc(g['name']).upper()}» ] —\n\n"
        f"👑 Лидер: {esc(g['owner_name'])}\n"
        f"📅 Создана: {created}\n\n"
        f"📜 <b>Описание:</b>\n"
        f"<i>{esc(g.get('description') or 'Пока нет описания...')}</i>\n\n"
        f"📊 Уровень: <b>{g.get('level', 1)}</b>\n"
        f"👥 Участники: <b>{len(members)} / {g.get('max_members', 5)}</b>\n"
        f"💰 Казна: <b>{g['treasury']}</b> монет\n"
        f"🏆 Очки недели: <b>{g.get('week_points', 0)}</b>"
    )

    img = g.get("image_url") if g and g.get("image_url") else await get_local_setting("image_guild", chat_id)

    await edit_or_send(query, text, guild_menu_kb(query.from_user.id, True, g["owner_id"] == query.from_user.id),
                       image_url=img or "")


@dp.callback_query(GuildCB.filter(F.action == "treasury"))
@inject_user
async def cb_guild_treasury(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id: return
    if not user["guild_id"]: return await query.answer("❌ Ты не в гильдии.", show_alert=True)
    g = await get_guild(user["guild_id"])
    text = (
        f"— [ 💰 КАЗНА ГИЛЬДИИ ] —\n\n"
        f"«{esc(g['name'])}»\n\n"
        f"В казне: <b>{g['treasury']}</b> монет\n\n"
        f"Пополнить:\n"
        f"/donate Сумма\n\n"
        f"🎖️ За каждые {REP_PER_DONATE_UNIT} монет: +1 репутации"
    )
    b = InlineKeyboardBuilder()
    b.button(text="⊱ ‹ Назад ⊰", callback_data=MenuCB(action="guild", owner_id=query.from_user.id))
    await edit_or_send(query, text, b.as_markup(), image_url="")


@dp.callback_query(GuildCB.filter(F.action == "leave"))
@inject_user
async def cb_guild_leave(query: types.CallbackQuery, callback_data: GuildCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id: return
    if not user["guild_id"]: return await query.answer("❌ Не в гильдии.", show_alert=True)
    g = await get_guild(user["guild_id"])
    if g and g["owner_id"] == query.from_user.id:
        return await query.answer("❌ Владелец не может выйти. Используй /disbandguild", show_alert=True)
    await update_user(query.from_user.id, chat_id, guild_id=0, guild_rank="Участник", guild_contribution=0)
    text = f"— [ 👋 ПОКА! ] —\n\nТы вышел(ла) из гильдии."
    await edit_or_send(query, text, back_kb(query.from_user.id), image_url="")


@dp.callback_query(F.data == "guild_top")
@inject_user
async def cb_guild_top(query: types.CallbackQuery, user: dict, chat_id: int):
    guilds = await get_all_guilds(chat_id, 10)
    if not guilds: return await query.answer("Пока нет гильдий.", show_alert=True)
    text = f"— [ 🏆 ТОП ГИЛЬДИЙ ] —\n\n"
    for i, g in enumerate(guilds, 1):
        medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
        title = " 🔥НЕПОКОРНЫЕ🔥" if g.get("is_unbroken") else ""
        text += f"{medal} {esc(g['name'])}{title}\n📊 Ур: {g.get('level', 1)} | 💰 Казна: {g['treasury']}\n👥 {g.get('members', 0)}/{g.get('max_members', 5)}\n\n"
    b = InlineKeyboardBuilder()
    b.button(text="⊱ ‹ Назад ⊰", callback_data=MenuCB(action="guild", owner_id=query.from_user.id))
    await edit_or_send(query, text.strip(), b.as_markup(), image_url="")


@dp.message(Command("transfer_ally"))
async def cmd_transfer_ally(message: types.Message):
    user = await _ensure_user(message.from_user.id, message.chat.id)
    if not user["guild_id"]: return await message.answer("❌ Ты не в гильдии.")
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != message.from_user.id: return await message.answer(
        "❌ Только лидер может передавать деньги.")
    ally_id = g.get("ally_id")
    if not ally_id: return await message.answer(
        "❌ У вашей гильдии нет союзника. Используйте /ally_create чтобы предложить союз.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit(): return await message.answer("Используй: /transfer_ally Сумма")
    amount = int(parts[1])
    if amount <= 0: return await message.answer("❌ Сумма > 0.")
    if g["treasury"] < amount: return await message.answer("❌ В казне недостаточно монет.")
    ally_g = await get_guild(ally_id)
    if not ally_g: return await message.answer("❌ Гильдия-союзник не найдена (возможно, распущена).")
    await update_guild(g["guild_id"], treasury=g["treasury"] - amount)
    await update_guild(ally_id, treasury=ally_g["treasury"] + amount)
    await message.answer(
        f"🤝 Ты передал {amount} монет из казны гильдии «{esc(g['name'])}» в казну союзной гильдии «{esc(ally_g['name'])}»!",
        reply_markup=back_kb(message.from_user.id))


@dp.message(Command("createguild"))
async def cmd_createguild(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type not in ("group", "supergroup"): return await message.answer("❌ Только в группе.")
    user = await _ensure_user(message.from_user.id, chat_id)
    if user["guild_id"]: return await message.answer("❌ Ты уже в гильдии.")
    if user["balance"] < GUILD_CREATE_PRICE: return await message.answer(f"❌ Нужно {GUILD_CREATE_PRICE} монет.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return await message.answer("Используй: /createguild Название")
    name = parts[1].strip()[:32]
    if await get_guild_by_name(name, chat_id): return await message.answer(f"❌ Гильдия «{esc(name)}» уже существует.")
    gid = await create_guild(name, message.from_user.id, user["character_name"] or "Игрок", chat_id)
    await update_user(message.from_user.id, chat_id, balance=user["balance"] - GUILD_CREATE_PRICE, guild_id=gid,
                      guild_rank="Лидер")
    if not user.get("guild_bonus_claimed"):
        await update_user(message.from_user.id, chat_id, guild_bonus_claimed=1)
        await _gain_rep(message.from_user.id, chat_id, REP_PER_GUILD_CREATE, message.from_user.first_name)
        rep_line = f"\n🎖️ +{REP_PER_GUILD_CREATE} репутации"
    else:
        rep_line = "\n🎖️ Бонус за создание уже получен ранее"
    await message.answer(
        f"— [ 🏰 ГИЛЬДИЯ СОЗДАНА! ] —\n\n«{esc(name)}»\nТы — Лидер.\n\n-{GUILD_CREATE_PRICE} монет{rep_line}\nУдачи!",
        reply_markup=back_kb(message.from_user.id))


@dp.message(Command("donate"))
async def cmd_donate(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type not in ("group", "supergroup"): return await message.answer("❌ Только в группе.")
    user = await _ensure_user(message.from_user.id, chat_id)
    if not user["guild_id"]: return await message.answer("❌ Ты не в гильдии.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit(): return await message.answer("Используй: /donate Сумма")
    amount = int(parts[1])
    if amount <= 0: return await message.answer("❌ Сумма > 0.")
    if user["balance"] < amount: return await message.answer("❌ Не хватает.")
    g = await get_guild(user["guild_id"])
    await update_user(message.from_user.id, chat_id, balance=user["balance"] - amount,
                      guild_contribution=user["guild_contribution"] + amount)
    await update_guild(g["guild_id"], treasury=g["treasury"] + amount)
    rep_gain = min(REP_PER_DONATE_MAX, (amount // REP_PER_DONATE_UNIT))
    if rep_gain > 0: await _gain_rep(message.from_user.id, chat_id, rep_gain, message.from_user.first_name)
    await message.answer(f"💛 Ты внёс(ла) {amount} монет.\n🎖️ Репутация: +{rep_gain}",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("disbandguild"))
async def cmd_disbandguild(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type not in ("group", "supergroup"): return await message.answer("❌ Только в группе.")
    user = await _ensure_user(message.from_user.id, chat_id)
    if not user["guild_id"]: return await message.answer("❌ Ты не в гильдии.")
    g = await get_guild(user["guild_id"])
    if not g or g["owner_id"] != message.from_user.id: return await message.answer("❌ Только лидер.")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET guild_id = 0, guild_rank = 'Участник', guild_contribution = 0 WHERE guild_id = ? AND chat_id = ?",
            (g["guild_id"], chat_id))
        await db.execute("DELETE FROM guilds WHERE guild_id = ?", (g["guild_id"],))
        await db.execute("DELETE FROM guild_member_stats WHERE guild_id = ?", (g["guild_id"],))
        await db.commit()
    await message.answer(f"🏰 Гильдия «{esc(g['name'])}» распущена.", reply_markup=back_kb(message.from_user.id))


# ==================== НОВАЯ СИСТЕМА ПРИГЛАШЕНИЙ ====================

@dp.message(Command("invite"))
async def cmd_invite(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("❌ Эта команда работает только в группах.")

    user = await _ensure_user(message.from_user.id, chat_id)
    if not user["guild_id"]:
        return await message.answer("❌ Ты не в гильдии.")

    g = await get_guild(user["guild_id"])
    if not g or user["guild_rank"] not in ("Лидер", "Офицер"):
        return await message.answer("❌ Только Лидер или Офицер может приглашать игроков.")

    members = await get_guild_members(g["guild_id"])
    if len(members) >= g.get("max_members", 5):
        return await message.answer("❌ В гильдии нет свободных мест.")

    target_ref, display = extract_target(message)
    if target_ref is None:
        return await message.answer(
            "⚔️ Ответь на сообщение игрока и напиши <code>/invite</code>, или укажи <code>/invite @username</code>",
            parse_mode="HTML")

    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            return await message.answer(f"❌ Не нашёл @{target_ref}. Пусть игрок напишет в чат с ботом.")
    else:
        target_id = target_ref

    if target_id == message.from_user.id:
        return await message.answer("❌ Себя пригласить нельзя.")

    target_user = await get_user(target_id, chat_id)
    if target_user and target_user["guild_id"]:
        return await message.answer(f"❌ {esc(display)} уже состоит в гильдии.")

    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять",
             callback_data=GuildInviteCB(action="accept", guild_id=g["guild_id"], target_id=target_id))
    b.button(text="❌ Отклонить",
             callback_data=GuildInviteCB(action="decline", guild_id=g["guild_id"], target_id=target_id))
    b.adjust(2)

    mention = f'<a href="tg://user?id={target_id}">{esc(display)}</a>'
    inviter = f'<a href="tg://user?id={message.from_user.id}">{esc(user["character_name"])}</a>'

    await message.answer(
        f"— [ 🏰 ПРИГЛАШЕНИЕ В ГИЛЬДИЮ ] —\n\n"
        f"{mention}, игрок {inviter} приглашает тебя в гильдию:\n\n"
        f"🛡 <b>{esc(g['name'])}</b>",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@dp.callback_query(GuildInviteCB.filter())
async def cb_guild_invite(query: types.CallbackQuery, callback_data: GuildInviteCB):
    if query.from_user.id != callback_data.target_id:
        return await query.answer("❌ Это приглашение не для тебя!", show_alert=True)

    if callback_data.action == "decline":
        await query.message.edit_text(f"— [ 🕊️ ОТКЛОНЕНО ] —\n\nТы отклонил приглашение в гильдию.",
                                      parse_mode="HTML")
        return

    chat_id = query.message.chat.id

    # ИСПРАВЛЕНИЕ: Проверка, не вступил ли уже в другую гильдию
    db_user = await get_user(query.from_user.id, chat_id)
    if db_user and db_user["guild_id"]:
        return await query.answer("❌ Вы уже состоите в гильдии!", show_alert=True)

    g = await get_guild(callback_data.guild_id)
    if not g:
        return await query.answer("❌ Гильдия больше не существует.", show_alert=True)

    members = await get_guild_members(g["guild_id"])
    if len(members) >= g.get("max_members", 5):
        return await query.answer("❌ В гильдии уже нет мест.", show_alert=True)

    # Вступаем
    await update_user(query.from_user.id, chat_id, guild_id=g["guild_id"], guild_rank="Участник", guild_contribution=0)

    target_user = await get_user(query.from_user.id, chat_id)
    name = esc(target_user["character_name"] or query.from_user.first_name)

    await query.message.edit_text(
        f"— [ 🎉 ДОБРО ПОЖАЛОВАТЬ! ] —\n\n"
        f"{name} вступил(а) в гильдию!\n\n"
        f"🛡 <b>{esc(g['name'])}</b>",
        parse_mode="HTML"
    )