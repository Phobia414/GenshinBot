import asyncio
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
import time

from bot_instance import bot, dp
from config import OWNER_ID
from constants import DIV
from db import get_user, update_user, get_application, update_application_status, get_taken_characters, \
    save_application, get_trusted_admins
from characters import CHARACTERS
from helpers import esc


class ApplyForm(StatesGroup):
    age = State()
    age_visibility = State()
    experience = State()
    about = State()
    timezone = State()
    triggers = State()
    activity = State()


FORM_STEPS = [
    (ApplyForm.age, "age"),
    (ApplyForm.age_visibility, "age_visibility"),
    (ApplyForm.experience, "experience"),
    (ApplyForm.about, "about"),
    (ApplyForm.timezone, "timezone"),
    (ApplyForm.triggers, "triggers"),
    (ApplyForm.activity, "activity")
]


async def send_step(chat_id: int, step_index: int, state: FSMContext):
    if step_index >= len(FORM_STEPS):
        return

    st, key = FORM_STEPS[step_index]
    await state.set_state(st)
    data = await state.get_data()

    b = InlineKeyboardBuilder()
    is_answered = data.get(key) is not None and data.get(key) != ""

    text = ""
    if st == ApplyForm.age:
        text = "🎂 <b>Сколько вам лет?</b>\n\nПожалуйста, укажите ваш реальный возраст цифрой. Мы принимаем участников строго с 14 лет."
    elif st == ApplyForm.age_visibility:
        text = "👁 <b>Показывать ваш возраст в анкете при вступлении?</b>\n\nВозраст будет виден другим участникам в приветственном сообщении."
        b.button(text="✅ Показывать", callback_data="apply_age_show")
        b.button(text="❌ Скрыть", callback_data="apply_age_hide")
    elif st == ApplyForm.experience:
        text = "📖 <b>Расскажите о вашем опыте в ролевых/флудах.</b>\n\nГде вы были раньше и как давно это было? Если вы новичок — просто напишите об этом."
    elif st == ApplyForm.about:
        text = "🌟 <b>Расскажите немного о себе.</b>\n\nУвлечения, достижения, образ жизни. <i>Вся ваша анкета будет автоматически отправлена в чат при вступлении!</i>"
    elif st == ApplyForm.timezone:
        text = "🕒 <b>Укажите ваш часовой пояс.</b>\n\nНапример: МСК, UTC+3, UTC+5. И удобное для вас время для отыгрышей."
    elif st == ApplyForm.triggers:
        text = "⚠️ <b>Есть ли у вас триггерные темы или то, что категорически неприемлемо в ролевой?</b>\n\nНапример: жестокость к животным, определенные фобии. Если таких тем нет — напишите «Нет»."
    elif st == ApplyForm.activity:
        text = "⚡ <b>Какова ваша ожидаемая активность?</b>\n\nКак часто или сколько сообщений в неделю вы сможете писать?"

    if step_index > 0:
        b.button(text="⬅️ Назад", callback_data="apply_nav_back")
    b.button(text="🔄 Заново", callback_data="apply_nav_rewrite")
    if is_answered and step_index < len(FORM_STEPS) - 1:
        b.button(text="➡️ Далее", callback_data="apply_nav_next")

    if st == ApplyForm.age_visibility:
        b.adjust(2, 2, 1)
    else:
        b.adjust(2, 1)

    await bot.send_chat_action(chat_id, 'typing')
    await asyncio.sleep(0.7)

    await bot.send_message(chat_id, text, reply_markup=b.as_markup(), parse_mode="HTML")


# ==================== ОБРАБОТЧИКИ КНОПОК НАВИГАЦИИ ====================

@dp.callback_query(F.data == "apply_nav_back", StateFilter(ApplyForm))
async def cb_nav_back(query: types.CallbackQuery, state: FSMContext):
    current_st = await state.get_state()
    idx = next((i for i, (st, _) in enumerate(FORM_STEPS) if st.state == current_st), 0)
    if idx > 0:
        try:
            await query.message.delete()
        except:
            pass
        await send_step(query.from_user.id, idx - 1, state)
    await query.answer()


@dp.callback_query(F.data == "apply_nav_next", StateFilter(ApplyForm))
async def cb_nav_next(query: types.CallbackQuery, state: FSMContext):
    current_st = await state.get_state()
    idx = next((i for i, (st, _) in enumerate(FORM_STEPS) if st.state == current_st), 0)
    if idx < len(FORM_STEPS) - 1:
        try:
            await query.message.delete()
        except:
            pass
        await send_step(query.from_user.id, idx + 1, state)
    await query.answer()


