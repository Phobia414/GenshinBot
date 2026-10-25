from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile

from bot_instance import bot, dp
from callbacks import MenuCB, RegionCB, CharCB
from config import CREATOR_USERNAME
from db import get_user, update_user, is_character_taken, get_taken_characters
from characters import REGIONS
from constants import DIV, PLACEHOLDER_IMAGES
from helpers import (
    esc, user_display_name, get_placeholder_image, _ensure_user,
    edit_or_send,
)
from keyboards import (
    gender_kb, regions_kb, characters_kb, main_menu_kb,
)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await _ensure_user(message.from_user.id)
    if not user["gender"]:
        text = (
            f"✨ ДОБРО ПОЖАЛОВАТЬ В ТЕЙВАТ\n{DIV}\n\n"
            f"Я — Орион, твой верный\n"
            f"спутник в этом мире 🧭\n\n"
            f"🌸 Мой создатель — {CREATOR_USERNAME}\n"
            f"Без него я бы не существовал!\n\n"
            f"{DIV}\n\n"
            f"Прежде чем мы отправимся\n"
            f"в путь, скажи:"
        )
        img = get_placeholder_image()
        try:
            await message.answer_photo(FSInputFile(img), caption=text,
                                       reply_markup=gender_kb(message.from_user.id), parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=gender_kb(message.from_user.id), parse_mode="HTML")
        return
    if not user["character_name"]:
        text = (
            f"🌸 ВЫБОР ПЕРСОНАЖА\n{DIV}\n\n"
            f"Рад снова тебя видеть,\n"
            f"Путешественник!\n\n"
            f"Пришло время выбрать, кем\n"
            f"ты будешь в этом мире 🎭\n\n"
            f"{DIV}\n\n"
            f"Выбери регион:"
        )
        img = get_placeholder_image()
        try:
            await message.answer_photo(FSInputFile(img), caption=text,
                                       reply_markup=regions_kb(message.from_user.id), parse_mode="HTML")
        except Exception:
            await message.answer(text, reply_markup=regions_kb(message.from_user.id), parse_mode="HTML")
        return
    name = esc(user_display_name(user))
    text = (
        f"🌟 ГЛАВНОЕ МЕНЮ\n{DIV}\n\n"
        f"Привет, {name}!\n"
        f"Куда отправимся сегодня?\n\n"
        f"{DIV}\n\n"
        f"🧭 Меня создал {CREATOR_USERNAME}"
    )
    img = get_placeholder_image()
    try:
        await message.answer_photo(FSInputFile(img), caption=text,
                                   reply_markup=main_menu_kb(message.from_user.id), parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=main_menu_kb(message.from_user.id), parse_mode="HTML")


@dp.callback_query(MenuCB.filter(F.action.in_(["gender_male", "gender_female"])))
async def cb_gender(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    g = "male" if callback_data.action == "gender_male" else "female"
    await update_user(query.from_user.id, gender=g)
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
    taken = await get_taken_characters()
    region_name = REGIONS[callback_data.region]
    text = f"🎭 ГЕРОИ РЕГИОНА {region_name}\n{DIV}\n\nВыбери того, кто станет\nтвоим воплощением ✨"
    await edit_or_send(query, text, characters_kb(query.from_user.id, callback_data.region, taken))


@dp.callback_query(CharCB.filter())
async def cb_character(query: types.CallbackQuery, callback_data: CharCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    name = callback_data.character
    if user["character_name"] and not user["char_change_paid"]:
        await query.answer("❌ У тебя уже есть персонаж. Смену можно купить в Лавке!", show_alert=True)
        return
    if await is_character_taken(name):
        await query.answer(f"❌ {name} уже занят.", show_alert=True)
        return
    await update_user(query.from_user.id, character_name=name, char_change_paid=0)
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
    await edit_or_send(query, text, main_menu_kb(query.from_user.id))