from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import json

from bot_instance import bot, dp
from callbacks import SubCB, MenuCB
from db import get_setting, update_user, get_user
from keyboards import gender_kb, regions_kb


async def send_sub_message(message_or_event, user_id: int, chat_id: int):
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

    b.button(text="✅ Проверить подписку", callback_data=SubCB(action="check").pack())
    b.adjust(1)

    user_mention = f'<a href="tg://user?id={user_id}">Новый участник</a>, ' if chat_id != user_id else ''

    text = (
        f"{user_mention}🔒 <b>Обязательная подписка</b>\n\n"
        "Пожалуйста, подпишитесь на каналы ниже, чтобы получить доступ к игре и общению в чате.\n\n"
        "После подписки нажмите кнопку <b>«Проверить подписку»</b>."
    )

    try:
        if isinstance(message_or_event, types.Message):
            # ИСПРАВЛЕНИЕ: Если это системное сообщение о входе, отправляем отдельным сообщением в чат
            if message_or_event.new_chat_members:
                await bot.send_message(chat_id, text, reply_markup=b.as_markup(), parse_mode="HTML")
            else:
                await message_or_event.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")

        elif isinstance(message_or_event, types.ChatMemberUpdated):
            await bot.send_message(chat_id, text, reply_markup=b.as_markup(), parse_mode="HTML")
        elif isinstance(message_or_event, types.CallbackQuery):
            await message_or_event.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
        else:
            await bot.send_message(chat_id, text, reply_markup=b.as_markup(), parse_mode="HTML")

    except Exception as e:
        print(f"Ошибка при отправке сообщения о подписке: {e}")
        return False
    return True


@dp.callback_query(SubCB.filter(F.action == "check"))
async def cb_check_sub(query: types.CallbackQuery, state: FSMContext):
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
        user = await get_user(user_id, chat_id)

        if not user["gender"]:
            text = f"── 〔 ✨ ПРИВЕТСТВИЕ 〕 ──\n\nДобро пожаловать в Тейват!\n\nДля начала выбери свой пол:"
            await query.message.edit_text(text, reply_markup=gender_kb(user_id), parse_mode="HTML")
        elif not user["character_name"]:
            text = f"── 〔 🌸 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nВыбери регион, откуда родом твой герой 🎭"
            await query.message.edit_text(text, reply_markup=regions_kb(user_id), parse_mode="HTML")
        else:
            await query.message.edit_text(
                "✅ Спасибо за подписку! Теперь вы можете общаться в чате. Напишите /start для вызова меню.")
    else:
        await query.answer("❌ Вы подписались не на все каналы!", show_alert=True)