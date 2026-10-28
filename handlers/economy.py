from aiogram import types, F
from aiogram.filters import Command

from bot_instance import dp
from db import get_user, update_primogems
from helpers import extract_target, resolve_user_id, esc, _ensure_user
from keyboards import back_kb


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
            await message.answer("❌ Игрок не найден.")
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
        f"💎 Ты передал **{amount}** примогемов игроку {esc(display)}!",
        parse_mode="Markdown",
        reply_markup=back_kb(message.from_user.id)
    )