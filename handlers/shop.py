from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    dt = f"\n🎖️ Скидка: -{disc}%" if disc else ""

    default_text = (
        f"╓───────────────────────╖\n"
        f"   🛒 ЛАВКА ТЕЙВАТА\n"
        f"╙───────────────────────╜\n\n"
        f"🍃 <b>{{name}}</b>, загляни!\n\n"
        f"╞═══════════════════════╡\n\n"
        f"╭ 💰 Баланс: <b>{{balance}}</b>\n"
        f"│\n"
        f"╰ 🎖️ Скидка: <b>{{discount}}</b>\n\n"
        f"╞═══════════════════════╡\n\n"
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

    image = await get_section_image("shop", chat_id=chat_id)
    await edit_or_send(query, text, shop_kb(query.from_user.id, disc), image_url=image)


@dp.callback_query(ShopCB.filter())
@inject_user
async def cb_shop_buy(query: types.CallbackQuery, callback_data: ShopCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    _, _, disc = get_reputation_bonuses(user["reputation"])

    prices = {
        "role": PRICE_ROLE_CHANGE,
        "rest": PRICE_REST,
        "clean": PRICE_CLEAN,
        "elixir": PRICE_ELIXIR
    }

    base = prices.get(callback_data.item, 0)
    price = int(base * (100 - disc) / 100) if disc else base

    if user["balance"] < price:
        await query.answer(f"❌ Нужно {price} монет", show_alert=True)
        return

    nb = user["balance"] - price

    if callback_data.item == "role":
        await update_user(query.from_user.id, chat_id, balance=nb, char_change_paid=1)
        b = InlineKeyboardBuilder()
        b.button(text="⊱ 🎭 Сменить персонажа ⊰", callback_data=MenuCB(action="regions", owner_id=query.from_user.id))
        b.button(text="⊱ ‹ В меню ⊰", callback_data=MenuCB(action="menu", owner_id=query.from_user.id))
        b.adjust(1)
        text = f"✅ СМЕНА КУПЛЕНА\n{DIV}\n\nОстаток: {nb}\n\n⚠️ Нажми кнопку ниже, чтобы выбрать нового героя!"
        await edit_or_send(query, text, b.as_markup())
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
            msg = f"🧪 Эликсир выпит! Вы с {esc(partner['partner_name'])} получили +50 XP.\n📊 Текущий уровень: {level} / {MAX_LEVEL}"
        else:
            await query.answer("❌ Ошибка данных партнера.", show_alert=True)
            return
    else:
        msg = "❌ Неизвестный предмет."

    b = InlineKeyboardBuilder()
    b.button(text="⊱ 🛒 В лавку ⊰", callback_data=MenuCB(action="shop", owner_id=query.from_user.id))
    b.button(text="⊱ ‹ В меню ⊰", callback_data=MenuCB(action="menu", owner_id=query.from_user.id))
    b.adjust(1)
    text = f"✅ ПОКУПКА\n{DIV}\n\n{msg}\n\n💰 Остаток: {nb}"
    await edit_or_send(query, text, b.as_markup())