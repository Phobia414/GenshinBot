from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot_instance import dp
from callbacks import MenuCB, ShopCB
from config import PRICE_ROLE_CHANGE, PRICE_REST, PRICE_CLEAN, PRICE_ELIXIR
from constants import DIV, XP_PER_LEVEL, MAX_LEVEL
from db import get_user, update_user, get_local_setting
from helpers import esc, get_reputation_bonuses, edit_or_send, get_section_image, inject_user, format_text
from keyboards import shop_kb


@dp.callback_query(MenuCB.filter(F.action == "shop"))
@inject_user
async def cb_shop(query: types.CallbackQuery, callback_data: MenuCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    _, _, disc = get_reputation_bonuses(user["reputation"])

    default_text = (
        f"─ [ 🛒 ЛАВКА ТЕЙВАТА ] ─\n\n"
        f"🍃 <b>{{name}}</b>, загляни!\n\n"
        f"💰 Баланс: <b>{{balance}}</b>\n\n"
        f"🎖️ Скидка: <b>{{discount}}</b>\n\n"
        f"Ассортимент:\n\n      "
        f"🎭 Смена персонажа: {{price_role}}\n"
        f"😴 Рест: {{price_rest}}\n"
        f"🧹 Чистка: {{price_clean}}\n"
        f"🧪 Эликсир Любви: {{price_elixir}}"
    )

    raw_text = await get_local_setting("text_shop", chat_id, default_text)

    text = format_text(raw_text, user, DIV) \
        .replace("{balance}", str(user["balance"])) \
        .replace("{discount}", f"-{disc}%" if disc else "Нет") \
        .replace("{price_role}", str(PRICE_ROLE_CHANGE)) \
        .replace("{price_rest}", str(PRICE_REST)) \
        .replace("{price_clean}", str(PRICE_CLEAN)) \
        .replace("{price_elixir}", str(PRICE_ELIXIR))

    custom_img = await get_local_setting("image_shop", chat_id)
    await edit_or_send(query, text, shop_kb(query.from_user.id, disc), image_url=custom_img or "")


@dp.callback_query(ShopCB.filter())
@inject_user
async def cb_shop_buy(query: types.CallbackQuery, callback_data: ShopCB, user: dict, chat_id: int, state: FSMContext):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    # Определяем цену для стандартных товаров
    price = 0
    if callback_data.item == "role":
        price = PRICE_ROLE_CHANGE
    elif callback_data.item == "rest":
        price = PRICE_REST
    elif callback_data.item == "clean":
        price = PRICE_CLEAN
    elif callback_data.item == "elixir":
        price = PRICE_ELIXIR

    # ОБРАБОТКА КАСТОМНЫХ ДЕЙСТВИЙ
    if callback_data.item in ["create_public", "create_private"]:
        is_private = 1 if callback_data.item == "create_private" else 0
        price = 8000 if is_private else 4000

        if user["balance"] < price:
            await query.answer(f"❌ Нужно {price} монет", show_alert=True)
            return

        # 1. Списываем баланс
        await update_user(query.from_user.id, chat_id, balance=user["balance"] - price)

        # 2. Включаем режим ожидания названия
        from handlers.custom_shop import CustomInteraction
        await state.set_state(CustomInteraction.waiting_for_name)
        await state.update_data(is_private=is_private)

        # 3. Отправляем инструкцию (безопасно)
        prompt_text = (
            "📝 **Создание нового действия**\n\n"
            "Напиши название действия (например: `потрепать по голове`).\n"
            "Оно должно быть коротким и начинаться с глагола."
        )

        try:
            # Пытаемся отредактировать текущее сообщение
            await query.message.edit_text(prompt_text, parse_mode="Markdown")
        except Exception:
            # Если это было фото или сообщение уже удалено — отправляем новое
            await query.message.answer(prompt_text, parse_mode="Markdown")

        # 4. Обязательно отвечаем на коллбэк, чтобы кнопка перестала грузиться
        await query.answer("Оплата прошла успешно!")
        return

    nb = user["balance"] - price

    if callback_data.item == "role":
        await update_user(query.from_user.id, chat_id, balance=nb, char_change_paid=1)
        b = InlineKeyboardBuilder()
        b.button(text="⊱ 🎭 Сменить персонажа ⊰", callback_data=MenuCB(action="regions", owner_id=query.from_user.id))
        b.button(text="⊱ ‹ В меню ⊰", callback_data=MenuCB(action="menu", owner_id=query.from_user.id))
        b.adjust(1)
        text = f"─ [ ✅ СМЕНА КУПЛЕНА ] ─\n\n💰 Остаток: {nb}\n\n⚠️ Нажми кнопку ниже, чтобы выбрать нового героя!"
        await edit_or_send(query, text, b.as_markup(), image_url="")
        return

    elif callback_data.item == "rest":
        await update_user(query.from_user.id, chat_id, balance=nb, rest_active=1)
        msg = "😴 Рест активирован."
    elif callback_data.item == "clean":
        await update_user(query.from_user.id, chat_id, balance=nb, clean_exempt=1)
        msg = "🧹 Освобождение от чистки активировано."
    elif callback_data.item == "elixir":
        if not user.get("partner_id"):
            await query.answer("❌ У тебя нет партнера, эликсир не подействует!", show_alert=True)
            return
        partner = await get_user(user["partner_id"], chat_id)
        if partner:
            new_xp = (user.get("rel_xp", 0) + 50)
            await update_user(query.from_user.id, chat_id, balance=nb, rel_xp=new_xp)
            await update_user(partner["user_id"], chat_id, rel_xp=partner.get("rel_xp", 0) + 50)
            level = min(new_xp // XP_PER_LEVEL, MAX_LEVEL)
            # ИСПРАВЛЕНО: partner['partner_name'] заменен на partner['character_name']
            msg = f"🧪 Эликсир выпит! Вы с {esc(partner['character_name'])} получили +50 XP.\n📊 Текущий уровень: {level} / {MAX_LEVEL}"
        else:
            await query.answer("❌ Ошибка данных партнера.", show_alert=True)
            return
    else:
        msg = "❌ Неизвестный предмет."

    b = InlineKeyboardBuilder()
    b.button(text="⊱ 🛒 В лавку ⊰", callback_data=MenuCB(action="shop", owner_id=query.from_user.id))
    b.button(text="⊱ ‹ В меню ⊰", callback_data=MenuCB(action="menu", owner_id=query.from_user.id))
    b.adjust(1)

    text = f"─ [ ✅ ПОКУПКА ] ─\n\n{msg}\n\n💰 Остаток: {nb}"
    await edit_or_send(query, text, b.as_markup(), image_url="")