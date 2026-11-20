from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta

from bot_instance import bot, dp
from config import OWNER_ID
from callbacks import AdminAppCB
from db import (get_pending_admin_applications, get_admin_application,
                update_admin_application_status, get_trusted_admins)
from constants import DIV
from helpers import esc  # <--- ДОБАВЛЕН ИМПОРТ ESC


class ReviewForm(StatesGroup):
    waiting_flaws_text = State()
    waiting_flaws_status = State()


@dp.message(Command("applications"))
async def cmd_applications_list(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return await message.answer("❌ Проверка анкет доступна только в ЛС бота.")

    if message.from_user.id != OWNER_ID:
        trusted = await get_trusted_admins()
        if message.from_user.id not in trusted:
            return await message.answer("❌ У вас нет доступа к проверке анкет.")

    await state.clear()
    await show_pending_list(message)


async def show_pending_list(message: types.Message):
    apps = await get_pending_admin_applications()
    if not apps:
        return await message.answer("📭 На данный момент нет нерассмотренных анкет.")

    b = InlineKeyboardBuilder()
    for app in apps:
        name = app['username'] or f"ID:{app['user_id']}"
        b.button(text=f"👤 {name}", callback_data=AdminAppCB(action="view", user_id=app['user_id']).pack())
    b.adjust(1)

    await message.answer(f"📥 <b>НЕРАССМОТРЕННЫЕ АНКЕТЫ</b>\n{DIV}\nВыберите анкету для просмотра:",
                         reply_markup=b.as_markup(), parse_mode="HTML")


@dp.callback_query(AdminAppCB.filter(F.action == "list"))
async def cb_back_to_list(query: types.CallbackQuery, callback_data: AdminAppCB):
    try:
        await query.message.delete()
    except:
        pass
    await show_pending_list(query.message)


@dp.callback_query(AdminAppCB.filter(F.action == "view"))
async def cb_view_app(query: types.CallbackQuery, callback_data: AdminAppCB, state: FSMContext):
    if query.from_user.id != OWNER_ID and query.from_user.id not in await get_trusted_admins():
        return await query.answer("❌ Нет доступа.", show_alert=True)

    user_id = callback_data.user_id
    app = await get_admin_application(user_id)
    if not app:
        return await query.answer("Анкета не найдена.", show_alert=True)
    if app['status'] != 'pending':
        return await query.answer(f"Эта анкета уже рассмотрена (Статус: {app['status']}).", show_alert=True)

    # ИСПРАВЛЕНИЕ: Экранируем все поля через esc(), чтобы HTML не ломался
    text_1 = f"👤 <b>АНКЕТА ОТ:</b> {esc(app['username'])} (<code>{user_id}</code>)\n{DIV}\n<b>1. Опыт:</b>\n{esc(app['q1'])}\n\n<b>2. Время:</b>\n{esc(app['q2'])}\n\n<b>3. Правила:</b>\n{esc(app['q3'])}\n\n<b>4. Бот:</b>\n{esc(app['q4'])}\n\n<b>5. Мотивация:</b>\n{esc(app['q5'])}"
    text_2 = f"<b>6. Ситуация (спор):</b>\n{esc(app['q6'])}\n\n<b>7. Ситуация (недочеты):</b>\n{esc(app['q7'])}\n\n<b>8. Подстройка:</b>\n{esc(app['q8'])}\n\n<b>9. Оскорбления друзей:</b>\n{esc(app['q9'])}"
    text_3 = f"<b>10. Сложный конфликт:</b>\n{esc(app['q10'])}\n\n<b>11. Срыв:</b>\n{esc(app['q11'])}\n\n<b>12. Ошибка:</b>\n{esc(app['q12'])}"

    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять", callback_data=AdminAppCB(action="accept", user_id=user_id).pack())
    b.button(text="❌ Отклонить", callback_data=AdminAppCB(action="reject", user_id=user_id).pack())
    b.button(text="✍️ Указать недочеты", callback_data=AdminAppCB(action="flaws", user_id=user_id).pack())
    b.button(text="💬 Связаться", url=f"tg://user?id={user_id}")
    b.button(text="‹ Назад к списку", callback_data=AdminAppCB(action="list").pack())
    b.adjust(2, 1, 1, 1)

    try:
        await query.message.edit_text(text_1, parse_mode="HTML")
        await query.message.answer(text_2, parse_mode="HTML")
        await query.message.answer(text_3, reply_markup=b.as_markup(), parse_mode="HTML")
    except Exception as e:
        await query.message.answer(f"Ошибка вывода: {e}")
    await query.answer()


async def send_accept_message(user_id: int, target_chat_id: int):
    msg = "🎉 <b>Поздравляем!</b>\nВаша анкета в администрацию была <b>ПРИНЯТА</b>!\n\n"
    if target_chat_id:
        try:
            member = await bot.get_chat_member(target_chat_id, user_id)
            if member.status in ('member', 'administrator', 'creator'):
                msg += "Вы уже находитесь в чате, ожидайте связи с куратором."
            else:
                link = await bot.create_chat_invite_link(target_chat_id, member_limit=1, expire_date=int(
                    (datetime.now() + timedelta(days=1)).timestamp()))
                msg += f"🔗 <b>Ссылка для вступления:</b>\n{link.invite_link}\n\n<i>(Ссылка действует 24 часа)</i>"
        except Exception as e:
            print(f"Ошибка при создании ссылки: {e}")
            msg += "С вами свяжется куратор для дальнейших инструкций."
    else:
        msg += "С вами свяжется куратор для дальнейших инструкций."

    try:
        await bot.send_message(user_id, msg, parse_mode="HTML")
    except:
        pass


@dp.callback_query(AdminAppCB.filter(F.action == "accept"))
async def cb_accept_app(query: types.CallbackQuery, callback_data: AdminAppCB):
    user_id = callback_data.user_id
    app = await get_admin_application(user_id)
    target_chat_id = app.get('target_chat_id', 0) if app else 0

    await update_admin_application_status(user_id, "accepted", reviewer_id=query.from_user.id)
    await send_accept_message(user_id, target_chat_id)

    await bot.send_message(OWNER_ID,
                           f"👑 <b>ЛОГ АНКЕТ</b>\nАдмин {esc(query.from_user.first_name)} (@{esc(query.from_user.username)}) ПРИНЯЛ анкету пользователя <code>{user_id}</code>.",
                           parse_mode="HTML")

    b = InlineKeyboardBuilder().button(text="‹ К списку анкет", callback_data=AdminAppCB(action="list").pack())
    await query.message.edit_text(f"✅ Вы ПРИНЯЛИ анкету <code>{user_id}</code>.\nСсылка отправлена пользователю.",
                                  reply_markup=b.as_markup())
    await query.answer("Принято!")


@dp.callback_query(AdminAppCB.filter(F.action == "reject"))
async def cb_reject_app(query: types.CallbackQuery, callback_data: AdminAppCB):
    user_id = callback_data.user_id
    await update_admin_application_status(user_id, "rejected", reviewer_id=query.from_user.id)

    try:
        await bot.send_message(user_id, "😔 <b>К сожалению...</b>\nВаша анкета в администрацию была <b>ОТКЛОНЕНА</b>.",
                               parse_mode="HTML")
    except:
        pass

    await bot.send_message(OWNER_ID,
                           f"👑 <b>ЛОГ АНКЕТ</b>\nАдмин {esc(query.from_user.first_name)} (@{esc(query.from_user.username)}) ОТКЛОНИЛ анкету пользователя <code>{user_id}</code>.",
                           parse_mode="HTML")

    b = InlineKeyboardBuilder().button(text="‹ К списку анкет", callback_data=AdminAppCB(action="list").pack())
    await query.message.edit_text(f"❌ Вы ОТКЛОНИЛИ анкету <code>{user_id}</code>.", reply_markup=b.as_markup())
    await query.answer("Отклонено!")


@dp.callback_query(AdminAppCB.filter(F.action == "flaws"))
async def cb_flaws_start(query: types.CallbackQuery, callback_data: AdminAppCB, state: FSMContext):
    await state.update_data(target_user=callback_data.user_id, flaws_buffer="")
    await state.set_state(ReviewForm.waiting_flaws_text)

    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data=AdminAppCB(action="view", user_id=callback_data.user_id).pack())

    await query.message.answer(
        "✍️ <b>Напиши, что не устроило в анкете (недочеты).</b>\nПользователь получит этот текст. (Можно писать в несколько сообщений, когда закончишь - нажми кнопку ниже)",
        reply_markup=b.as_markup(), parse_mode="HTML")
    await query.answer()


