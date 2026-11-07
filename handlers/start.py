import time
from aiogram import types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from callbacks import MenuCB, RegionCB, CharCB
from config import CREATOR_USERNAME
from db import get_user, update_user, is_character_taken, get_taken_characters, get_local_setting, get_application, \
    update_application_status, fetch_all
from characters import REGIONS, get_character_image, CHARACTERS
from constants import DIV, PLACEHOLDER_IMAGES
from helpers import (
    esc, user_display_name, get_placeholder_image, _ensure_user,
    edit_or_send, get_section_image
)
from keyboards import (
    gender_kb, regions_kb, characters_kb, main_menu_kb,
)
from handlers.apply import ApplyForm, FORM_STEPS, send_step
from handlers.chat_list import update_chat_list
import state as bot_state


def format_text(text: str, name: str, div: str) -> str:
    return text.replace("{name}", name).replace("{div}", div)


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject):
    current_state = await state.get_state()

    # 1. Продолжение заполнения анкеты (если пользователь уже начал)
    if current_state and current_state.startswith("ApplyForm"):
        data = await state.get_data()
        old_target_chat_id = data.get("target_chat_id")

        if command.args and command.args.startswith("apply_"):
            new_target_chat_id = int(command.args.replace("apply_", ""))
            if old_target_chat_id == new_target_chat_id:
                idx = next((i for i, (st, _) in enumerate(FORM_STEPS) if st.state == current_state), 0)
                await send_step(message.chat.id, idx, state)
                return

        await message.answer("⚠️ Предыдущая анкета отменена.")
        await state.clear()
    else:
        await state.clear()

    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)

    # 2. Обработка перехода по ссылке на анкету
    if command.args and command.args.startswith("apply_"):
        target_chat_id = int(command.args.replace("apply_", ""))

        group_user = await get_user(message.from_user.id, target_chat_id)
        if group_user and group_user["character_name"]:
            try:
                expire_date = int(time.time()) + 86400
                link = await bot.create_chat_invite_link(target_chat_id, member_limit=1, expire_date=expire_date)
                await message.answer(
                    f"✅ Вы уже зарегистрированы в этой ролевой как <b>{esc(group_user['character_name'])}</b>!\n\n"
                    f"🔗 <b>Ваша ссылка для вступления в группу:</b>\n{link.invite_link}\n\n"
                    f"<i>Если вы хотите сменить персонажа, зайдите в группу и напишите /freerole</i>",
                    parse_mode="HTML"
                )
                return
            except Exception as e:
                await message.answer(f"❌ Ошибка создания ссылки: {e}")
                return

        app = await get_application(message.from_user.id, target_chat_id)
        if app:
            status = app['status']
            if status in ('pending', 'waiting_char'):
                return await message.answer("⏳ Ваша анкета уже на рассмотрении или одобрена. Ожидайте.")
            elif status == 'rejected':
                pass

        await state.update_data(target_chat_id=target_chat_id)
        await send_step(message.chat.id, 0, state)
        return

    # =======================================================
    # 3. БЛОКИРОВКА ВСЕГО, КРОМЕ АНКЕТ, В ЛИЧНЫХ СООБЩЕНИЯХ
    # =======================================================
    if message.chat.type == "private":
        # Проверяем, есть ли одобренная анкета
        if not user["character_name"]:
            apps = await fetch_all(
                "SELECT chat_id, status FROM applications WHERE user_id = ? AND status IN ('accepted', 'waiting_char')",
                (message.from_user.id,))
            if apps:
                target_chat_id = apps[0]["chat_id"]
                if apps[0]["status"] == 'accepted':
                    await update_application_status(message.from_user.id, target_chat_id, 'waiting_char')

                try:
                    expire_date = int(time.time()) + 86400
                    link = await bot.create_chat_invite_link(target_chat_id, member_limit=1, expire_date=expire_date)
                    await message.answer(
                        f"🎉 <b>Ваша анкета одобрена!</b>\n\n"
                        f"Пожалуйста, перейдите в группу по ссылке ниже. Клавиатура с выбором региона появится автоматически при входе в чат:\n\n"
                        f"🔗 {link.invite_link}",
                        parse_mode="HTML"
                    )
                except Exception:
                    await message.answer(
                        "🎉 <b>Ваша анкета одобрена!</b>\n\nПожалуйста, перейдите в группу и нажмите там кнопку выбора персонажа.",
                        parse_mode="HTML")
            else:
                await message.answer(
                    f"── 〔 🌸 ДОБРО ПОЖАЛОВАТЬ 〕 ──\n\n"
                    f"╭ Я — Орион, твой верный спутник.\n"
                    f"├\n"
                    f"├ Заполнение анкет и игра проходят <b>только в группе</b>.\n"
                    f"├\n"
                    f"╰ Пожалуйста, вернись в группу и напиши /start там."
                )
        else:
            await message.answer(
                f"── 〔 🌟 ПРИВЕТ 〕 ──\n\n"
                f"╭ Ты уже зарегистрирован как <b>{esc(user['character_name'])}</b>.\n"
                f"╰ Все игровые меню доступны <b>только в группе</b>."
            )
        return  # Выходим, чтобы в ЛС не показывалось ничего лишнего
    # =======================================================

    # =======================================================
    # 4. ЛОГИКА ДЛЯ ГРУППЫ (ВЫБОР ПОЛА И ПЕРСОНАЖА)
    # =======================================================
    if not user["character_name"]:
        apps = await fetch_all("SELECT chat_id FROM applications WHERE user_id = ? AND status = 'accepted'",
                               (message.from_user.id,))
        if apps:
            target_chat_id = apps[0]["chat_id"]
            await update_application_status(message.from_user.id, target_chat_id, 'waiting_char')
            await message.answer("🎉 Ваша анкета одобрена!\nПожалуйста, выбери регион, откуда твой персонаж:",
                                 reply_markup=regions_kb(message.from_user.id))
            return

    try:
        await message.delete()
    except Exception:
        pass

    if chat_id in bot_state._last_bot_msg:
        try:
            await bot.delete_message(chat_id, bot_state._last_bot_msg[chat_id])
        except Exception:
            pass

    if not user["character_name"] or user.get("char_change_paid") == 1:
        if not user["gender"]:
            default_text = (
                f"── 〔 ✨ ПРИВЕТСТВИЕ 〕 ──\n\n"
                f"╭ Я — Орион, твой верный\n"
                f"├ спутник в этом мире 🧭\n"
                f"├\n"
                f"├ 🌸 Мой создатель — {CREATOR_USERNAME}\n"
                f"├ Без него я бы не существовал!\n"
                f"├\n"
                f"╰ Прежде чем мы отправимся в путь, скажи:"
            )
            raw_text = await get_local_setting("text_start", chat_id, default_text)
            text = format_text(raw_text, "", DIV)

            image = await get_section_image("start", chat_id=chat_id)

            if image:
                msg = await message.answer_photo(image, caption=text, reply_markup=gender_kb(message.from_user.id),
                                                 parse_mode="HTML")
            else:
                msg = await message.answer(text, reply_markup=gender_kb(message.from_user.id), parse_mode="HTML")
            bot_state._last_bot_msg[chat_id] = msg.message_id
            return

        text = (
            f"── 〔 🌸 ВЫБОР ПЕРСОНАЖА 〕 ──\n\n"
            f"╭ Рад снова тебя видеть,\n"
            f"├ Путешественник!\n"
            f"├\n"
            f"├ Пришло время выбрать, кем\n"
            f"├ ты будешь в этом мире 🎭\n"
            f"├\n"
            f"╰ Выбери регион:"
        )
        image = await get_section_image("regions", chat_id=chat_id)

        if image:
            msg = await message.answer_photo(image, caption=text, reply_markup=regions_kb(message.from_user.id),
                                             parse_mode="HTML")
        else:
            msg = await message.answer(text, reply_markup=regions_kb(message.from_user.id), parse_mode="HTML")
        bot_state._last_bot_msg[chat_id] = msg.message_id
        return

    name = esc(user_display_name(user))
    default_menu = (
        f"── 〔 🌟 ГЛАВНОЕ МЕНЮ 〕 ──\n\n"
        f"╭ 🍃 Привет, <b>{{name}}</b>!\n"
        f"├\n"
        f"├ Куда отправимся сегодня?\n"
        f"├\n"
        f"╰ 🧭 Меня создал {CREATOR_USERNAME}"
    )
    raw_menu = await get_local_setting("text_menu", chat_id, default_menu)
    text = format_text(raw_menu, name, DIV)

    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    image = await get_section_image("menu", fallback, chat_id)

    if image:
        msg = await message.answer_photo(image, caption=text, reply_markup=main_menu_kb(message.from_user.id),
                                         parse_mode="HTML")
    else:
        msg = await message.answer(text, reply_markup=main_menu_kb(message.from_user.id), parse_mode="HTML")
    bot_state._last_bot_msg[chat_id] = msg.message_id


