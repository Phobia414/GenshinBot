from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

from bot_instance import bot, dp
from config import OWNER_ID
from callbacks import AdminAppCB
from db import save_admin_application, get_admin_application, get_trusted_admins
from constants import DIV
from helpers import is_chat_admin


class AdminApplyForm(StatesGroup):
    q1 = State();
    q2 = State();
    q3 = State();
    q4 = State()
    q5 = State();
    q6 = State();
    q7 = State();
    q8 = State()
    q9 = State();
    q10 = State();
    q11 = State();
    q12 = State()
    confirm = State()


QUESTIONS = {
    "q1": "1. Ваш опыт во флудах/ролевых, других проектах (Игры, группы, работа) как администратора. Напишите подробный ответ. (Сколько были на посту администрации, какие должности занимали и как относитесь к должностной лестнице, можете добавить свое, если есть, что рассказать.)",
    "q2": "2. Ваше свободное время в реальной жизни, напишите примерное количество времени или расскажите о вашей занятости. (Время на учебу/работу, хобби, отдых, так нам будет легче узнать о вашем свободном времени для флуда.)",
    "q3": "3. Как хорошо вы знаете наши правила? Выберите вариант ниже:",
    "q4": "4. Читали ли вы информацию про нашего бота о его механиках, функциях и общем описании?",
    "q5": "5. Почему решили стать частью администрации нашего проекта?",
    "q6": "6. В административном чате происходит спор двух членов администрации, один из них намного меньше рангом другого. (Например Мл. Модер спорит с Гл. Админом) Вы являетесь обычным модератором и видите как Гл. Админ, начинает унижать или переходить на личности Мл. Модера в чате администрации. Владельца или Совладельца нет в сети на данный момент, ваши действия? (Гл. Админ является членом высшей администрации, отвечает за должности ниже себя и курирует их)",
    "q7": "7. Участник в чате начинает указывать на не точности в системе проекта, бота, администрации. Вы как ответственный администратор, начинаете выяснять, что именно не нравится участнику и почему. Он указывает на моменты которые вы можете оспорить. Вы начнете спор отстояв проект, бота, администрацию или отступите и просто примете к сведению упрёк который вы могли оспорить? (Ответить кратко, что предпримете и почему?)",
    "q8": "8. Администрация должна подстраиваться под участников или участники под администрацию? (2-3 предложения, что и почему?)",
    "q9": "9. Действующее правило: \"Всем участникам чата запрещено оскорблять, унижать, провоцировать, угнетать других участников чата.\" Два друга знакомые между собой начали друг друга в \"шутку\" оскорблять, ваши действия, учитывая, действующее правило? (Ответить кратко, что предпримете и почему?)",
    "q10": "10. Расскажите о самом сложном конфликте который вы рассматривали как администратор. Удалось ли вам его устранить? Если да, то как?",
    "q11": "11. Бывало ли, что вы сорвались на участника/администратора? Что послужило триггером?",
    "q12": "12. Вспомните ситуацию, когда вы допустили ошибку в выполнении обязанностей и это вызвало недовольство со стороны коллег-администраторов или участников, как вы себя повели? Признали ошибку или пытались оспорить? Делали что то, чтобы исправить ситуацию?"
}


