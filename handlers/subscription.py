import asyncio
from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import json

from bot_instance import bot, dp
from callbacks import SubCB, MenuCB
from db import get_setting, update_user, get_user
from keyboards import gender_kb, regions_kb

# Замок от двойного нажатия при входе
_send_locks = {}


async def send_sub_message(message_or_event, user_id: int, chat_id: int):
    if user_id not in _send_locks:
        _send_locks[user_id] = asyncio.Lock()

    if _send_locks[user_id].locked():
        return True

    async with _send_locks[user_id]:
        channels_json = await get_setting("sub_channels", "[]")
        try:
            channels = json.loads(channels_json)
        except:
            channels = []

        if not channels:
            await update_user(user_id, chat_id, sub_passed=1)
            return False

        b = InlineKeyboardBuilder()
        for ch in channels:
            b.button(text=f"📢 {ch['title']}", url=ch['url'])

        b.button(text="✅ Проверить подписку", callback_data=SubCB(action="check", target_id=user_id).pack())
        b.adjust(1)

        user_mention = f'<a href="tg://user?id={user_id}">Новый участник</a>, ' if chat_id != user_id else ''

        text = (
            f"{user_mention}🔒 <b>Обязательная подписка</b>\n\n"
            "Пожалуйста, подпишитесь на каналы ниже, чтобы получить доступ к игре и общению в чате.\n\n"
            "После подписки нажмите кнопку <b>«Проверить подписку»</b>."
        )

        try:
            if isinstance(message_or_event, (types.Message, types.ChatMemberUpdated)):
                await bot.send_message(chat_id, text, reply_markup=b.as_markup(), parse_mode="HTML")
            elif isinstance(message_or_event, types.CallbackQuery):
                await message_or_event.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")

            await asyncio.sleep(3)  # Защита от дублей
            return True
        except Exception as e:
            print(f"Ошибка при отправке сообщения о подписке: {e}")
            await update_user(user_id, chat_id, sub_passed=1)
            return False


@dp.callback_query(SubCB.filter(F.action == "check"))
async def cb_check_sub(query: types.CallbackQuery, callback_data: SubCB, state: FSMContext):
    if query.from_user.id != callback_data.target_id:
        await query.answer("❌ Это не ваша кнопка!", show_alert=True)
        return

    await query.answer("Проверяем...", show_alert=False)
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    channels_json = await get_setting("sub_channels", "[]")
    try:
        channels = json.loads(channels_json)
    except:
        channels = []

    all_subbed = True
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch['id'], user_id=user_id)
            if member.status in ('left', 'kicked'):
                all_subbed = False
                break
        except Exception as e:
            if "member list is inaccessible" in str(e):
                continue

    if all_subbed:
        await update_user(user_id, chat_id, sub_passed=1)
        try:
            await query.message.delete()  # Удаляем меню с каналами
        except:
            pass

        user = await get_user(user_id, chat_id)

        # СРАЗУ ВЫДАЕМ ПОЛ ИЛИ РЕГИОН
        if not user["gender"]:
            text = f"── 〔 ✨ ПРИВЕТСТВИЕ 〕 ──\n\nДобро пожаловать в Тейват!\n\nДля начала выбери свой пол:"
            await bot.send_message(chat_id, text, reply_markup=gender_kb(user_id), parse_mode="HTML")
        elif not user["character_name"]:
            text = f"── 〔 🌸 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nВыбери регион, откуда родом твой герой 🎭"
            await bot.send_message(chat_id, text, reply_markup=regions_kb(user_id), parse_mode="HTML")
        else:
            await bot.send_message(chat_id,
                                   "✅ Спасибо за подписку! Теперь вы можете общаться в чате. Напишите /start для вызова меню.")
    else:
        await query.answer("❌ Вы подписались не на все каналы!", show_alert=True)