@dp.callback_query(MenuCB.filter(F.action.in_(["gender_male", "gender_female"])))
async def cb_gender(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    g = "male" if callback_data.action == "gender_male" else "female"
    await update_user(query.from_user.id, chat_id, gender=g)

    user = await get_user(query.from_user.id, chat_id)

    if user and user.get("character_name"):
        text = f"── 〔 💖 ОТЛИЧНО! 〕 ──\n\n╭ Пол успешно обновлен.\n╰ Твой персонаж: <b>{esc(user['character_name'])}</b>"
        fallback = get_character_image(user["character_name"]) if user["character_name"] else None
        image = await get_section_image("menu", fallback, chat_id)
        await edit_or_send(query, text, main_menu_kb(query.from_user.id), image_url=image)
    else:
        text = f"── 〔 💖 ОТЛИЧНО! 〕 ──\n\n╭ Теперь выбери регион,\n╰ откуда родом твой герой 🎭"
        image = await get_section_image("regions", chat_id=chat_id)
        await edit_or_send(query, text, regions_kb(query.from_user.id), image_url=image)


@dp.callback_query(MenuCB.filter(F.action == "regions"))
async def cb_regions(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    text = f"── 〔 🌍 ВЫБОР РЕГИОНА 〕 ──\n\n╭ Выбери регион,\n╰ Путешественник:"
    image = await get_section_image("regions", chat_id=query.message.chat.id)
    await edit_or_send(query, text, regions_kb(query.from_user.id), image_url=image)


@dp.callback_query(RegionCB.filter())
async def cb_region(query: types.CallbackQuery, callback_data: RegionCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    taken = await get_taken_characters(chat_id)
    region_name = REGIONS[callback_data.region]
    text = f"── 〔 🎭 РЕГИОН: {region_name.upper()} 〕 ──\n\n╭ Выбери того, кто станет\n╰ твоим воплощением ✨"

    image = await get_section_image(f"region_{callback_data.region}", chat_id=chat_id)
    if not image:
        image = await get_section_image("regions", chat_id=chat_id)

    await edit_or_send(query, text, characters_kb(query.from_user.id, callback_data.region, taken), image_url=image)


@dp.callback_query(CharCB.filter())
async def cb_character(query: types.CallbackQuery, callback_data: CharCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return

    chat_id = query.message.chat.id

    # Запрет на выбор персонажа в ЛС (на всякий случай)
    if query.message.chat.type == "private":
        await query.answer("❌ Выбор персонажа доступен только в группе!", show_alert=True)
        return

    user = await get_user(query.from_user.id, chat_id)
    name = callback_data.character

    if user["character_name"] and not user["char_change_paid"]:
        await query.answer("❌ У тебя уже есть персонаж. Смену можно купить в Лавке!", show_alert=True)
        return
    if await is_character_taken(name, chat_id):
        await query.answer(f"❌ {name} уже занят.", show_alert=True)
        return

    await update_user(query.from_user.id, chat_id, character_name=name, char_change_paid=0)
    await update_chat_list(chat_id)

    # =======================================================
    # ВЫДАЧА ТЕГА УЧАСТНИКА (БЕЗ ВЫДАЧИ АДМИНКИ)
    # =======================================================
    chat = query.message.chat
    ts = ""

    try:
        bot_member = await bot.get_chat_member(chat.id, bot.id)

        # Проверяем, что у бота есть право управлять тегами
        if not getattr(bot_member, "can_manage_tags", False):
            ts = "\n\n⚠️ <b>Ошибка:</b> У бота нет права «Управление тегами» в настройках группы."
        else:
            # ВАЖНО: Используется ТОЛЬКО set_chat_member_tag. Метод promote_chat_member удален.
            await bot.set_chat_member_tag(
                chat_id=chat.id,
                user_id=query.from_user.id,
                tag=name[:16]
            )
            ts = "\n\n🏷️ Тег участника установлен!"
    except Exception as e:
        print(f"Ошибка выдачи тега: {e}")
        ts = f"\n\n⚠️ Не удалось установить тег (возможно, устарела версия aiogram)."

    # =======================================================
    # ПРОВЕРКА АНКЕТЫ И ПУБЛИКАЦИЯ
    # =======================================================
    app = await get_application(query.from_user.id, chat_id)
    if app and app['status'] == 'waiting_char':
        await update_application_status(query.from_user.id, chat_id, 'joined')
        text = (
            f"🎉 <b>У нас новенький! Встречайте!</b>\n\n"
            f"🎭 <b>Роль:</b> {esc(name)}\n\n"
            f"📖 <b>Опыт:</b> {esc(app['experience'])}\n"
            f"🌟 <b>О себе:</b> {esc(app['about'])}\n"
            f"🕒 <b>Часовой пояс:</b> {esc(app['timezone'])}\n"
            f"⚠️ <b>Триггеры:</b> {esc(app['triggers'])}\n"
            f"⚡ <b>Активность:</b> {esc(app['activity'])}"
        )
        await bot.send_message(chat_id, text, parse_mode="HTML")
        try:
            await query.message.delete()
        except:
            pass

        await bot.send_message(chat_id, f"✅ Анкета опубликована! Добро пожаловать в игру, {esc(name)}!{ts}",
                               reply_markup=main_menu_kb(query.from_user.id), parse_mode="HTML")
        return

    # =======================================================
    # ОБЫЧНОЕ ПРИВЕТСТВИЕ
    # =======================================================
    text = f"── 〔 🎉 ДОБРО ПОЖАЛОВАТЬ! 〕 ──\n\n╭ Теперь ты — <b>{esc(name)}</b>!{ts}\n├\n╰ Орион рад за тебя! 💛"

    try:
        await query.message.delete()
    except Exception:
        pass

    char_image = get_character_image(name)

    if char_image:
        try:
            msg = await bot.send_photo(chat.id, photo=char_image, caption=text,
                                       reply_markup=main_menu_kb(query.from_user.id), parse_mode="HTML")
        except:
            msg = await bot.send_message(chat.id, text=text, reply_markup=main_menu_kb(query.from_user.id),
                                         parse_mode="HTML")
    else:
        msg = await bot.send_message(chat.id, text=text, reply_markup=main_menu_kb(query.from_user.id),
                                     parse_mode="HTML")

    bot_state._last_bot_msg[chat.id] = msg.message_id


@dp.message(Command("freerole"))
async def cmd_freerole(message):
    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)
    if not user["character_name"]: return await message.answer("У тебя нет персонажа.")
    old = user["character_name"]
    await update_user(message.from_user.id, chat_id, character_name="")
    await message.answer(f"✅ Роль «{esc(old)}» освобождена.\n\n⚠️ Вернуть можно за 25000 монет.", parse_mode="HTML")
    await update_chat_list(chat_id)