@dp.message(Command("adminlink"))
async def cmd_adminlink(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("❌ Эта команда работает только в группе.")

    if message.from_user.id != OWNER_ID and not await is_chat_admin(message.chat.id, message.from_user.id):
        return await message.answer("❌ Только для администраторов группы.")

    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=admin_apply_{message.chat.id}"

    text = (
        f"🔗 <b>ССЫЛКА ДЛЯ НАБОРА В АДМИНИСТРАЦИЮ</b>\n{DIV}\n\n"
        f"Отправьте эту ссылку в рекламный пост или закрепите в чате. "
        f"Все, кто по ней перейдут, смогут заполнить анкету на пост администратора.\n\n"
        f"<code>{link}</code>\n\n"
        f"<i>Анкеты будут приходить в ЛС всем доверенным админам и владельцу.</i>"
    )
    await message.answer(text, parse_mode="HTML")


async def start_admin_apply(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return await message.answer("❌ Анкету нужно заполнять в личных сообщениях с ботом.")

    app = await get_admin_application(message.from_user.id)
    if app:
        if app['status'] == 'pending':
            return await message.answer("⏳ Ваша анкета уже находится на рассмотрении у администрации.")
        elif app['status'] == 'accepted':
            return await message.answer("✅ Вы уже являетесь частью администрации.")

    await state.clear()
    await state.set_state(AdminApplyForm.q1)

    text = (
        f"📝 <b>АНКЕТА В АДМИНИСТРАЦИЮ</b>\n{DIV}\n"
        f"Заполнение займет около 10-15 минут. Отвечайте честно и развернуто.\n\n"
        f"<b>Для отмены напишите:</b> /cancel\n\n"
        f"{QUESTIONS['q1']}"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("admin_apply"))
async def cmd_admin_apply(message: types.Message, state: FSMContext):
    await start_admin_apply(message, state)


@dp.message(Command("cancel"))
async def cmd_cancel_apply(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None and current_state.startswith("AdminApplyForm"):
        await state.clear()
        await message.answer("❌ Заполнение анкеты отменено.")


@dp.message(AdminApplyForm.q1, F.text)
async def process_q1(message: types.Message, state: FSMContext):
    await state.update_data(q1=message.text)
    await state.set_state(AdminApplyForm.q2)
    await message.answer(QUESTIONS["q2"])


@dp.message(AdminApplyForm.q2, F.text)
async def process_q2(message: types.Message, state: FSMContext):
    await state.update_data(q2=message.text)
    await state.set_state(AdminApplyForm.q3)

    b = InlineKeyboardBuilder()
    b.button(text="1) Один раз прочитал", callback_data="a_ans_q3_1) Один раз прочитал")
    b.button(text="2) Итак знаю, даже не читал", callback_data="a_ans_q3_2) Итак знаю, даже не читал")
    b.button(text="3) Читал пару раз, помню большую часть",
             callback_data="a_ans_q3_3) Читал пару раз, помню большую часть")
    b.button(text="4) Не помню вообще", callback_data="a_ans_q3_4) Не помню вообще")
    b.button(text="5) Идеально знаю правила, учил их", callback_data="a_ans_q3_5) Идеально знаю правила, учил их")
    b.adjust(1)
    await message.answer(QUESTIONS["q3"], reply_markup=b.as_markup())


@dp.callback_query(AdminApplyForm.q3, F.data.startswith("a_ans_q3_"))
async def process_q3_btn(query: types.CallbackQuery, state: FSMContext):
    ans = query.data.replace("a_ans_q3_", "")
    await state.update_data(q3=ans)
    await query.message.edit_text(f"{QUESTIONS['q3']}\n\n✅ <b>Ваш ответ:</b> {ans}")

    await state.set_state(AdminApplyForm.q4)
    b = InlineKeyboardBuilder()
    b.button(text="Да, читал внимательно", callback_data="a_ans_q4_Да, читал внимательно")
    b.button(text="Частично", callback_data="a_ans_q4_Частично")
    b.button(text="Нет, не читал", callback_data="a_ans_q4_Нет, не читал")
    b.adjust(1)
    await query.message.answer(QUESTIONS["q4"], reply_markup=b.as_markup())
    await query.answer()


@dp.callback_query(AdminApplyForm.q4, F.data.startswith("a_ans_q4_"))
async def process_q4_btn(query: types.CallbackQuery, state: FSMContext):
    ans = query.data.replace("a_ans_q4_", "")
    await state.update_data(q4=ans)
    await query.message.edit_text(f"{QUESTIONS['q4']}\n\n✅ <b>Ваш ответ:</b> {ans}")

    await state.set_state(AdminApplyForm.q5)
    await query.message.answer(QUESTIONS["q5"])
    await query.answer()


@dp.message(AdminApplyForm.q5, F.text)
async def process_q5(message: types.Message, state: FSMContext):
    await state.update_data(q5=message.text)
    await state.set_state(AdminApplyForm.q6)
    await message.answer(QUESTIONS["q6"])


@dp.message(AdminApplyForm.q6, F.text)
async def process_q6(message: types.Message, state: FSMContext):
    await state.update_data(q6=message.text)
    await state.set_state(AdminApplyForm.q7)
    await message.answer(QUESTIONS["q7"])


@dp.message(AdminApplyForm.q7, F.text)
async def process_q7(message: types.Message, state: FSMContext):
    await state.update_data(q7=message.text)
    await state.set_state(AdminApplyForm.q8)
    await message.answer(QUESTIONS["q8"])


@dp.message(AdminApplyForm.q8, F.text)
async def process_q8(message: types.Message, state: FSMContext):
    await state.update_data(q8=message.text)
    await state.set_state(AdminApplyForm.q9)
    await message.answer(QUESTIONS["q9"])


@dp.message(AdminApplyForm.q9, F.text)
async def process_q9(message: types.Message, state: FSMContext):
    await state.update_data(q9=message.text)
    await state.set_state(AdminApplyForm.q10)
    await message.answer(QUESTIONS["q10"])


@dp.message(AdminApplyForm.q10, F.text)
async def process_q10(message: types.Message, state: FSMContext):
    await state.update_data(q10=message.text)
    await state.set_state(AdminApplyForm.q11)
    await message.answer(QUESTIONS["q11"])


@dp.message(AdminApplyForm.q11, F.text)
async def process_q11(message: types.Message, state: FSMContext):
    await state.update_data(q11=message.text)
    await state.set_state(AdminApplyForm.q12)
    await message.answer(QUESTIONS["q12"])


@dp.message(AdminApplyForm.q12, F.text)
async def process_q12(message: types.Message, state: FSMContext):
    await state.update_data(q12=message.text)
    await state.set_state(AdminApplyForm.confirm)

    data = await state.get_data()
    preview = (
        f"👀 <b>ПРОВЕРЬТЕ ВАШИ ОТВЕТЫ</b>\n{DIV}\n"
        f"<b>1. Опыт:</b> {data['q1'][:100]}...\n"
        f"<b>2. Время:</b> {data['q2'][:100]}...\n"
        f"<b>3. Правила:</b> {data['q3']}\n"
        f"<b>4. Бот:</b> {data['q4']}\n"
        f"<b>5. Мотивация:</b> {data['q5'][:100]}...\n\n"
        f"<i>(Полный текст будет отправлен админам)</i>"
    )

    b = InlineKeyboardBuilder()
    b.button(text="✅ Отправить", callback_data="a_ans_submit")
    b.button(text="🔄 Заполнить заново", callback_data="a_ans_restart")
    b.adjust(1)
    await message.answer(preview, reply_markup=b.as_markup(), parse_mode="HTML")


@dp.callback_query(AdminApplyForm.confirm, F.data == "a_ans_submit")
async def process_submit(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    username = f"@{query.from_user.username}" if query.from_user.username else query.from_user.first_name

    await save_admin_application(query.from_user.id, username, data)

    # Рассылка "потоком" сразу всем админам
    admins = await get_trusted_admins()
    if OWNER_ID not in admins: admins.append(OWNER_ID)

    text_1 = (
        f"📥 <b>НОВАЯ АНКЕТА В АДМИНИСТРАЦИЮ</b>\n"
        f"👤 От: {username} (<code>{query.from_user.id}</code>)\n{DIV}\n"
        f"<b>1. Опыт:</b>\n{data['q1']}\n\n"
        f"<b>2. Время:</b>\n{data['q2']}\n\n"
        f"<b>3. Правила:</b>\n{data['q3']}\n\n"
        f"<b>4. Бот:</b>\n{data['q4']}\n\n"
        f"<b>5. Мотивация:</b>\n{data['q5']}"
    )

    text_2 = (
        f"<b>6. Ситуация (спор):</b>\n{data['q6']}\n\n"
        f"<b>7. Ситуация (недочеты):</b>\n{data['q7']}\n\n"
        f"<b>8. Подстройка:</b>\n{data['q8']}\n\n"
        f"<b>9. Оскорбления друзей:</b>\n{data['q9']}"
    )

    text_3 = (
        f"<b>10. Сложный конфликт:</b>\n{data['q10']}\n\n"
        f"<b>11. Срыв:</b>\n{data['q11']}\n\n"
        f"<b>12. Ошибка:</b>\n{data['q12']}"
    )

    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять", callback_data=AdminAppCB(action="accept", user_id=query.from_user.id).pack())
    b.button(text="❌ Отклонить", callback_data=AdminAppCB(action="reject", user_id=query.from_user.id).pack())
    b.button(text="✍️ Указать недочеты", callback_data=AdminAppCB(action="flaws", user_id=query.from_user.id).pack())
    b.button(text="💬 Связаться", url=f"tg://user?id={query.from_user.id}")
    b.adjust(2, 1, 1)

    for admin_id in admins:
        try:
            await bot.send_message(admin_id, text_1, parse_mode="HTML")
            await bot.send_message(admin_id, text_2, parse_mode="HTML")
            await bot.send_message(admin_id, text_3, reply_markup=b.as_markup(), parse_mode="HTML")
        except:
            pass

    await state.clear()
    await query.message.edit_text(
        "✅ <b>Ваша анкета отправлена на рассмотрение!</b>\nОжидайте ответа, мы свяжемся с вами в ЛС.")
    await query.answer()


@dp.callback_query(AdminApplyForm.confirm, F.data == "a_ans_restart")
async def process_restart(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.delete()
    await start_admin_apply(query.message, state)
    await query.answer()


@dp.message(AdminApplyForm.q3)
@dp.message(AdminApplyForm.q4)
async def process_btn_states_text(message: types.Message):
    await message.answer("⚠️ Пожалуйста, выберите один из вариантов на кнопках выше.")