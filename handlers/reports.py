import time
from aiogram import types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from callbacks import MenuCB, ReportCB
from config import OWNER_ID
from db import save_complaint, get_trusted_admins
from helpers import esc


class ReportForm(StatesGroup):
    start = State()
    type = State()
    evidence = State()


@dp.callback_query(MenuCB.filter(F.action == "report_start"))
async def cb_report_start_group(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    bot_me = await bot.get_me()
    chat_id = query.message.chat.id
    link = f"https://t.me/{bot_me.username}?start=report_{chat_id}"
    await query.answer(url=link)


async def process_report_start(message: types.Message, chat_id: int, state: FSMContext):
    await state.clear()
    await state.update_data(report_chat_id=chat_id)
    await state.set_state(ReportForm.start)
    b = InlineKeyboardBuilder()
    b.button(text="📝 Написать жалобу", callback_data=ReportCB(action="start_pm").pack())
    await message.answer(
        "Привет, заметил нарушение со стороны участника или администрации?\n\n"
        "Нажми на кнопку ниже и напиши жалобу.",
        reply_markup=b.as_markup()
    )


@dp.callback_query(ReportCB.filter(F.action == "start_pm"), StateFilter(ReportForm.start))
async def cb_report_type(query: types.CallbackQuery, state: FSMContext):
    await state.set_state(ReportForm.type)
    b = InlineKeyboardBuilder()
    b.button(text="🕵️ Анонимная жалоба", callback_data=ReportCB(action="anon_yes").pack())
    b.button(text="👤 Подписанная жалоба", callback_data=ReportCB(action="anon_no").pack())
    b.adjust(1)
    await query.message.edit_text(
        "Выбери какая у тебя будет жалоба, анонимная или подписанная?\n\n"
        "🔒 <i>При анонимной жалобе, никто не увидит твой аккаунт, даже администраторы.</i>",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )
    await query.answer()


@dp.callback_query(ReportCB.filter(F.action.in_(["anon_yes", "anon_no"])), StateFilter(ReportForm.type))
async def cb_report_evidence(query: types.CallbackQuery, callback_data: ReportCB, state: FSMContext):
    is_anon = 1 if callback_data.action == "anon_yes" else 0
    await state.update_data(is_anon=is_anon)
    await state.set_state(ReportForm.evidence)
    await query.message.edit_text(
        "📥 <b>Отправь материал.</b>\n\n"
        "Пришли фото/видео материал доказательства нарушения со стороны пользователя, "
        "а также опиши ситуацию текстом в одном сообщении (или подпиши медиафайл).",
        parse_mode="HTML"
    )
    await query.answer("Пришли фото/видео материал доказательства нарушения", show_alert=True)


@dp.message(ReportForm.evidence)
async def report_get_evidence(message: types.Message, state: FSMContext):
    # ИСПРАВЛЕНИЕ (Баг 2): Проверяем и текст, и подпись к фото
    check_text = message.text or message.caption or ""
    if check_text.startswith("/"):
        await state.clear() # <--- СБРОС СОСТОЯНИЯ
        return  # Игнорируем команды в любом виде

    data = await state.get_data()
    chat_id = data.get("report_chat_id")
    is_anon = data.get("is_anon", 0)
    reason_text = check_text or "Без текста"

    await save_complaint(chat_id, message.from_user.id, 0, "Нарушитель", reason_text, is_anon)
    await state.clear()

    type_text = "🕵️ Анонимная" if is_anon else "👤 Подписанная"
    receipt_text = (
        f"✅ <b>Ваша жалоба успешно отправлена администрации!</b>\n\n"
        f"<b>Тип:</b> {type_text}\n"
        f"<b>Текст жалобы:</b>\n<i>{esc(reason_text)}</i>"
    )
    await message.answer(receipt_text, parse_mode="HTML")

    user_link = "Скрыт (Аноним)" if is_anon else f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'

    admin_header = (
        f"🚨 <b>НОВАЯ ЖАЛОБА</b>\n"
        f"Группа: <code>{chat_id}</code>\n"
        f"Тип: {type_text}\n"
        f"От кого: {user_link}\n\n"
        f"📝 <b>Описание:</b>\n<i>{esc(reason_text)}</i>\n\n"
        f"👇 <b>Доказательства (если есть) ниже:</b>"
    )

    admins = await get_trusted_admins()
    if not admins:
        admins = [OWNER_ID]

    for admin_id in admins:
        try:
            await bot.send_message(admin_id, admin_header, parse_mode="HTML")
            if not message.text:
                await message.copy_to(chat_id=admin_id)
        except Exception as e:
            print(f"Не удалось отправить жалобу админу {admin_id}: {e}")