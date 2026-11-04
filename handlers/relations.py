from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot_instance import bot, dp
from callbacks import MenuCB, RelCB, GiftCB, ProposeCB
from config import OWNER_ID, PROPOSE_COOLDOWN
from constants import (
    DIV, GIFTS, XP_PER_LEVEL, MAX_LEVEL, WEDDING_LEVEL,
)
from db import (
    get_user, update_user, get_protected_owner, get_local_setting
)
from helpers import (
    esc, user_display_name, edit_or_send, _ensure_user,
    extract_target, resolve_user_id, _now_ts, get_section_image, inject_user
)
from keyboards import relations_kb, gifts_kb, back_kb
from state import _propose_cooldown


class RelationsEdit(StatesGroup):
    waiting_for_image = State()


@dp.callback_query(MenuCB.filter(F.action == "relations"))
@inject_user
async def cb_relations(query: types.CallbackQuery, callback_data: MenuCB, user: dict, chat_id: int, state: FSMContext):
    await state.clear()
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    name = esc(user_display_name(user))

    if user["partner_id"]:
        level = min(user["rel_xp"] // XP_PER_LEVEL, MAX_LEVEL)
        married = bool(user["is_married"])
        status = "💍 В браке" if married else "💕 В отношениях"
        started = (datetime.fromtimestamp(user["rel_started"], timezone.utc).strftime("%d.%m.%Y") if user["rel_started"] else "?")
        extra = ""
        if married and user["married_at"]:
            extra += f"\n├ 💒 Свадьба: {datetime.fromtimestamp(user['married_at'], timezone.utc).strftime('%d.%m.%Y')}"
        if user["child_id"]:
            extra += f"\n├ 👶 Ребёнок: {esc(user['child_name'])}"

        default_text = (
            f"─ [ ❤️ ОТНОШЕНИЯ ] ─\n\n"
            f"╭ 💕 {{name}} + {{partner_name}}\n"
            f"┆\n"
            f"├ 📅 Вместе с: {{rel_started}}\n"
            f"├ 📊 Уровень: {{rel_level}} / {{max_level}}\n"
            f"├ ✨ Опыт: {{rel_xp}} XP\n"
            f"├ 💍 Статус: {{rel_status}}{{extra}}\n"
            f"╰"
        )
        raw_text = await get_local_setting("text_relations", chat_id, default_text)
        text = raw_text.replace("{name}", name).replace("{partner_name}", esc(user['partner_name'])).replace("{rel_started}", started).replace("{rel_level}", str(level)).replace("{max_level}", str(MAX_LEVEL)).replace("{rel_xp}", str(user['rel_xp'])).replace("{rel_status}", status).replace("{extra}", extra).replace("{div}", DIV)
        kb = relations_kb(query.from_user.id, True, married, level >= WEDDING_LEVEL, bool(user["child_id"]), user["gender"])
    else:
        default_text = (
            f"─ [ ❤️ ОТНОШЕНИЯ ] ─\n\n"
            f"╭ 🍃 {{name}}, твоё сердце\n"
            f"├ свободно 💌\n"
            f"┆\n"
            f"├ Ответь на сообщение игрока\n"
            f"├ и напиши /propose\n"
            f"┆\n"
            f"╰ или укажи @username: /propose @user"
        )
        raw_text = await get_local_setting("text_relations", chat_id, default_text)
        text = raw_text.replace("{name}", name).replace("{div}", DIV)
        kb = relations_kb(query.from_user.id, False, False, False, False, user["gender"])

    custom_img = await get_local_setting("image_relations", chat_id)
    await edit_or_send(query, text, kb, image_url=custom_img or "")


@dp.callback_query(RelCB.filter(F.action == "gifts"))
@inject_user
async def cb_gifts(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return
    text = f"─ [ 🎁 ПОДАРКИ ] ─\n\n╭ Для: {esc(user['partner_name'])}\n├\n╰ 💰 Баланс: {user['balance']}"
    await edit_or_send(query, text, gifts_kb(query.from_user.id), image_url="")