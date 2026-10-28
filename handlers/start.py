from aiogram import types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from callbacks import MenuCB, RegionCB, CharCB
from config import CREATOR_USERNAME
from db import get_user, update_user, is_character_taken, get_taken_characters, get_local_setting, get_application
from characters import REGIONS, get_character_image, CHARACTERS
from constants import DIV, PLACEHOLDER_IMAGES
from helpers import (
    esc, user_display_name, get_placeholder_image, _ensure_user,
    edit_or_send, get_section_image
)
from keyboards import (
    gender_kb, regions_kb, characters_kb, main_menu_kb,
)
from handlers.apply import ApplyForm
import state


def format_text(text: str, name: str, div: str) -> str:
    return text.replace("{name}", name).replace("{div}", div)


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject):
    await state.clear()
    chat_id = message.chat.id

    # --- ОБРАБОТКА ССЫЛКИ-ПРИГЛАШЕНИЯ ---
    if command.args and command.args.startswith("apply_"):
        target_chat_id = int(command.args.replace("apply_", ""))

        # Проверяем, есть ли уже анкета
        app = await get_application(message.from_user.id, target_chat_id)
        if app:
            status = app['status']
            if status == 'pending':
                return await message.answer("⏳ Ваша анкета уже находится на рассмотрении у администратора.")
            elif status == 'rejected':
                return await message.answer(
                    "❌ Ваша предыдущая анкета была отклонена. Вы можете попробовать снова позже.")

        # Получаем список занятых персонажей в целевом чате
        taken = await get_taken_characters(target_chat_id)
        free_chars = [name for name in CHARACTERS.keys() if name not in taken]

        if not free_chars:
            return await message.answer("😔 К сожалению, в этой ролевой сейчас нет свободных ролей.")

        await state.update_data(target_chat_id=target_chat_id)
        await state.set_state(ApplyForm.choosing_char)

        b = InlineKeyboardBuilder()
        # Выводим первые 20 штук для удобства
        for ch in free_chars[:20]:
            b.button(text=ch, callback_data=f"apply_char_{ch}")
        b.adjust(2)

        await message.answer(
            f"🎭 <b>Выберите желаемую роль</b>\n{DIV}\n\n"
            f"Ниже представлены свободные персонажи в этой ролевой. Выберите того, за кого хотите играть.",
            reply_markup=b.as_markup(), parse_mode="HTML"
        )
        return
    # --------------------------------------

    try:
        await message.delete()
    except Exception:
        pass

    if chat_id in state._last_bot_msg:
        try:
            await bot.delete_message(chat_id, state._last_bot_msg[chat_id])
        except Exception:
            pass

    user = await _ensure_user(message.from_user.id, chat_id)

    if not user["gender"]:
        default_text = (
            f"✨ ДОБРО ПОЖАЛОВАТЬ В ТЕЙВАТ\n{{div}}\n\n"
            f"Я — Орион, твой верный\n"
            f"спутник в этом мире 🧭\n\n"
            f"🌸 Мой создатель — {CREATOR_USERNAME}\n"
            f"Без него я бы не существовал!\n\n"
            f"{{div}}\n\n"
            f"Прежде чем мы отправимся\n"
            f"в путь, скажи:"
        )
        raw_text = await get_local_setting("text_start", chat_id, default_text)
        text = format_text(raw_text, "", DIV)

        img = await get_section_image("menu")
        try:
            msg = await message.answer_photo(
                FSInputFile(img) if img in PLACEHOLDER_IMAGES else img,
                caption=text,
                reply_markup=gender_kb(message.from_user.id),
                parse_mode="HTML"
            )
            state._last_bot_msg[chat_id] = msg.message_id
        except Exception:
            msg = await message.answer(
                text,
                reply_markup=gender_kb(message.from_user.id),
                parse_mode="HTML"
            )
            state._last_bot_msg[chat_id] = msg.message_id
        return

    if not user["character_name"] or user.get("char_change_paid") == 1:
        text = (
            f"🌸 ВЫБОР ПЕРСОНАЖА\n{DIV}\n\n"
            f"Рад снова тебя видеть,\n"
            f"Путешественник!\n\n"
            f"Пришло время выбрать, кем\n"
            f"ты будешь в этом мире 🎭\n\n"
            f"{DIV}\n\n"
            f"Выбери регион:"
        )
        img = await get_section_image("menu")
        try:
            msg = await message.answer_photo(
                FSInputFile(img) if img in PLACEHOLDER_IMAGES else img,
                caption=text,
                reply_markup=regions_kb(message.from_user.id),
                parse_mode="HTML"
            )
            state._last_bot_msg[chat_id] = msg.message_id
        except Exception:
            msg = await message.answer(
                text,
                reply_markup=regions_kb(message.from_user.id),
                parse_mode="HTML"
            )
            state._last_bot_msg[chat_id] = msg.message_id
        return

    name = esc(user_display_name(user))
    default_menu = (
        f"🌟 ГЛАВНОЕ МЕНЮ\n{{div}}\n\n"
        f"Привет, {{name}}!\n"
        f"Куда отправимся сегодня?\n\n"
        f"{{div}}\n\n"
        f"🧭 Меня создал {CREATOR_USERNAME}"
    )
    raw_menu = await get_local_setting("text_menu", chat_id, default_menu)
    text = format_text(raw_menu, name, DIV)

    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    image = await get_section_image("menu", fallback)

    try:
        if image in PLACEHOLDER_IMAGES:
            msg = await message.answer_photo(
                FSInputFile(image),
                caption=text,
                reply_markup=main_menu_kb(message.from_user.id),
                parse_mode="HTML"
            )
        else:
            msg = await message.answer_photo(
                image,
                caption=text,
                reply_markup=main_menu_kb(message.from_user.id),
                parse_mode="HTML"
            )
        state._last_bot_msg[chat_id] = msg.message_id
    except Exception:
        msg = await message.answer(
            text,
            reply_markup=main_menu_kb(message.from_user.id),
            parse_mode="HTML"
        )
        state._last_bot_msg[chat_id] = msg.message_id


