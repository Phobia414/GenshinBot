from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp
from callbacks import MenuCB, ShopCB
from config import PRICE_ROLE_CHANGE, PRICE_REST, PRICE_CLEAN
from constants import DIV
from db import get_user, update_user
from helpers import esc, user_display_name, get_reputation_bonuses, edit_or_send
from keyboards import shop_kb


@dp.callback_query(MenuCB.filter(F.action == "shop"))
async def cb_shop(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    _, _, disc = get_reputation_bonuses(user["reputation"])
    dt = f"\n🎖️ Скидка: -{disc}%" if disc else ""
    name = esc(user_display_name(user))
    text = (f"🛒 ЛАВКА ТЕЙВАТА\n{DIV}\n\n{name}, загляни!\n\n"
            f"💰 Баланс: {user['balance']}{dt}\n\n"
            f"{DIV}\n\n"
            f"🎭 Смена персонажа: {PRICE_ROLE_CHANGE}\n"
            f"😴 Рест: {PRICE_REST}\n"
            f"🧹 Освобождение от чистки: {PRICE_CLEAN}")
    await edit_or_send(query, text, shop_kb(query.from_user.id, disc))


@dp.callback_query(ShopCB.filter())
async def cb_shop_buy(query: types.CallbackQuery, callback_data: ShopCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    _, _, disc = get_reputation_bonuses(user["reputation"])
    base = {"role": PRICE_ROLE_CHANGE, "rest": PRICE_REST, "clean": PRICE_CLEAN}[callback_data.item]
    price = int(base * (100 - disc) / 100) if disc else base
    if user["balance"] < price:
        await query.answer(f"❌ Нужно {price}", show_alert=True)
        return
    nb = user["balance"] - price
    if callback_data.item == "role":
        await update_user(query.from_user.id, balance=nb, char_change_paid=1)
        b = InlineKeyboardBuilder()
        b.button(text="🎭 Сменить персонажа ›", callback_data=MenuCB(action="regions", owner_id=query.from_user.id))
        b.button(text="‹ В меню", callback_data=MenuCB(action="menu", owner_id=query.from_user.id))
        b.adjust(1)
        text = f"✅ СМЕНА КУПЛЕНА\n{DIV}\n\nОстаток: {nb}"
        await edit_or_send(query, text, b.as_markup())
        return
    elif callback_data.item == "rest":
        await update_user(query.from_user.id, balance=nb, rest_active=1)
        msg = "Рест активирован"
    else:
        await update_user(query.from_user.id, balance=nb, clean_exempt=1)
        msg = "Освобождение от чистки"
    b = InlineKeyboardBuilder()
    b.button(text="🛒 В лавку ›", callback_data=MenuCB(action="shop", owner_id=query.from_user.id))
    b.button(text="‹ В меню", callback_data=MenuCB(action="menu", owner_id=query.from_user.id))
    b.adjust(1)
    text = f"✅ ПОКУПКА\n{DIV}\n\n{msg}\n\n💰 Остаток: {nb}"
    await edit_or_send(query, text, b.as_markup())