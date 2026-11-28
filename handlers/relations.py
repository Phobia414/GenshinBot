from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot_instance import bot, dp
from callbacks import MenuCB, RelCB, GiftCB, ProposeCB, ConfirmCB
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
    if state:  # <--- ДОБАВЛЕНА ПРОВЕРКА
        await state.clear()

    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    name = esc(user_display_name(user))

    if user["partner_id"]:
        level = min(user["rel_xp"] // XP_PER_LEVEL, MAX_LEVEL)
        married = bool(user["is_married"])
        status = "💍 В браке" if married else "💕 В отношениях"
        started = (datetime.fromtimestamp(user["rel_started"], timezone.utc).strftime("%d.%m.%Y") if user[
            "rel_started"] else "?")
        extra = ""
        if married and user["married_at"]:
            extra += f"\n📅 Свадьба: {datetime.fromtimestamp(user['married_at'], timezone.utc).strftime('%d.%m.%Y')}"

        # Считаем количество детей
        child_count = 0
        if user["child_id"]:
            child_count = len([i for i in str(user["child_id"]).split(",") if i and i != "0"])

        if child_count > 0:
            extra += f"\n👶 Дети: {esc(user['child_name'])}"

        default_text = (
            f"— [ ❤️ ОТНОШЕНИЯ ] —\n\n"
            f"💕 {name} + {esc(user['partner_name'])}\n\n"
            f"📅 Вместе с: {started}\n"
            f"📊 Уровень: {level} / {MAX_LEVEL}\n"
            f"✨ Опыт: {user['rel_xp']} XP\n"
            f"💍 Статус: {status}{extra}"
        )
        raw_text = await get_local_setting("text_relations", chat_id, default_text)
        text = raw_text.replace("{name}", name).replace("{partner_name}", esc(user['partner_name'])).replace(
            "{rel_started}", started).replace("{rel_level}", str(level)).replace("{max_level}", str(MAX_LEVEL)).replace(
            "{rel_xp}", str(user['rel_xp'])).replace("{rel_status}", status).replace("{extra}", extra).replace("{div}",
                                                                                                               DIV)

        # Передаем child_count вместо bool(user["child_id"])
        kb = relations_kb(query.from_user.id, True, married, level >= WEDDING_LEVEL, child_count, user["gender"])
    else:
        default_text = (
            f"— [ ❤️ ОТНОШЕНИЯ ] —\n\n"
            f"🍃 {name}, твоё сердце свободно 💌\n\n"
            f"Ответь на сообщение игрока\n"
            f"и напиши /propose\n\n"
            f"или укажи @username: /propose @user"
        )
        raw_text = await get_local_setting("text_relations", chat_id, default_text)
        text = raw_text.replace("{name}", name).replace("{div}", DIV)
        kb = relations_kb(query.from_user.id, False, False, False, False, user["gender"])

    custom_img = await get_local_setting("image_relations", chat_id)
    img = user.get("rel_image") or custom_img
    await edit_or_send(query, text, kb, image_url=img or "")


# ==================== СОЗДАНИЕ ОТНОШЕНИЙ (/propose) ====================

@dp.message(Command("propose"))
async def cmd_propose(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Предложить отношения можно только в группе.")
        return

    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)

    if user["partner_id"]:
        await message.answer("❌ У тебя уже есть партнёр.")
        return
    if not user["character_name"]:
        await message.answer("❌ Сначала выбери персонажа.")
        return

    target_ref, display = extract_target(message)
    if target_ref is None:
        await message.answer("Ответь на сообщение игрока и напиши /propose\n(или укажи @username)")
        return

    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            await message.answer(f"❌ Не нашёл @{target_ref}.")
            return
    else:
        target_id = target_ref

    if target_id == message.from_user.id:
        await message.answer("❌ Себе предложить нельзя.")
        return

    target = await _ensure_user(target_id, chat_id)
    if not target["character_name"]:
        await message.answer("❌ Этот игрок ещё не выбрал персонажа.")
        return
    if target["partner_id"]:
        await message.answer("❌ У этого игрока уже есть партнёр.")
        return

    protector = await get_protected_owner(target_id, chat_id)
    if protector and protector != message.from_user.id:
        await message.answer("🛡 Этот игрок находится под защитой. Вы не можете предложить ему отношения.")
        return

    if message.from_user.id != OWNER_ID:
        key = (message.from_user.id, target_id, chat_id)
        now_ts = _now_ts()
        last = _propose_cooldown.get(key, 0)
        if now_ts - last < PROPOSE_COOLDOWN:
            left = int(PROPOSE_COOLDOWN - (now_ts - last))
            await message.answer(f"⏳ Подожди {left} сек. перед повторным предложением.")
            return
        _propose_cooldown[key] = now_ts

    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять",
             callback_data=ProposeCB(action="accept", proposer_id=message.from_user.id, target_id=target_id))
    b.button(text="❌ Отклонить",
             callback_data=ProposeCB(action="decline", proposer_id=message.from_user.id, target_id=target_id))
    b.adjust(2)

    mention = f'<a href="tg://user?id={target_id}">{esc(target["character_name"])}</a>'
    proposer = f'<a href="tg://user?id={message.from_user.id}">{esc(user["character_name"])}</a>'

    await message.answer(
        f"— [ 💌 ПРЕДЛОЖЕНИЕ ] —\n\n"
        f"{mention}, игрок {proposer} предлагает тебе встречаться! 💕",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@dp.callback_query(ProposeCB.filter())
async def cb_propose(query: types.CallbackQuery, callback_data: ProposeCB):
    if query.from_user.id != callback_data.target_id:
        await query.answer("❌ Это предложение не для тебя!", show_alert=True)
        return

    chat_id = query.message.chat.id

    if callback_data.action == "decline":
        await query.message.edit_text("— [ 🕊️ ОТКЛОНЕНО ] —\n\nПредложение отклонено.", parse_mode="HTML")
        return

    proposer = await get_user(callback_data.proposer_id, chat_id)
    target = await get_user(callback_data.target_id, chat_id)

    if not proposer or not target:
        await query.answer("❌ Ошибка данных.", show_alert=True)
        return
    if proposer["partner_id"] or target["partner_id"]:
        await query.answer("❌ Кто-то из вас уже в отношениях.", show_alert=True)
        return

    now = int(datetime.now(timezone.utc).timestamp())

    await update_user(callback_data.proposer_id, chat_id, partner_id=callback_data.target_id,
                      partner_name=target["character_name"], rel_xp=0, rel_started=now, is_married=0)
    await update_user(callback_data.target_id, chat_id, partner_id=callback_data.proposer_id,
                      partner_name=proposer["character_name"], rel_xp=0, rel_started=now, is_married=0)

    await query.message.edit_text(
        f"— [ 🎉 УРА! ] —\n\n"
        f"💕 {esc(proposer['character_name'])} и {esc(target['character_name'])} теперь вместе!",
        parse_mode="HTML"
    )


# ==================== СВАДЬБА, РАЗРЫВ И УСЫНОВЛЕНИЕ ====================

@dp.callback_query(RelCB.filter(F.action == "breakup"))
@inject_user
async def cb_breakup(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int):
    await query.answer()
    if query.from_user.id != callback_data.owner_id or not user["partner_id"]: return

    partner_id = user["partner_id"]
    await update_user(query.from_user.id, chat_id, partner_id=0, partner_name="", rel_xp=0, rel_started=0, is_married=0,
                      married_at=0, child_id=0, child_name="", rel_image="")
    await update_user(partner_id, chat_id, partner_id=0, partner_name="", rel_xp=0, rel_started=0, is_married=0,
                      married_at=0, child_id=0, child_name="", rel_image="")

    await edit_or_send(query, "💔 Отношения разорваны.", back_kb(query.from_user.id), image_url="")


@dp.callback_query(RelCB.filter(F.action == "marry"))
@inject_user
async def cb_marry(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int):
    await query.answer()
    if query.from_user.id != callback_data.owner_id or not user["partner_id"]: return

    now = int(datetime.now(timezone.utc).timestamp())
    await update_user(query.from_user.id, chat_id, is_married=1, married_at=now)
    await update_user(user["partner_id"], chat_id, is_married=1, married_at=now)

    await edit_or_send(query, "💍 Поздравляем со свадьбой!", back_kb(query.from_user.id), image_url="")


@dp.callback_query(RelCB.filter(F.action == "adopt_hint"))
async def cb_adopt_hint(query: types.CallbackQuery, callback_data: RelCB):
    await query.answer("Чтобы усыновить партнёра, ответь на его сообщение в чате и напиши 'усыновить' или 'удочерить'.",
                       show_alert=True)


@dp.callback_query(RelCB.filter(F.action == "remove_child"))
@inject_user
async def cb_remove_child_menu(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int):
    await query.answer()
    if query.from_user.id != callback_data.owner_id or not user["child_id"]: return

    current_ids = [i for i in str(user["child_id"]).split(",") if i and i != "0"]
    current_names = [n for n in str(user["child_name"]).split(",") if n]

    if not current_ids:
        await query.answer("У вас нет детей.", show_alert=True)
        return

    b = InlineKeyboardBuilder()
    # Выводим кнопку для каждого ребенка
    for cid, cname in zip(current_ids, current_names):
        b.button(text=f"👶 Отказаться от: {cname}", callback_data=f"delchild_{cid}")

    b.button(text="❌ Отмена", callback_data=MenuCB(action="relations", owner_id=query.from_user.id))
    b.adjust(1)

    await edit_or_send(
        query,
        f"— [ 🕊️ ОТКАЗ ] —\n\nВыбери, от какого ребенка ты хочешь отказаться:",
        b.as_markup(),
        image_url=""
    )


@dp.callback_query(F.data.startswith("delchild_"))
@inject_user
async def cb_remove_child_do(query: types.CallbackQuery, user: dict, chat_id: int, state: FSMContext):
    target_id = query.data.replace("delchild_", "")

    if not user["child_id"]: return

    current_ids = str(user["child_id"]).split(",")
    current_names = str(user["child_name"]).split(",")

    # Оставляем только тех детей, чей ID не совпадает с выбранным
    new_ids = [i for i in current_ids if i != target_id and i != "0"]
    new_names = [name for i, name in zip(current_ids, current_names) if i != target_id and i != "0"]

    new_id_str = ",".join(new_ids)
    new_name_str = ",".join(new_names)

    # Удаляем ребенка у себя
    await update_user(query.from_user.id, chat_id, child_id=new_id_str, child_name=new_name_str)

    # Удаляем ребенка у партнера (если он есть)
    if user["partner_id"]:
        await update_user(user["partner_id"], chat_id, child_id=new_id_str, child_name=new_name_str)

    await query.answer("✅ Вы отказались от ребенка.", show_alert=True)

    # Перезагружаем меню отношений с актуальными данными
    updated_user = await get_user(query.from_user.id, chat_id)
    await cb_relations(query, MenuCB(action="relations", owner_id=query.from_user.id), user=updated_user,
                       chat_id=chat_id, state=None)


# ==================== ФОТО ПАРЫ И ПОДАРКИ ====================

@dp.callback_query(RelCB.filter(F.action == "set_image"))
@inject_user
async def cb_set_rel_image(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int,
                           state: FSMContext):
    await query.answer()
    if query.from_user.id != callback_data.owner_id: return
    if not user["partner_id"]:
        await query.answer("❌ У тебя нет партнёра.", show_alert=True)
        return

    await state.set_state(RelationsEdit.waiting_for_image)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data=MenuCB(action="relations", owner_id=query.from_user.id))

    await edit_or_send(query, "📸 **Отправь фотографию**, которая будет стоять в вашем меню отношений.", b.as_markup(),
                       image_url="")