@dp.callback_query(F.data == "apply_nav_rewrite", StateFilter(ApplyForm))
async def cb_nav_rewrite(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    target_chat_id = data.get("target_chat_id")

    await state.clear()
    if target_chat_id:
        await state.update_data(target_chat_id=target_chat_id)

    try:
        await query.message.delete()
    except:
        pass

    await bot.send_message(query.from_user.id, "🔄 <b>Анкета полностью сброшена. Начинаем заново!</b>",
                           parse_mode="HTML")
    await send_step(query.from_user.id, 0, state)
    await query.answer("Анкета сброшена")


@dp.callback_query(F.data == "apply_age_show", StateFilter(ApplyForm.age_visibility))
async def cb_age_show(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    raw_age = data.get("age_raw", data.get("age", "18"))
    await state.update_data(age=raw_age)
    try:
        await query.message.delete()
    except:
        pass
    await send_step(query.from_user.id, 2, state)
    await query.answer()


@dp.callback_query(F.data == "apply_age_hide", StateFilter(ApplyForm.age_visibility))
async def cb_age_hide(query: types.CallbackQuery, state: FSMContext):
    await state.update_data(age="Скрыт")
    try:
        await query.message.delete()
    except:
        pass
    await send_step(query.from_user.id, 2, state)
    await query.answer()


# ==================== ОБРАБОТЧИКИ ТЕКСТОВЫХ ОТВЕТОВ ====================

@dp.message(ApplyForm.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text: return
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("❌ Пожалуйста, напишите возраст цифрой (например: 18).")
        return
    age = int(text)
    if age < 14:
        await state.clear()
        await message.answer("❌ К сожалению, мы принимаем участников только с 14 лет. Ваша анкета отклонена.")
        return
    await state.update_data(age_raw=str(age), age=str(age))
    await send_step(message.chat.id, 1, state)


@dp.message(ApplyForm.experience)
async def process_experience(message: types.Message, state: FSMContext):
    if not message.text: return
    await state.update_data(experience=message.text)
    await send_step(message.chat.id, 3, state)


@dp.message(ApplyForm.about)
async def process_about(message: types.Message, state: FSMContext):
    if not message.text: return
    await state.update_data(about=message.text)
    await send_step(message.chat.id, 4, state)


@dp.message(ApplyForm.timezone)
async def process_timezone(message: types.Message, state: FSMContext):
    if not message.text: return
    await state.update_data(timezone=message.text)
    await send_step(message.chat.id, 5, state)


@dp.message(ApplyForm.triggers)
async def process_triggers(message: types.Message, state: FSMContext):
    if not message.text: return
    await state.update_data(triggers=message.text)
    await send_step(message.chat.id, 6, state)


@dp.message(ApplyForm.activity)
async def process_activity(message: types.Message, state: FSMContext):
    if not message.text: return
    try:
        await state.update_data(activity=message.text)
        data = await state.get_data()

        if "target_chat_id" not in data or not data["target_chat_id"]:
            await state.clear()
            await message.answer(
                "❌ Ошибка: не найден ID ролевой. Пожалуйста, начните заполнение анкеты заново по ссылке.")
            return

        await save_application(
            message.from_user.id, data["target_chat_id"], "Не выбран",
            data["age"], data["experience"], data["about"], data["timezone"],
            data["triggers"], "", data["activity"]
        )
        await state.clear()

        await message.answer(
            "✅ <b>Ваша анкета отправлена на проверку администраторам!</b>\nПожалуйста, ожидайте ответа.",
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
            f"⚡ <b>Активность:</b> {esc(data['activity'])}"
        )

        b = InlineKeyboardBuilder()
        b.button(text="✅ Принять", callback_data=f"appr_accept_{message.from_user.id}_{data['target_chat_id']}")
        b.button(text="❌ Отклонить", callback_data=f"appr_decline_{message.from_user.id}_{data['target_chat_id']}")
        b.button(text="💬 Связаться", url=f"tg://user?id={message.from_user.id}")
        b.adjust(2, 1)

        # РАССЫЛАЕМ ТОЛЬКО ДОВЕРЕННЫМ АДМИНАМ
        admins = await get_trusted_admins()
        if not admins:
            admins = [OWNER_ID]

        for admin_id in admins:
            try:
                await bot.send_message(admin_id, text, reply_markup=b.as_markup(), parse_mode="HTML")
            except Exception as e:
                print(f"Ошибка отправки анкеты админу {admin_id}: {e}")

    except Exception as e:
        print(f"Ошибка при отправке анкеты: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении анкеты. Пожалуйста, напишите ответ еще раз или начните заново.")


# --- Обработчики для владельца и админов ---

async def is_admin_of_chat(user_id: int, chat_id: int) -> bool:
    if user_id == OWNER_ID: return True
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
                               f"🎉 <b>Поздравляем! Ваша анкета одобрена!</b>\n\n🔗 <b>Ссылка для вступления в группу:</b>\n{invite_link}\n\n<i>Как только вы зайдете в группу, бот попросит вас выбрать персонажа.</i>",
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