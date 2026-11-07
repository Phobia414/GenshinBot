from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot_instance import bot, dp
from callbacks import MenuCB, RelCB, GiftCB, ProposeCB
from config import OWNER_ID, PROPOSE_COOLDOWN
from constants import (
    DIV, GIFTS, XP_PER_LEVEL, MAX_LEVEL, WEDDING_LEVEL,
)
from db import (
    get_user, update_user, get_protected_owner, get_local_setting
)
from helpers import (
    esc, user_display_name, edit_or_send, _ensure_user,
    extract_target, resolve_user_id, _now_ts, get_section_image, inject_user
)
from keyboards import relations_kb, gifts_kb, back_kb
from state import _propose_cooldown


class RelationsEdit(StatesGroup):
    waiting_for_image = State()


@dp.callback_query(MenuCB.filter(F.action == "relations"))
@inject_user
async def cb_relations(query: types.CallbackQuery, callback_data: MenuCB, user: dict, chat_id: int, state: FSMContext):
    await state.clear()
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    name = esc(user_display_name(user))

    if user["partner_id"]:
        level = min(user["rel_xp"] // XP_PER_LEVEL, MAX_LEVEL)
        married = bool(user["is_married"])
        status = "💍 В браке" if married else "💕 В отношениях"
        started = (datetime.fromtimestamp(user["rel_started"], timezone.utc).strftime("%d.%m.%Y") if user[
            "rel_started"] else "?")
        extra = ""
        if married and user["married_at"]:
            extra += f"\n📅 Свадьба: {datetime.fromtimestamp(user['married_at'], timezone.utc).strftime('%d.%m.%Y')}"
        if user["child_id"]:
            extra += f"\n👶 Ребёнок: {esc(user['child_name'])}"

        default_text = (
            f"— [ ❤️ ОТНОШЕНИЯ ] —\n\n"
            f"💕 {name} + {esc(user['partner_name'])}\n\n"
            f"📅 Вместе с: {started}\n"
            f"📊 Уровень: {level} / {MAX_LEVEL}\n"
            f"✨ Опыт: {user['rel_xp']} XP\n"
            f"💍 Статус: {status}{extra}"
        )
        raw_text = await get_local_setting("text_relations", chat_id, default_text)
        text = raw_text.replace("{name}", name).replace("{partner_name}", esc(user['partner_name'])).replace(
            "{rel_started}", started).replace("{rel_level}", str(level)).replace("{max_level}", str(MAX_LEVEL)).replace(
            "{rel_xp}", str(user['rel_xp'])).replace("{rel_status}", status).replace("{extra}", extra).replace("{div}",
                                                                                                               DIV)
        kb = relations_kb(query.from_user.id, True, married, level >= WEDDING_LEVEL, bool(user["child_id"]),
                          user["gender"])
    else:
        default_text = (
            f"— [ ❤️ ОТНОШЕНИЯ ] —\n\n"
            f"🍃 {name}, твоё сердце свободно 💌\n\n"
            f"Ответь на сообщение игрока\n"
            f"и напиши /propose\n\n"
            f"или укажи @username: /propose @user"
        )
        raw_text = await get_local_setting("text_relations", chat_id, default_text)
        text = raw_text.replace("{name}", name).replace("{div}", DIV)
        kb = relations_kb(query.from_user.id, False, False, False, False, user["gender"])

    # Подтягиваем кастомную картинку пары или стандартную картинку меню
    custom_img = await get_local_setting("image_relations", chat_id)
    img = user.get("rel_image") or custom_img
    await edit_or_send(query, text, kb, image_url=img or "")


# ==========================================
# ЛОГИКА ФОТО ПАРЫ (КНОПКА "ФОТО ПАРЫ")
# ==========================================
@dp.callback_query(RelCB.filter(F.action == "set_image"))
@inject_user
async def cb_set_rel_image(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int,
                           state: FSMContext):
    await query.answer()  # Убираем "часики" загрузки на кнопке

    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    if not user["partner_id"]:
        await query.answer("❌ У тебя нет партнёра.", show_alert=True)
        return

    await state.set_state(RelationsEdit.waiting_for_image)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data=MenuCB(action="relations", owner_id=query.from_user.id))

    await edit_or_send(query, "📸 **Отправь фотографию**, которая будет стоять в вашем меню отношений.",
                       b.as_markup(), image_url="")


