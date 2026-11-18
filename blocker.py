from aiogram import types
from aiogram.filters import Command
from bot_instance import dp
from config import OWNER_ID
from db import block_user_db, unblock_user_db
from helpers import resolve_user_id


@dp.message(Command("block"))
async def cmd_block(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1:
            arg = parts[1]
            if arg.isdigit():
                target_id = int(arg)
            else:
                target_id = await resolve_user_id(arg)

    if not target_id:
        await message.answer("❌ Используй: /block (ответом на сообщение) или /block @username или /block ID")
        return

    if target_id == OWNER_ID:
        return await message.answer("❌ Себя блокировать нельзя.")

    await block_user_db(target_id)
    await message.answer(
        f"✅ Пользователь <code>{target_id}</code> заблокирован. Бот больше не будет реагировать на его действия.",
        parse_mode="HTML")


@dp.message(Command("unblock"))
async def cmd_unblock(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) > 1:
            arg = parts[1]
            if arg.isdigit():
                target_id = int(arg)
            else:
                target_id = await resolve_user_id(arg)

    if not target_id:
        await message.answer("❌ Используй: /unblock (ответом) или /unblock ID / @username")
        return

    await unblock_user_db(target_id)
    await message.answer(f"✅ Пользователь <code>{target_id}</code> разблокирован.", parse_mode="HTML")