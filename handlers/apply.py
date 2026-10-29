from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import time

from bot_instance import bot, dp
from config import OWNER_ID
from constants import DIV
from db import get_user, update_user, get_application, update_application_status, get_taken_characters, save_application
from characters import CHARACTERS
from helpers import esc


class ApplyForm(StatesGroup):
    age = State()
    age_visibility = State()
    experience = State()
    about = State()
    timezone = State()
    triggers = State()
    metagaming = State()
    activity = State()


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
    await state.set_state(ApplyForm.age_visibility)

    b = InlineKeyboardBuilder()
    b.button(text="✅ Показывать", callback_data="apply_age_show")
    b.button(text="❌ Скрыть", callback_data="apply_age_hide")

    await message.answer(
        f"👁 <b>Показывать ваш возраст в анкете при вступлении?</b>\n\n"
        f"Возраст будет виден другим участникам в приветственном сообщении.",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "apply_age_show")
async def cb_age_show(query: types.CallbackQuery, state: FSMContext):
    await query.message.edit_text("👁 Возраст будет отображаться в анкете.")
    await ask_experience(query.message, state)


@dp.callback_query(F.data == "apply_age_hide")
async def cb_age_hide(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(age="Скрыт")
    await query.message.edit_text("🙈 Возраст будет скрыт от других.")
    await ask_experience(query.message, state)


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
        f"Увлечения, достижения, образ жизни. <i>Вся ваша анкета будет автоматически отправлена в чат при вступлении!</i>",
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
        f"<i>Расшифровка: Метагейминг — это использование информации, которую ваш персонаж не знает в ролевой, но знаете вы как игрок.</i>\n\n"
        f"Напишите ваше отношение.",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.metagaming)
async def process_metagaming(message: types.Message, state: FSMContext):
    await state.update_data(metagaming=message.text)
    await state.set_state(ApplyForm.activity)
    await message.answer(
        f"⚡ <b>Какова ваша ожидаемая активность?</b>\n\n"
        f"Сколько постов в неделю вы сможете писать в ролевой? (Например: 10-15 постов в неделю).",
        parse_mode="HTML"
    )


@dp.message(ApplyForm.activity)
async def process_activity(message: types.Message, state: FSMContext):
    await state.update_data(activity=message.text)
    data = await state.get_data()

    await save_application(
        message.from_user.id, data["target_chat_id"], "Не выбран",
        data["age"], data["experience"], data["about"], data["timezone"],
        data["triggers"], data["metagaming"], data["activity"]
    )
    await state.clear()

    # ИСПРАВЛЕНО: Добавлен parse_mode="HTML"
    await message.answer("✅ <b>Ваша анкета отправлена на проверку администраторам!</b>\nПожалуйста, ожидайте ответа.",
                         parse_mode="HTML")

    text = (
        f"📩 <b>НОВАЯ АНКЕТА</b>\n{DIV}\n\n"
        f"👤 <b>Пользователь:</b> {esc(message.from_user.first_name)} (@{message.from_user.username})\n"
        f"🎭 <b>Роль:</b> Будет выбрана при входе\n\n"
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

    try:
        admins = await bot.get_chat_administrators(data["target_chat_id"])
        for admin in admins:
            if not admin.user.is_bot:
                try:
                    await bot.send_message(admin.user.id, text, reply_markup=b.as_markup(), parse_mode="HTML")
                except Exception:
                    pass
    except Exception as e:
        print(f"Ошибка при рассылке админам: {e}")
        try:
            await bot.send_message(OWNER_ID, text, reply_markup=b.as_markup(), parse_mode="HTML")
        except:
            pass


# --- Обработчики для владельца и админов ---

async def is_admin_of_chat(user_id: int, chat_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


@dp.callback_query(F.data.startswith("appr_accept_"))
async def cb_appr_accept(query: types.CallbackQuery):
    parts = query.data.replace("appr_accept_", "").split("_")
    user_id, chat_id = int(parts[0]), int(parts[1])

    if not await is_admin_of_chat(query.from_user.id, chat_id):
        await query.answer("❌ Вы не являетесь админом этой группы.", show_alert=True)
        return

    try:
        # ИСПРАВЛЕНО: Ссылка будет жить 24 часа, чтобы не сгорала, если человек нажмет позже
        expire_date = int(time.time()) + 86400
        link = await bot.create_chat_invite_link(chat_id, member_limit=1, expire_date=expire_date)
        invite_link = link.invite_link
    except Exception as e:
        await query.message.edit_text(f"{query.message.html_text}\n\n❌ <b>Ошибка создания ссылки:</b> {e}",
                                      parse_mode="HTML")
        return

    await update_application_status(user_id, chat_id, "accepted")
    await query.message.edit_text(
        f"{query.message.html_text}\n\n✅ <b>СТАТУС: ПРИНЯТ (Админ: {query.from_user.first_name})</b>",
        parse_mode="HTML")

    try:
        await bot.send_message(user_id,
                               f"🎉 <b>Поздравляем! Ваша анкета одобрена!</b>\n\n"
                               f"🔗 <b>Ссылка для вступления в группу (живет 24 часа):</b>\n{invite_link}\n\n"
                               f"<i>Как только вы зайдете в группу, бот попросит вас выбрать персонажа, и ваша анкета появится в чате.</i>",
                               parse_mode="HTML")
    except Exception:
        pass


@dp.callback_query(F.data.startswith("appr_decline_"))
async def cb_appr_decline(query: types.CallbackQuery):
    parts = query.data.replace("appr_decline_", "").split("_")
    user_id, chat_id = int(parts[0]), int(parts[1])

    if not await is_admin_of_chat(query.from_user.id, chat_id):
        await query.answer("❌ Вы не являетесь админом этой группы.", show_alert=True)
        return

    await update_application_status(user_id, chat_id, "rejected")
    await query.message.edit_text(
        f"{query.message.html_text}\n\n❌ <b>СТАТУС: ОТКЛОНЕН (Админ: {query.from_user.first_name})</b>",
        parse_mode="HTML")

    try:
        await bot.send_message(user_id, "😔 <b>К сожалению, ваша анкета была отклонена.</b>", parse_mode="HTML")
    except Exception:
        pass