@dp.callback_query(MenuCB.filter(F.action.in_(["gender_male", "gender_female"])))
async def cb_gender(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    g = "male" if callback_data.action == "gender_male" else "female"
    await update_user(query.from_user.id, chat_id, gender=g)
    text = f"💖 ОТЛИЧНО!\n{DIV}\n\nТеперь выбери регион,\nоткуда родом твой герой 🎭"
    await edit_or_send(query, text, regions_kb(query.from_user.id))


@dp.callback_query(MenuCB.filter(F.action == "regions"))
async def cb_regions(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    text = f"🌍 ВЫБОР РЕГИОНА\n{DIV}\n\nВыбери регион, Путешественник:"
    await edit_or_send(query, text, regions_kb(query.from_user.id))


@dp.callback_query(RegionCB.filter())
async def cb_region(query: types.CallbackQuery, callback_data: RegionCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    taken = await get_taken_characters(chat_id)
    region_name = REGIONS[callback_data.region]
    text = f"🎭 ГЕРОИ РЕГИОНА {region_name}\n{DIV}\n\nВыбери того, кто станет\nтвоим воплощением ✨"
    await edit_or_send(query, text, characters_kb(query.from_user.id, callback_data.region, taken))


@dp.callback_query(CharCB.filter())
async def cb_character(query: types.CallbackQuery, callback_data: CharCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    user = await get_user(query.from_user.id, chat_id)
    name = callback_data.character

    if user["character_name"] and not user["char_change_paid"]:
        await query.answer("❌ У тебя уже есть персонаж. Смену можно купить в Лавке!", show_alert=True)
        return
    if await is_character_taken(name, chat_id):
        await query.answer(f"❌ {name} уже занят.", show_alert=True)
        return

    await update_user(query.from_user.id, chat_id, character_name=name, char_change_paid=0)
    chat = query.message.chat
    ts = ""
    if chat.type in ("group", "supergroup"):
        try:
            await bot.promote_chat_member(chat_id=chat.id, user_id=query.from_user.id,
                                          can_change_info=False, can_delete_messages=False, can_invite_users=False,
                                          can_restrict_members=False, can_pin_messages=False, can_promote_members=False,
                                          can_manage_chat=False, can_manage_video_chats=True)
            await bot.set_chat_administrator_custom_title(
                chat_id=chat.id, user_id=query.from_user.id, custom_title=name[:16])
            ts = "\n\n👑 Титул установлен!"
        except Exception:
            ts = ""

    text = f"🎉 ДОБРО ПОЖАЛОВАТЬ!\n{DIV}\n\nТеперь ты — {esc(name)}!{ts}\n\n{DIV}\n\nОрион рад за тебя! 💛"

    try:
        await query.message.delete()
    except Exception:
        pass

    char_image = get_character_image(name)

    try:
        if char_image in PLACEHOLDER_IMAGES:
            msg = await bot.send_photo(
                chat_id=chat.id,
                photo=FSInputFile(char_image),
                caption=text,
                reply_markup=main_menu_kb(query.from_user.id),
                parse_mode="HTML"
            )
        else:
            msg = await bot.send_photo(
                chat_id=chat.id,
                photo=char_image,
                caption=text,
                reply_markup=main_menu_kb(query.from_user.id),
                parse_mode="HTML"
            )
        state._last_bot_msg[chat.id] = msg.message_id
    except Exception:
        msg = await bot.send_photo(
            chat_id=chat.id,
            photo=FSInputFile(get_placeholder_image()),
            caption=text,
            reply_markup=main_menu_kb(query.from_user.id),
            parse_mode="HTML"
        )
        state._last_bot_msg[chat.id] = msg.message_id