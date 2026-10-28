from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from config import OWNER_ID
from constants import DIV
from db import get_user, update_user, get_application, update_application_status, get_taken_characters, save_application
from characters import CHARACTERS
from helpers import esc


class ApplyForm(StatesGroup):
    choosing_char = State()
    age = State()
    experience = State()
    about = State()
    timezone = State()
    triggers = State()
    metagaming = State()
    activity = State()


@dp.callback_query(F.data.startswith("apply_char_"))
async def cb_apply_choose_char(query: types.CallbackQuery, state: FSMContext):
    char_name = query.data.replace("apply_char_", "")
    data = await state.get_data()
    chat_id = data.get("target_chat_id")

    # Проверяем, не заняли ли роль, пока он думал
    taken = await get_taken_characters(chat_id)
    if char_name in taken:
        await query.answer("❌ Увы, эту роль только что заняли. Выберите другую.", show_alert=True)
        return

    await state.update_data(character_name=char_name)
    await state.set_state(ApplyForm.age)

    b = InlineKeyboardBuilder()
    b.button(text="Пропустить", callback_data="apply_skip_age")

    await query.message.edit_text(
        f"🎂 <b>Сколько вам лет?</b>\n\n"
        f"Пожалуйста, укажите ваш реальный возраст цифрой. Мы принимаем участников строго с 14 лет.\n\n"
        f"<i>Если не хотите указывать — нажмите «Пропустить».</i>",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "apply_skip_age")