@dp.message(RelationsEdit.waiting_for_image, F.photo)
async def process_rel_image(message: types.Message, state: FSMContext):
    user = await get_user(message.from_user.id, message.chat.id)
    if not user or not user["partner_id"]:
        await message.answer("❌ Ошибка: нет партнёра.")
        await state.clear()
        return

    file_id = message.photo[-1].file_id
    await update_user(message.from_user.id, message.chat.id, rel_image=file_id)
    await update_user(user["partner_id"], message.chat.id, rel_image=file_id)

    await state.clear()
    b = InlineKeyboardBuilder()
    b.button(text="❤️ К отношениям", callback_data=MenuCB(action="relations", owner_id=message.from_user.id))
    await message.answer("✅ Фото пары успешно обновлено!", reply_markup=b.as_markup())


@dp.callback_query(RelCB.filter(F.action == "gifts"))
@inject_user
async def cb_gifts(query: types.CallbackQuery, callback_data: RelCB, user: dict, chat_id: int):
    await query.answer()
    if query.from_user.id != callback_data.owner_id: return
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return

    text = f"— [ 🎁 ПОДАРКИ ] —\n\nДля: {esc(user['partner_name'])}\n\n💰 Твой баланс: {user['balance']}"
    await edit_or_send(query, text, gifts_kb(query.from_user.id), image_url="")


