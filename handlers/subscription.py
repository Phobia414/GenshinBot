from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import json

from bot_instance import bot, dp
from callbacks import SubCB, MenuCB
from db import get_setting, update_user, get_user
from keyboards import gender_kb, regions_kb


async def send_sub_message(message_or_query, user_id: int, chat_id: int):
    channels_json = await get_setting("sub_channels", "[]")
    channels = json.loads(channels_json)

    b = InlineKeyboardBuilder()
    if not channels:
        # Если админ забыл добавить каналы, пропускаем
        await update_user(user_id, chat_id, sub_passed=1)
        return False

    for ch in channels:
        b.button(text=f"📢 {ch['title']}", url=ch['url'])

    b.button(text="✅ Проверить подписку", callback_data=SubCB(action="check").pack())
    b.adjust(1)

    text = (
        "🔒 <b>Обязательная подписка</b>\n\n"
        "Пожалуйста, подпишитесь на каналы ниже, чтобы получить доступ к игре и общению в чате.\n\n"
        "После подписки нажмите кнопку <b>«Проверить подписку»</b>."
    )

    if isinstance(message_or_query, types.Message):
        await message_or_query.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")
    else:
        try:
            await message_or_query.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
        except:
            await message_or_query.message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")
    return True


@dp.callback_query(SubCB.filter(F.action == "check"))
async def cb_check_sub(query: types.CallbackQuery, state: FSMContext):
    await query.answer("Проверяем...", show_alert=False)
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    channels_json = await get_setting("sub_channels", "[]")
    channels = json.loads(channels_json)

    all_subbed = True
    for ch in channels:
        try:
            # Проверяем подписку на канал по его ID или @юзернейму
            member = await bot.get_chat_member(chat_id=ch['id'], user_id=user_id)
            if member.status in ('left', 'kicked'):
                all_subbed = False
                break
        except Exception as e:
            print(f"Ошибка проверки канала {ch['id']}: {e}")
            # Если бот не админ в канале, он не сможет проверить
            pass

    if all_subbed:
        await update_user(user_id, chat_id, sub_passed=1)

        user = await get_user(user_id, chat_id)
        if not user["gender"]:
            text = f"── 〔 ✨ ПРИВЕТСТВИЕ 〕 ──\n\nДобро пожаловать в Тейват!\n\nДля начала выбери свой пол:"
            await query.message.edit_text(text, reply_markup=gender_kb(user_id), parse_mode="HTML")
        else:
            text = f"── 〔 🌸 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nВыбери регион, откуда родом твой герой 🎭"
            await query.message.edit_text(text, reply_markup=regions_kb(user_id), parse_mode="HTML")
    else:
        await query.answer("❌ Вы подписались не на все каналы!", show_alert=True)