async def cb_skip_age(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(age="Не указан")
    await ask_experience(query.message, state)


@dp.message(ApplyForm.age)
async def process_age(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Пожалуйста, напишите возраст цифрой (например: 18).")
        return

    age = int(text)
    if age < 14:
        await state.clear()
        await message.answer("❌ К сожалению, мы принимаем участников только с 14 лет. Ваша анкета отклонена.")
        return

    await state.update_data(age=str(age))
    await ask_experience(message, state)


async def ask_experience(message: types.Message, state: FSMContext):
    await state.set_state(ApplyForm.experience)
    await message.answer(
        f"📖 <b>Расскажите о вашем опыте в ролевых.</b>\n\n"
        f"Где вы играли раньше и как давно это было? Если вы новичок — просто напишите об этом.",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.experience)
async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(ApplyForm.about)
    await message.answer(
        f"🌟 <b>Расскажите немного о себе.</b>\n\n"
        f"Увлечения, достижения, образ жизни. <i>Вся ваша анкета будет автоматически отправлена в чат при вступлении, чтобы другим участникам было проще начать с вами диалог!</i>",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.about)
async def process_about(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    await state.set_state(ApplyForm.timezone)
    await message.answer(
        f"🕒 <b>Укажите ваш часовой пояс.</b>\n\n"
        f"Например: МСК, UTC+3, UTC+5. И удобное для вас время для отыгрышей.",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.timezone)
async def process_timezone(message: types.Message, state: FSMContext):
    await state.update_data(timezone=message.text)
    await state.set_state(ApplyForm.triggers)
    await message.answer(
        f"⚠️ <b>Есть ли у вас триггерные темы или то, что категорически неприемлемо в ролевой?</b>\n\n"
        f"Например: жестокость к животным, определенные фобии. Если таких тем нет — напишите «Нет».",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.triggers)
async def process_triggers(message: types.Message, state: FSMContext):
    await state.update_data(triggers=message.text)
    await state.set_state(ApplyForm.metagaming)
    await message.answer(
        f"🚫 <b>Как вы относитесь к метагеймингу?</b>\n\n"
        f"<i>Расшифровка: Метагейминг — это использование информации, которую ваш персонаж не знает в ролевой, но знаете вы как игрок (например, вы прочитали в ООС-чате, что персонаж другого игрока задумал предательство, и ваш персонаж «случайно» начинает его подозревать).</i>\n\n"
        f"Напишите ваше отношение.",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.metagaming)
async def process_metagaming(message: types.Message, state: FSMContext):
    await state.update_data(metagaming=message.text)
    await state.set_state(ApplyForm.activity)
    await message.answer(
        f"⚡ <b>Какова ваша ожидаемая активность?</b>\n\n"
        f"Сколько постов в неделю вы сможете писать в ролевой, и как часто планируете заходить в чат? (Например: 10-15 постов в неделю, захожу каждый вечер).",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.activity)
async def process_activity(message: types.Message, state: FSMContext):
    await state.update_data(activity=message.text)
    data = await state.get_data()

    # Сохраняем в БД
    await save_application(
        message.from_user.id, data["target_chat_id"], data["character_name"],
        data["age"], data["experience"], data["about"], data["timezone"],
        data["triggers"], data["metagaming"], data["activity"]
    )
    await state.clear()

    await message.answer("✅ <b>Ваша анкета отправлена на проверку администратору!</b>\nПожалуйста, ожидайте ответа.")

    # Отправляем анкету владельцу бота
    try:
        text = (
            f"📩 <b>НОВАЯ АНКЕТА</b>\n{DIV}\n\n"
            f"👤 <b>Пользователь:</b> {esc(message.from_user.first_name)} (@{message.from_user.username})\n"
            f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
            f"🏰 <b>Чат (ID):</b> <code>{data['target_chat_id']}</code>\n"
            f"🎭 <b>Роль:</b> {esc(data['character_name'])}\n\n"
            f"🎂 <b>Возраст:</b> {esc(data['age'])}\n"
            f"📖 <b>Опыт:</b> {esc(data['experience'])}\n"
            f"🌟 <b>О себе:</b> {esc(data['about'])}\n"
            f"🕒 <b>Часовой пояс:</b> {esc(data['timezone'])}\n"
            f"⚠️ <b>Триггеры:</b> {esc(data['triggers'])}\n"
            f"🚫 <b>Метагейминг:</b> {esc(data['metagaming'])}\n"
            f"⚡ <b>Активность:</b> {esc(data['activity'])}"
        )

        b = InlineKeyboardBuilder()
        b.button(text="✅ Принять", callback_data=f"appr_accept_{message.from_user.id}_{data['target_chat_id']}")
        b.button(text="❌ Отклонить", callback_data=f"appr_decline_{message.from_user.id}_{data['target_chat_id']}")
        b.button(text="💬 Связаться", url=f"tg://user?id={message.from_user.id}")
        b.adjust(2, 1)

        await bot.send_message(OWNER_ID, text, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки анкеты: {e}")


# --- Обработчики для владельца (Принять/Отклонить) ---

@dp.callback_query(F.data.startswith("appr_accept_"))
async def cb_appr_accept(query: types.CallbackQuery):
    if query.from_user.id != OWNER_ID: return

    parts = query.data.replace("appr_accept_", "").split("_")
    user_id, chat_id = int(parts[0]), int(parts[1])

    # Создаем одноразовую ссылку
    try:
        link = await bot.create_chat_invite_link(chat_id, member_limit=1)
        invite_link = link.invite_link
    except Exception as e:
        await query.message.edit_text(f"{query.message.html_text}\n\n❌ <b>Ошибка создания ссылки:</b> {e}",
                                      parse_mode="HTML")
        return

    await update_application_status(user_id, chat_id, "accepted")
    await query.message.edit_text(f"{query.message.html_text}\n\n✅ <b>СТАТУС: ПРИНЯТ</b>", parse_mode="HTML")

    try:
        await bot.send_message(user_id,
                               f"🎉 <b>Поздравляем! Ваша анкета одобрена!</b>\n\n"
                               f"🔗 <b>Ссылка для вступления в группу:</b>\n{invite_link}\n\n"
                               f"<i>Ссылка одноразовая! Как только вы зайдете, бот опубликует вашу анкету в чате.</i>",
                               parse_mode="HTML")
    except Exception:
        pass


@dp.callback_query(F.data.startswith("appr_decline_"))
async def cb_appr_decline(query: types.CallbackQuery):
    if query.from_user.id != OWNER_ID: return

    parts = query.data.replace("appr_decline_", "").split("_")
    user_id, chat_id = int(parts[0]), int(parts[1])

    await update_application_status(user_id, chat_id, "rejected")
    await query.message.edit_text(f"{query.message.html_text}\n\n❌ <b>СТАТУС: ОТКЛОНЕН</b>", parse_mode="HTML")

    try:
        await bot.send_message(user_id,
                               "😔 <b>К сожалению, ваша анкета была отклонена.</b>\nВы можете попробовать связаться с администратором.",
                               parse_mode="HTML")
    except Exception:
        pass