@dp.callback_query(GiftCB.filter())
@inject_user
async def cb_buy_gift(query: types.CallbackQuery, callback_data: GiftCB, user: dict, chat_id: int):
    if query.from_user.id != callback_data.owner_id: return
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return

    gift = GIFTS.get(callback_data.item)
    if not gift: return

    if user["balance"] < gift["price"]:
        await query.answer("❌ Недостаточно монет на балансе!", show_alert=True)
        return

    partner = await get_user(user["partner_id"], chat_id)
    if not partner: return

    new_balance = user["balance"] - gift["price"]
    new_xp = user["rel_xp"] + gift["xp"]

    await update_user(query.from_user.id, chat_id, balance=new_balance, rel_xp=new_xp)
    await update_user(partner["user_id"], chat_id, rel_xp=new_xp)

    level = min(new_xp // XP_PER_LEVEL, MAX_LEVEL)

    await query.answer(f"✅ Ты подарил(а) {gift['name']}!\n+{gift['xp']} XP к отношениям.", show_alert=True)

    # ===== УВЕДОМЛЕНИЕ В ЧАТ О ПОДАРКЕ =====
    sender_name = esc(user["character_name"])
    partner_name = esc(partner["character_name"])
    gift_name = gift["name"]
    xp_gained = gift["xp"]

    try:
        await bot.send_message(
            chat_id,
            f"🎁 <b>{sender_name}</b> подарил(а) <b>{gift_name}</b> для <b>{partner_name}</b>!\n"
            f"💕 +{xp_gained} XP к отношениям.\n"
            f"📊 Текущий уровень отношений: <b>{level} / {MAX_LEVEL}</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки подарка в чат: {e}")

    text = f"— [ 🎁 ПОДАРКИ ] —\n\nДля: {esc(partner['character_name'])}\n\n💰 Твой баланс: {new_balance}\n📊 Уровень отношений: {level} / {MAX_LEVEL}"
    await edit_or_send(query, text, gifts_kb(query.from_user.id), image_url="")
@dp.message(Command("divorce_text"))
async def cmd_divorce_text(message: types.Message):
    # Это скрытая команда, мы вызываем её из tracker.py
    chat_id = message.chat.id
    user = await get_user(message.from_user.id, chat_id)
    if not user["partner_id"]:
        return await message.answer("❌ У тебя нет партнёра.")

    partner_id = user["partner_id"]
    await update_user(message.from_user.id, chat_id, partner_id=0, partner_name="", rel_xp=0, rel_started=0, is_married=0,
                      married_at=0, child_id="", child_name="", rel_image="")
    await update_user(partner_id, chat_id, partner_id=0, partner_name="", rel_xp=0, rel_started=0, is_married=0,
                      married_at=0, child_id="", child_name="", rel_image="")

    await message.answer("💔 Отношения разорваны.", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("refuse_child"))
async def cmd_refuse_child_text(message: types.Message):
    chat_id = message.chat.id
    user = await get_user(message.from_user.id, chat_id)
    if not user["child_id"]:
        return await message.answer("❌ У тебя нет детей.")

    # Очищаем у обоих
    partner_id = user["partner_id"]
    await update_user(message.from_user.id, chat_id, child_id="", child_name="")
    if partner_id:
        await update_user(partner_id, chat_id, child_id="", child_name="")

    await message.answer("🕊️ Вы отказались от ребенка.", reply_markup=back_kb(message.from_user.id))


from callbacks import ConfirmCB  # <--- добавь в импорты вверху


@dp.callback_query(ConfirmCB.filter(F.action == "divorce"))
async def cb_confirm_divorce(query: types.CallbackQuery, callback_data: ConfirmCB):
    if query.from_user.id != callback_data.owner_id:
        return await query.answer("❌ Это не ваша кнопка.", show_alert=True)

    chat_id = query.message.chat.id
    user = await get_user(query.from_user.id, chat_id)
    if not user["partner_id"]:
        return await query.answer("У вас нет партнёра.", show_alert=True)

    partner_id = user["partner_id"]
    await update_user(query.from_user.id, chat_id, partner_id=0, partner_name="", rel_xp=0, rel_started=0, is_married=0,
                      married_at=0, child_id="", child_name="", rel_image="")
    await update_user(partner_id, chat_id, partner_id=0, partner_name="", rel_xp=0, rel_started=0, is_married=0,
                      married_at=0, child_id="", child_name="", rel_image="")

    await query.message.edit_text("💔 Отношения разорваны.", parse_mode="HTML")


@dp.callback_query(ConfirmCB.filter(F.action == "refuse_child"))
async def cb_confirm_refuse(query: types.CallbackQuery, callback_data: ConfirmCB):
    if query.from_user.id != callback_data.owner_id:
        return await query.answer("❌ Это не ваша кнопка.", show_alert=True)

    chat_id = query.message.chat.id
    user = await get_user(query.from_user.id, chat_id)
    if not user["child_id"]:
        return await query.answer("У вас нет детей.", show_alert=True)

    partner_id = user["partner_id"]
    await update_user(query.from_user.id, chat_id, child_id="", child_name="")
    if partner_id:
        await update_user(partner_id, chat_id, child_id="", child_name="")

    await query.message.edit_text("🕊️ Вы отказались от ребенка.", parse_mode="HTML")
@dp.callback_query(F.data == "cancel_confirm")
async def cb_cancel_confirm(query: types.CallbackQuery):
    await query.message.edit_text("❌ Действие отменено.", parse_mode="HTML")