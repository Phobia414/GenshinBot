from aiogram import types, F
from aiogram.filters import Command

from bot_instance import dp
from db import get_user, update_primogems
from helpers import extract_target, resolve_user_id, esc, _ensure_user
from keyboards import back_kb
from callbacks import ConfirmCB


@dp.message(Command("give"))
async def cmd_give_primogems(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Только в группе.")
        return

    target_ref, display = extract_target(message)
    if target_ref is None:
        await message.answer("Используй: /give Сумма (ответом на сообщение) или /give @user Сумма")
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[-1].isdigit():
        await message.answer("Укажи сумму в конце.")
        return

    amount = int(parts[-1])
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0.")
        return

    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            await message.answer("❌ Участник не найден.")
            return
    else:
        target_id = target_ref

    if target_id == message.from_user.id:
        await message.answer("❌ Себе нельзя.")
        return

    sender = await _ensure_user(message.from_user.id, chat_id)
    await _ensure_user(target_id, chat_id)

    if sender.get("primogems", 0) < amount:
        await message.answer("❌ У тебя недостаточно примогемов.")
        return

    await update_primogems(message.from_user.id, chat_id, -amount)
    await update_primogems(target_id, chat_id, amount)

    await message.answer(
        f"💎 Ты передал **{amount}** примогемов участнику {esc(display)}!",
        parse_mode="Markdown",
        reply_markup=back_kb(message.from_user.id)
    )
@dp.message(Command("transfer_coins"))
async def cmd_transfer_coins(message: types.Message, amount: int):
    chat_id = message.chat.id
    target_ref, display = extract_target(message)

    if target_ref is None:
        return await message.answer("Ответь на сообщение игрока или укажи @username.")

    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            return await message.answer("❌ Участник не найден.")
    else:
        target_id = target_ref

    if target_id == message.from_user.id:
        return await message.answer("❌ Себе нельзя.")

    sender = await _ensure_user(message.from_user.id, chat_id)
    await _ensure_user(target_id, chat_id)

    if sender["balance"] < amount:
        return await message.answer("❌ У тебя недостаточно монет.")

    await update_user(message.from_user.id, chat_id, balance=sender["balance"] - amount)
    target_user = await get_user(target_id, chat_id)
    await update_user(target_id, chat_id, balance=target_user["balance"] + amount)

    await message.answer(
        f"💰 Ты перевёл **{amount}** монет участнику {esc(display)}!",
        parse_mode="Markdown",
        reply_markup=back_kb(message.from_user.id)
    )


from callbacks import ConfirmCB  # <--- добавь в импорты вверху


@dp.callback_query(ConfirmCB.filter(F.action == "transfer"))
async def cb_confirm_transfer(query: types.CallbackQuery, callback_data: ConfirmCB):
    if query.from_user.id != callback_data.owner_id:
        return await query.answer("❌ Это не ваша кнопка.", show_alert=True)

    chat_id = query.message.chat.id
    amount = callback_data.amount
    target_id = callback_data.target_id

    sender = await get_user(query.from_user.id, chat_id)
    target_user = await get_user(target_id, chat_id)

    if not sender or not target_user:
        return await query.message.edit_text("❌ Ошибка базы данных. Игрок не найден.")

    if sender["balance"] < amount:
        return await query.message.edit_text("❌ У вас недостаточно монет на балансе.")

    await update_user(query.from_user.id, chat_id, balance=sender["balance"] - amount)
    await update_user(target_id, chat_id, balance=target_user["balance"] + amount)

    await query.message.edit_text(
        f"✅ Успешно переведено <b>{amount}</b> монет игроку {esc(target_user['character_name'])}!",
        parse_mode="HTML"
    )
@dp.callback_query(F.data == "cancel_confirm")
async def cb_cancel_confirm(query: types.CallbackQuery):
    await query.message.edit_text("❌ Действие отменено.", parse_mode="HTML")