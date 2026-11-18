from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot_instance import dp
from db import add_custom_interaction
from keyboards import back_kb


class CustomInteraction(StatesGroup):
    waiting_for_name = State()
    waiting_for_emoji = State()


@dp.message(CustomInteraction.waiting_for_name)
async def process_custom_name(message: types.Message, state: FSMContext):
    name = message.text.lower().strip()

    if len(name) < 3 or len(name) > 30:
        return await message.answer("❌ Название должно быть от 3 до 30 символов.")
    if name.isdigit():
        return await message.answer("❌ Название не может состоять только из цифр.")

    await state.update_data(name=name)
    await state.set_state(CustomInteraction.waiting_for_emoji)

    await message.answer("✨ Отправь один эмодзи, который будет символизировать это действие (например, 🍰):")


@dp.message(CustomInteraction.waiting_for_emoji)
async def process_custom_emoji(message: types.Message, state: FSMContext):
    emoji = message.text.strip()
    if len(emoji) > 4:
        return await message.answer("❌ Отправь только один эмодзи.")

    data = await state.get_data()
    chat_id = message.chat.id
    user_id = message.from_user.id
    is_private = data.get("is_private", 0)

    await add_custom_interaction(chat_id, user_id, message.from_user.first_name, data["name"], emoji, is_private)
    await state.clear()

    status = "🔒 Личное (доступно только вам)" if is_private else "🌐 Общее (доступно всем)"
    await message.answer(
        f"✅ **Действие успешно создано!**\n\n"
        f"Эмодзи: {emoji}\n"
        f"Название: `{data['name']}`\n"
        f"Доступ: {status}\n\n"
        f"Чтобы использовать, напиши в чате:\n"
        f"`{data['name']}` (ответом на сообщение игрока) или `{data['name']} @юзер`",
        parse_mode="Markdown",
        reply_markup=back_kb(user_id)
    )