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
from db import get_user, update_user, get_application, update_application_status, get_taken_characters, save_application, get_trusted_admins
from characters import CHARACTERS
from helpers import esc

# ================= СОСТОЯНИЯ =================
class ApplyForm(StatesGroup):
    age = State()
    age_visibility = State()
    experience = State()
    about = State()
    timezone = State()
    triggers = State()
    activity = State()
    source = State()

# ВОТ ЭТОТ КЛАСС НУЖНО ДОБАВИТЬ ОБЯЗАТЕЛЬНО:
class ApplyComment(StatesGroup):
    waiting_for_comment = State()
# =============================================

FORM_STEPS = [
    (ApplyForm.age, "age"),  # 0
    (ApplyForm.age_visibility, "age_visibility"),  # 1
    (ApplyForm.experience, "experience"),  # 2
    (ApplyForm.about, "about"),  # 3
    (ApplyForm.timezone, "timezone"),  # 4
    (ApplyForm.triggers, "triggers"),  # 5
    (ApplyForm.activity, "activity"),  # 6
    (ApplyForm.source, "source")  # 7
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
        text = "🕒 <b>Укажите ваш часовой пояс.</b>\n\nНапример: МСК, UTC+3, UTC+5. И удобное для вас время для общения."
    elif st == ApplyForm.triggers:
        text = "⚠️ <b>Будете ли вы ролить в нашем проекте?</b>\n\nНаша ролевая не обязательная. Если вы не планируете отыгрывать роль, просто напишите «Нет»."
    elif st == ApplyForm.activity:
        text = "⚡ <b>Какова ваша ожидаемая активность?</b>\n\nКак часто или сколько сообщений в неделю вы сможете писать?"
    elif st == ApplyForm.source:
        text = (
            "📢 <b>Откуда вы о нас узнали?</b>\n\n"
            "Тик ток, пиар чаты или кто-то посоветовал? Если вы связывались с участником или администратором нашего проекта для вступления, напишите его юзернейм пожалуйста или имя/никнейм."
        )

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


@dp.message(ApplyForm.age, F.text, ~F.text.startswith("/"))
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
    await state.update_data(age_raw=str(age), age=str(age))
    await send_step(message.chat.id, 1, state)


@dp.message(ApplyForm.experience, F.text, ~F.text.startswith("/"))
async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await send_step(message.chat.id, 3, state)


@dp.message(ApplyForm.about, F.text, ~F.text.startswith("/"))
async def process_about(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    await send_step(message.chat.id, 4, state)


@dp.message(ApplyForm.timezone, F.text, ~F.text.startswith("/"))
async def process_timezone(message: types.Message, state: FSMContext):
    await state.update_data(timezone=message.text)
    await send_step(message.chat.id, 5, state)


@dp.message(ApplyForm.triggers, F.text, ~F.text.startswith("/"))
async def process_triggers(message: types.Message, state: FSMContext):
    await state.update_data(triggers=message.text)
    await send_step(message.chat.id, 6, state)


@dp.message(ApplyForm.activity, F.text, ~F.text.startswith("/"))
async def process_activity(message: types.Message, state: FSMContext):
    await state.update_data(activity=message.text)
    await send_step(message.chat.id, 7, state) # Переходим к вопросу про источник


@dp.message(ApplyForm.source, F.text, ~F.text.startswith("/"))
async def process_source(message: types.Message, state: FSMContext):
    try:
        await state.update_data(source=message.text)
        data = await state.get_data()

        if "target_chat_id" not in data or not data["target_chat_id"]:
            await state.clear()
            await message.answer(
                "❌ Ошибка: не найден ID ролевой. Пожалуйста, начните заполнение анкеты заново по ссылке.")
            return

        # ИСПРАВЛЕНИЕ: Используем .get(), чтобы не вылетал KeyError и передаем source
        await save_application(
            message.from_user.id, data["target_chat_id"], "Не выбран",
            data.get("age", "Не указан"), data.get("experience", "Не указан"),
            data.get("about", "Не указано"), data.get("timezone", "Не указан"),
            data.get("triggers", "Не указаны"), "", data.get("activity", "Не указана"),
            data.get("source", "Не указан")
        )
        await state.clear()

        await message.answer(
            "✅ <b>Ваша анкета отправлена на проверку администраторам!</b>\nПожалуйста, ожидайте ответа.",
            parse_mode="HTML")

        text = (
            f"📩 <b>НОВАЯ АНКЕТА</b>\n{DIV}\n\n"
            f"👤 <b>Пользователь:</b> {esc(message.from_user.first_name)} (@{message.from_user.username})\n"
            f"🎭 <b>Роль:</b> Будет выбрана при входе\n\n"
            f"🎂 <b>Возраст:</b> {esc(data.get('age', 'Не указан'))}\n"
            f"📖 <b>Опыт:</b> {esc(data.get('experience', 'Не указан'))}\n"
            f"🌟 <b>О себе:</b> {esc(data.get('about', 'Не указано'))}\n"
            f"🕒 <b>Часовой пояс:</b> {esc(data.get('timezone', 'Не указан'))}\n"
            f"🎭 <b>Будет ролить:</b> {esc(data.get('triggers', 'Не указаны'))}\n"
            f"⚡ <b>Активность:</b> {esc(data.get('activity', 'Не указана'))}\n"
            f"📢 <b>Откуда узнал(а):</b> {esc(data.get('source', 'Не указан'))}"
        )

        b = InlineKeyboardBuilder()
        b.button(text="✅ Принять", callback_data=f"appr_accept_{message.from_user.id}_{data['target_chat_id']}")
        b.button(text="❌ Отклонить", callback_data=f"appr_decline_{message.from_user.id}_{data['target_chat_id']}")
        b.button(text="✍️ Комментарий", callback_data=f"appr_comment_{message.from_user.id}_{data['target_chat_id']}")
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
            try:
                await bot.send_message(OWNER_ID, text, reply_markup=b.as_markup(), parse_mode="HTML")
            except:
                pass

    except Exception as e:
        print(f"Ошибка при отправке анкеты: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении анкеты. Пожалуйста, напишите ответ еще раз или начните заново.")


@dp.message(StateFilter(ApplyForm), ~F.text)
async def process_non_text(message: types.Message, state: FSMContext):
    await message.answer("⚠️ Пожалуйста, отвечайте на вопросы <b>текстом</b> (сообщением).", parse_mode="HTML")


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

    # Меняем текст в чате того админа, который нажал
    new_text = f"{query.message.html_text}\n\n✅ <b>СТАТУС: ПРИНЯТ (Админ: {query.from_user.first_name})</b>"
    await query.message.edit_text(new_text, parse_mode="HTML")

    # ИСПРАВЛЕНИЕ: Уведомляем остальных админов
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            if not admin.user.is_bot and admin.user.id != query.from_user.id:
                try:
                    await bot.send_message(admin.user.id,
                                           f"🔔 Коллега {query.from_user.first_name} уже <b>ПРИНЯЛ</b> анкету пользователя <code>{user_id}</code>.\nДействий не требуется.",
                                           parse_mode="HTML")
                except:
                    pass
    except:
        pass

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

    new_text = f"{query.message.html_text}\n\n❌ <b>СТАТУС: ОТКЛОНЕН (Админ: {query.from_user.first_name})</b>"
    await query.message.edit_text(new_text, parse_mode="HTML")

    # ИСПРАВЛЕНИЕ: Уведомляем остальных админов
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            if not admin.user.is_bot and admin.user.id != query.from_user.id:
                try:
                    await bot.send_message(admin.user.id,
                                           f"🔔 Коллега {query.from_user.first_name} уже <b>ОТКЛОНИЛ</b> анкету пользователя <code>{user_id}</code>.\nДействий не требуется.",
                                           parse_mode="HTML")
                except:
                    pass
    except:
        pass

    try:
        await bot.send_message(user_id, "😔 <b>К сожалению, ваша анкета была отклонена.</b>", parse_mode="HTML")
    except Exception:
        pass


@dp.callback_query(F.data.startswith("appr_comment_"))
async def cb_appr_comment(query: types.CallbackQuery, state: FSMContext):
    parts = query.data.replace("appr_comment_", "").split("_")
    user_id, chat_id = int(parts[0]), int(parts[1])

    if not await is_admin_of_chat(query.from_user.id, chat_id):
        await query.answer("❌ Вы не являетесь админом этой группы.", show_alert=True)
        return

    # Сохраняем данные для следующего шага
    await state.update_data(appr_user_id=user_id, appr_chat_id=chat_id)
    await state.set_state(ApplyComment.waiting_for_comment)

    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="appr_cancel_comment")

    await query.message.reply(
        "✍️ **Напишите комментарий или причину отклонения для этого игрока.**\n\n"
        "Ваш текст будет отправлен ему в личные сообщения.",
        reply_markup=b.as_markup(),
        parse_mode="Markdown"
    )
    await query.answer()


@dp.callback_query(F.data == "appr_cancel_comment")
async def cb_appr_cancel_comment(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.delete()


@dp.message(ApplyComment.waiting_for_comment, F.text)
async def process_appr_comment_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("appr_user_id")
    chat_id = data.get("appr_chat_id")

    if not user_id or not chat_id:
        await message.answer("❌ Ошибка: данные анкеты утеряны.")
        await state.clear()
        return

    comment = message.text
    await update_application_status(user_id, chat_id, "rejected")
    await state.clear()

    # Отправляем комментарий игроку
    try:
        await bot.send_message(
            user_id,
            f"😔 <b>К сожалению, ваша анкета была отклонена.</b>\n\n"
            f"<b>Комментарий администратора:</b>\n<i>{esc(comment)}</i>",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("⚠️ Не удалось отправить сообщение игроку (возможно, у него закрыты ЛС).")

    await message.answer("✅ Анкета отклонена, а комментарий отправлен игроку!")

    # Уведомляем остальных админов
    try:
        admins = await bot.get_chat_administrators(chat_id)
        for admin in admins:
            if not admin.user.is_bot and admin.user.id != message.from_user.id:
                try:
                    await bot.send_message(
                        admin.user.id,
                        f"🔔 Админ {message.from_user.first_name} <b>ОТКЛОНИЛ</b> анкету пользователя <code>{user_id}</code> с комментарием:\n<i>{esc(comment)}</i>",
                        parse_mode="HTML"
                    )
                except:
                    pass
    except:
        pass