@dp.message(ReviewForm.waiting_flaws_text, F.text)
async def process_flaws_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_text = data.get("flaws_buffer", "")
    new_text = current_text + "\n" + message.text if current_text else message.text
    await state.update_data(flaws_buffer=new_text)

    b = InlineKeyboardBuilder()
    b.button(text="✅ Текст готов, выбрать итог", callback_data="flaws_ready")
    b.button(text="❌ Отмена", callback_data=AdminAppCB(action="view", user_id=data['target_user']).pack())
    await message.answer("Текст добавлен. Можешь написать еще или перейти к выбору итога.", reply_markup=b.as_markup())


@dp.callback_query(F.data == "flaws_ready")
async def process_flaws_ready(query: types.CallbackQuery, state: FSMContext):
    await state.set_state(ReviewForm.waiting_flaws_status)
    b = InlineKeyboardBuilder()
    b.button(text="✅ Анкета Принята (с недочетами)", callback_data="flaws_final_accept")
    b.button(text="❌ Анкета Отклонена", callback_data="flaws_final_reject")
    b.adjust(1)
    await query.message.edit_text("Выбери итоговый статус для этой анкеты:", reply_markup=b.as_markup())


@dp.callback_query(ReviewForm.waiting_flaws_status, F.data.startswith("flaws_final_"))
async def process_flaws_final(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = data['target_user']
    flaws_text = data.get("flaws_buffer", "")
    final_status = "accepted" if query.data == "flaws_final_accept" else "rejected"

    app = await get_admin_application(user_id)
    target_chat_id = app.get('target_chat_id', 0) if app else 0

    await update_admin_application_status(user_id, final_status, reviewer_id=query.from_user.id, flaws_text=flaws_text)

    status_str = "✅ ПРИНЯТА" if final_status == "accepted" else "❌ ОТКЛОНЕНА"
    user_msg = f"📩 <b>Ваша анкета рассмотрена!</b>\n\n<b>Комментарий проверяющего:</b>\n{esc(flaws_text)}\n\n<b>Итог:</b> {status_str}"

    try:
        await bot.send_message(user_id, user_msg, parse_mode="HTML")
        if final_status == "accepted":
            await send_accept_message(user_id, target_chat_id)
    except:
        pass

    await bot.send_message(OWNER_ID,
                           f"👑 <b>ЛОГ АНКЕТ</b>\nАдмин {esc(query.from_user.first_name)} рассмотрел анкету <code>{user_id}</code>.\nСтатус: {status_str}\nНедочеты:\n{esc(flaws_text)}",
                           parse_mode="HTML")

    await state.clear()
    b = InlineKeyboardBuilder().button(text="‹ К списку анкет", callback_data=AdminAppCB(action="list").pack())
    await query.message.edit_text(f"✅ Готово! Пользователь получил уведомление со статусом: {status_str}",
                                  reply_markup=b.as_markup())
    await query.answer()