from datetime import datetime, timezone

from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from callbacks import MenuCB, RelCB, GiftCB, ProposeCB
from config import OWNER_ID, PROPOSE_COOLDOWN
from constants import (
    DIV, GIFTS, XP_PER_LEVEL, MAX_LEVEL, WEDDING_LEVEL,
)
from db import (
    get_user, update_user, get_protected_owner,
)
from helpers import (
    esc, user_display_name, edit_or_send, _ensure_user,
    extract_target, resolve_user_id, _now_ts,
)
from keyboards import relations_kb, gifts_kb, back_kb
from state import _propose_cooldown


@dp.callback_query(MenuCB.filter(F.action == "relations"))
async def cb_relations(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    name = esc(user_display_name(user))
    if user["partner_id"]:
        level = min(user["rel_xp"] // XP_PER_LEVEL, MAX_LEVEL)
        married = bool(user["is_married"])
        status = "💍 В браке" if married else "💕 В отношениях"
        started = (datetime.fromtimestamp(user["rel_started"], timezone.utc).strftime("%d.%m.%Y")
                   if user["rel_started"] else "?")
        extra = ""
        if married and user["married_at"]:
            extra += f"\n💒 Свадьба: {datetime.fromtimestamp(user['married_at'], timezone.utc).strftime('%d.%m.%Y')}"
        if user["child_id"]:
            extra += f"\n👶 Ребёнок: {esc(user['child_name'])}"
        text = (f"❤️ ОТНОШЕНИЯ\n{DIV}\n\n"
                f"💕 {name} + {esc(user['partner_name'])}\n\n"
                f"{DIV}\n\n"
                f"📅 Вместе с: {started}\n"
                f"📊 Уровень: {level} / {MAX_LEVEL}\n"
                f"✨ Опыт: {user['rel_xp']} XP\n"
                f"💍 Статус: {status}{extra}")
        kb = relations_kb(query.from_user.id, True, married, level >= WEDDING_LEVEL,
                          bool(user["child_id"]), user["gender"])
    else:
        text = (f"❤️ ОТНОШЕНИЯ\n{DIV}\n\n"
                f"{name}, твоё сердце\nсвободно 💌\n\n"
                f"{DIV}\n\n"
                f"Ответь на сообщение игрока\nи напиши /propose\n\n"
                f"или укажи @username:\n/propose @user")
        kb = relations_kb(query.from_user.id, False, False, False, False, user["gender"])
    await edit_or_send(query, text, kb)


@dp.callback_query(RelCB.filter(F.action == "gifts"))
async def cb_gifts(query: types.CallbackQuery, callback_data: RelCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return
    text = f"🎁 ПОДАРКИ\n{DIV}\n\nДля: {esc(user['partner_name'])}\n💰 Баланс: {user['balance']}"
    await edit_or_send(query, text, gifts_kb(query.from_user.id))


@dp.callback_query(GiftCB.filter())
async def cb_gift_buy(query: types.CallbackQuery, callback_data: GiftCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return
    if callback_data.item not in GIFTS:
        await query.answer("❌ Не найдено", show_alert=True)
        return
    g = GIFTS[callback_data.item]
    if user["balance"] < g["price"]:
        await query.answer(f"❌ Нужно {g['price']}", show_alert=True)
        return
    await update_user(query.from_user.id, balance=user["balance"] - g["price"])
    partner = await get_user(user["partner_id"])
    if partner:
        await update_user(partner["user_id"], rel_xp=partner["rel_xp"] + g["xp"])
    await update_user(query.from_user.id, rel_xp=user["rel_xp"] + g["xp"])
    level = min((user["rel_xp"] + g["xp"]) // XP_PER_LEVEL, MAX_LEVEL)
    b = InlineKeyboardBuilder()
    b.button(text="🎁 Ещё ›", callback_data=RelCB(action="gifts", owner_id=query.from_user.id))
    b.button(text="‹ К отношениям", callback_data=MenuCB(action="relations", owner_id=query.from_user.id))
    b.adjust(1)
    text = (f"💝 ПОДАРОК ВРУЧЁН!\n{DIV}\n\n"
            f"Ты подарил(а): {g['name']}\n\n"
            f"💕 +{g['xp']} XP\n"
            f"📊 Уровень: {level} / {MAX_LEVEL}\n"
            f"💰 Остаток: {user['balance'] - g['price']}")
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(RelCB.filter(F.action == "marry"))
async def cb_marry(query: types.CallbackQuery, callback_data: RelCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["partner_id"]:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return
    level = min(user["rel_xp"] // XP_PER_LEVEL, MAX_LEVEL)
    if level < WEDDING_LEVEL:
        await query.answer(f"❌ Нужен {WEDDING_LEVEL} уровень", show_alert=True)
        return
    if user["is_married"]:
        await query.answer("❌ Вы уже женаты.", show_alert=True)
        return
    now = int(datetime.now(timezone.utc).timestamp())
    await update_user(query.from_user.id, is_married=1, married_at=now)
    partner = await get_user(user["partner_id"])
    if partner:
        await update_user(partner["user_id"], is_married=1, married_at=now)
    m1 = f'<a href="tg://user?id={query.from_user.id}">{esc(query.from_user.first_name)}</a>'
    m2 = f'<a href="tg://user?id={user["partner_id"]}">{esc(user["partner_name"])}</a>'
    text = f"💍 СВАДЬБА СЫГРАНА!\n{DIV}\n\n{m1} и {m2}\nтеперь муж и жена! 🎉\n\n{DIV}\n\nОрион поздравляет! 💛"
    await edit_or_send(query, text, back_kb(query.from_user.id))


@dp.callback_query(RelCB.filter(F.action == "adopt_hint"))
async def cb_adopt_hint(query: types.CallbackQuery, callback_data: RelCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    verb = ("усыновить" if user["gender"] == "male"
            else ("удочерить" if user["gender"] == "female" else "усыновить/удочерить"))
    await query.answer(f"👶 Ответь на сообщение партнёра и напиши «{verb}»\n(можно и через @username)", show_alert=True)


@dp.callback_query(RelCB.filter(F.action == "breakup"))
async def cb_breakup(query: types.CallbackQuery, callback_data: RelCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    pid = user["partner_id"]
    if not pid:
        await query.answer("❌ Нет партнёра.", show_alert=True)
        return
    await update_user(query.from_user.id, partner_id=0, partner_name="", rel_xp=0,
                      is_married=0, rel_started=0, married_at=0, child_id=0, child_name="")
    await update_user(pid, partner_id=0, partner_name="", rel_xp=0,
                      is_married=0, rel_started=0, married_at=0, child_id=0, child_name="")
    text = f"💔 ОТНОШЕНИЯ РАЗОРВАНЫ\n{DIV}\n\nВсё ещё впереди!"
    await edit_or_send(query, text, back_kb(query.from_user.id))


@dp.message(Command("propose"))
async def cmd_propose(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Только в группе.")
        return
    target_ref, display = extract_target(message)
    if target_ref is None:
        await message.answer("💌 Ответь (reply) на сообщение игрока и напиши /propose\n"
                             "или укажи его через @username: /propose @user")
        return
    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            await message.answer(f"❌ Не нашёл @{target_ref}. Пусть игрок сначала напишет что-нибудь в чат с ботом.")
            return
        display = target_ref
    else:
        target_id = target_ref
    if target_id == message.from_user.id:
        await message.answer("❌ Себе нельзя.")
        return
    me = await _ensure_user(message.from_user.id)
    other = await _ensure_user(target_id)
    try:
        tg_target = await bot.get_chat(target_id)
        if getattr(tg_target, "is_bot", False):
            await message.answer("❌ Боту нельзя.")
            return
    except Exception:
        pass
    protected_owner = await get_protected_owner(target_id)
    if protected_owner and message.from_user.id != protected_owner:
        owner_user = await get_user(protected_owner)
        if owner_user and owner_user.get("character_name"):
            owner_name = esc(owner_user["character_name"])
        else:
            owner_name = f'<a href="tg://user?id={protected_owner}">владельца</a>'
        try:
            await message.answer(f"❌ Этот человек только для {owner_name}.", parse_mode="HTML")
        except Exception:
            await message.answer("❌ Этот человек только для владельца.")
        return
    if not me["character_name"]:
        await message.answer("❌ Сначала выбери персонажа: /start")
        return
    if not other["character_name"]:
        await message.answer(f"❌ {esc(display)} ещё не выбрал персонажа.")
        return
    # ПАТЧ 5: игрок не писал боту — он не увидит предложение
    if not other.get("last_msg_time"):
        await message.answer(f"❌ {esc(display)} ещё не писал боту. Пусть напишет /start.")
        return
    if me["partner_id"]:
        await message.answer("❌ Ты уже в отношениях.")
        return
    if other["partner_id"]:
        await message.answer(f"❌ {esc(display)} уже в отношениях.")
        return
    if message.from_user.id != OWNER_ID:
        key = ("propose", message.from_user.id, target_id, message.chat.id)
        now_ts = _now_ts()
        last = _propose_cooldown.get(key, 0)
        if now_ts - last < PROPOSE_COOLDOWN:
            left = int(PROPOSE_COOLDOWN - (now_ts - last))
            await message.answer(f"⏳ Ты уже отправлял(а) предложение этому игроку. Подожди {left} сек.")
            return
        _propose_cooldown[key] = now_ts
    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять", callback_data=ProposeCB(action="accept",
                                                       proposer_id=message.from_user.id, target_id=target_id))
    b.button(text="❌ Отклонить", callback_data=ProposeCB(action="decline",
                                                         proposer_id=message.from_user.id, target_id=target_id))
    b.adjust(2)
    mention = f'<a href="tg://user?id={target_id}">{esc(display)}</a>'
    proposer = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'
    await message.answer(
        f"💌 ПРЕДЛОЖЕНИЕ ОТНОШЕНИЙ\n{DIV}\n\n{mention}, {proposer}\nпредлагает тебе отношения!\n\nСогласен(на)?",
        reply_markup=b.as_markup(), parse_mode="HTML")


@dp.callback_query(ProposeCB.filter())
async def cb_propose(query: types.CallbackQuery, callback_data: ProposeCB):
    if query.from_user.id != callback_data.target_id:
        await query.answer("❌ Не для тебя!", show_alert=True)
        return
    proposer = await get_user(callback_data.proposer_id)
    target = await get_user(callback_data.target_id)
    if not proposer or not target:
        await query.answer("❌ Ошибка", show_alert=True)
        return
    if callback_data.action == "decline":
        b = InlineKeyboardBuilder()
        b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=callback_data.target_id))
        text = f"💔 ОТКЛОНЕНО\n{DIV}\n\nНичего страшного!"
        await edit_or_send(query, text, b.as_markup())
        return
    protected_owner = await get_protected_owner(callback_data.target_id)
    if protected_owner and callback_data.proposer_id != protected_owner:
        await query.answer("❌ Этот человек только для владельца.", show_alert=True)
        return
    if not proposer["character_name"] or not target["character_name"]:
        await query.answer("❌ Кто-то из вас не выбрал персонажа.", show_alert=True)
        return
    if proposer["partner_id"] or target["partner_id"]:
        await query.answer("❌ Кто-то уже в отношениях.", show_alert=True)
        return
    now = int(datetime.now(timezone.utc).timestamp())
    await update_user(callback_data.proposer_id, partner_id=callback_data.target_id,
                      partner_name=target["character_name"] or "Игрок",
                      rel_xp=0, is_married=0, rel_started=now)
    await update_user(callback_data.target_id, partner_id=callback_data.proposer_id,
                      partner_name=proposer["character_name"] or "Игрок",
                      rel_xp=0, is_married=0, rel_started=now)
    b = InlineKeyboardBuilder()
    b.button(text="❤️ К отношениям ›", callback_data=MenuCB(action="relations", owner_id=callback_data.target_id))
    b.button(text="‹ В меню", callback_data=MenuCB(action="menu", owner_id=callback_data.target_id))
    b.adjust(1)
    text = (f"💕 ПОЗДРАВЛЯЕМ!\n{DIV}\n\nТеперь вы вместе!\n\n"
            f"Свадьба — на 5 уровне\nотношений 💒")
    await edit_or_send(query, text, b.as_markup())