@dp.message(RelationsEdit.waiting_for_image, F.photo)
async def process_rel_image(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id, message.chat.id)
    if not user or not user["partner_id"]:
        await message.answer("❌ Ошибка: нет партнёра.")
        await state.clear()
        return

    file_id = message.photo[-1].file_id

    # Сохраняем фото и себе, и партнёру, чтобы у вас обоих оно отображалось
    await update_user(message.from_user.id, message.chat.id, rel_image=file_id)
    await update_user(user["partner_id"], message.chat.id, rel_image=file_id)

    await state.clear()
    b = InlineKeyboardBuilder()
    b.button(text="❤️ К отношениям", callback_data=MenuCB(action="relations", owner_id=message.from_user.id))
    await message.answer("✅ Фото пары успешно обновлено!", reply_markup=b.as_markup())


# ==========================================
# ЛОГИКА ПОДАРКОВ (КНОПКА "ПОДАРИТЬ ПОДАРОК")
# ==========================================
@dp.callback_query(RelCB.filter(F.action == "gifts"))
@inject_user
async def cb_gifts(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int):
    await query.answer()

    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return

    text = f"— [ 🎁 ПОДАРКИ ] —\n\nДля: {esc(user['partner_name'])}\n\n💰 Твой баланс: {user['balance']}"
    await edit_or_send(query, text, gifts_kb(query.from_user.id), image_url="")


@dp.callback_query(GiftCB.filter())
@inject_user
async def cb_buy_gift(query: types.CallbackQuery, callback_data: GiftCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return

    gift = GIFTS.get(callback_data.item)
    if not gift:
        await query.answer("❌ Подарок не найден.", show_alert=True)
        return

    if user["balance"] < gift["price"]:
        await query.answer("❌ Недостаточно монет на балансе!", show_alert=True)
        return

    partner = await get_user(user["partner_id"], chat_id)
    if not partner:
        await query.answer("❌ Ошибка базы данных партнёра.", show_alert=True)
        return

    # Вычитаем баланс и добавляем опыт
    new_balance = user["balance"] - gift["price"]
    new_xp = user["rel_xp"] + gift["xp"]

    await update_user(query.from_user.id, chat_id, balance=new_balance, rel_xp=new_xp)
    await update_user(partner["user_id"], chat_id, rel_xp=new_xp)

    level = min(new_xp // XP_PER_LEVEL, MAX_LEVEL)

    await query.answer(f"✅ Ты подарил(а) {gift['name']}!\n+{gift['xp']} XP к отношениям.", show_alert=True)

    # Возвращаем в меню подарков с обновленным балансом
    text = f"— [ 🎁 ПОДАРКИ ] —\n\nДля: {esc(partner['character_name'])}\n\n💰 Твой баланс: {new_balance}\n📊 Уровень отношений: {level} / {MAX_LEVEL}"
    await edit_or_send(query, text, gifts_kb(query.from_user.id), image_url="")


@dp.callback_query(F.data == "rel_gift_menu_back")
@inject_user
async def cb_gift_back(query: types.CallbackQuery, user: dict, chat_id: int):
    # Этот обработчик нужен на случай, если в клавиатуре подарков есть кнопка "Назад"
    b = InlineKeyboardBuilder()
    b.button(text="⊱ ‹ Назад ⊰", callback_data=MenuCB(action="relations", owner_id=query.from_user.id))
    text = f"— [ ❤️ ОТНОШЕНИЯ ] —"
    await edit_or_send(query, text, b.as_markup(), image_url="")