import random
from datetime import datetime, timezone

from aiogram import types, F
from aiogram.types import FSInputFile

from bot_instance import bot, dp
from config import ANTISPAM_SECONDS
from constants import INTERACTIONS, INGREDIENT_DROP_CHANCE, REP_PER_MESSAGE, REP_PER_BOARD_TASK, DIV, PLACEHOLDER_IMAGES
from db import (
    get_user, update_user, increment_user_field,
    get_guild, update_guild,
    add_ingredient, get_ingredients, INGREDIENTS,
    get_food_buff, get_total_bonuses,
)
from helpers import (
    esc, _mention, extract_target, resolve_user_id,
    _gain_rep, get_progress, get_reputation_bonuses,
)
from state import _inter_cooldown
from characters import get_character_image
from helpers import get_placeholder_image
from handlers.chat_list import update_chat_list


@dp.message(F.text & ~F.text.startswith("/"))
async def track_text(message: types.Message):
    is_group = message.chat.type in ("group", "supergroup")
    user = await get_user(message.from_user.id)
    if message.from_user.username:
        try:
            await update_user(message.from_user.id, username=message.from_user.username)
        except Exception:
            pass
    if is_group and (not user or not user["character_name"]):
        try:
            await message.delete()
        except Exception:
            pass
        return
    if not user:
        return
    now = int(datetime.now(timezone.utc).timestamp())
    if user["muted_until"] and user["muted_until"] > now:
        try:
            await message.delete()
        except Exception:
            pass
        return
    text_lower = (message.text or "").lower().strip()
    matched = None
    for phrase in sorted(INTERACTIONS.keys(), key=len, reverse=True):
        if text_lower == phrase or text_lower.startswith(phrase + " "):
            matched = phrase
            break
    if matched or text_lower in ("усыновить", "удочерить"):
        if await handle_interaction(message, user, matched or text_lower):
            return
    if text_lower == "кто я":
        await show_user_card(message, user, message.from_user)
        return
    if text_lower == "кто ты" and message.reply_to_message:
        target = await get_user(message.reply_to_message.from_user.id)
        if target:
            await show_user_card(message, target, message.reply_to_message.from_user)
            return
        else:
            await message.answer("❌ Игрок ещё не зарегистрирован.")
            return
    if now - user["last_msg_time"] < ANTISPAM_SECONDS:
        return
    await increment_user_field(message.from_user.id, "messages_count", 1)
    await increment_user_field(message.from_user.id, "board_msgs", 1)
    await update_user(message.from_user.id, last_msg_time=now)
    await _gain_rep(message.from_user.id, message.chat.id, REP_PER_MESSAGE, message.from_user.first_name)
    if random.random() < INGREDIENT_DROP_CHANCE:
        await add_ingredient(message.from_user.id, random.choice(list(INGREDIENTS.keys())))
    if message.reply_to_message:
        await increment_user_field(message.from_user.id, "replies_count", 1)
        await increment_user_field(message.from_user.id, "board_reps", 1)
    user = await get_user(message.from_user.id)
    if user["guild_id"]:
        g = await get_guild(user["guild_id"])
        if g:
            await update_guild(user["guild_id"], week_points=g["week_points"] + 1)
    await check_board_auto(message)


@dp.message(F.sticker)
async def track_sticker(message: types.Message):
    is_group = message.chat.type in ("group", "supergroup")
    user = await get_user(message.from_user.id)
    if is_group and (not user or not user["character_name"]):
        try:
            await message.delete()
        except Exception:
            pass
        return
    if not user:
        return
    now = int(datetime.now(timezone.utc).timestamp())
    if user["muted_until"] and user["muted_until"] > now:
        try:
            await message.delete()
        except Exception:
            pass
        return
    if now - user["last_msg_time"] < ANTISPAM_SECONDS:
        return
    await increment_user_field(message.from_user.id, "stickers_count", 1)
    await increment_user_field(message.from_user.id, "board_sts", 1)
    await update_user(message.from_user.id, last_msg_time=now)
    await check_board_auto(message)


async def handle_interaction(message, user, text_lower):
    target_ref, target_disp = extract_target(message)
    target_id = None
    if isinstance(target_ref, int):
        target_id = target_ref
    elif isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            await message.reply(f"❌ Не нашёл @{target_ref}. Пусть игрок напишет в чат с ботом.")
            return True
    if not target_id:
        return False
    if target_id == message.from_user.id:
        await message.reply("🙃 С собой так нельзя.")
        return True
    target = await get_user(target_id)
    if not target or not target["character_name"]:
        await message.reply("❌ Игрок ещё не зарегистрирован или не выбрал персонажа.")
        return True
    if text_lower in ("усыновить", "удочерить"):
        if not user["is_married"]:
            await message.reply("👶 Усыновить можно только в браке.")
            return True
        if user["child_id"]:
            await message.reply("👶 У тебя уже есть ребёнок.")
            return True
        if user["partner_id"] != target_id:
            await message.reply("👶 Усыновить можно только партнёра по браку.")
            return True
        await update_user(message.from_user.id, child_id=target_id, child_name=target["character_name"])
        await update_user(target_id, child_id=message.from_user.id, child_name=user["character_name"])
        verb = "усыновил" if user["gender"] == "male" else ("удочерил" if user["gender"] == "female" else "усыновил(а)")
        await message.answer(
            f"👶 {esc(user['character_name'])} {verb} {esc(target['character_name'])}!\n\nОрион плачет от умиления 💛")
        return True
    inter = INTERACTIONS.get(text_lower)
    if not inter:
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    last = _inter_cooldown.get(message.from_user.id, 0)
    if now - last < 2:
        try:
            await message.delete()
        except Exception:
            pass
        return True
    xp = inter.get("xp", 0)
    if inter.get("pair_only"):
        if user["partner_id"] != target_id:
            await message.reply("💕 Это взаимодействие только для пары.")
            return True
        if xp:
            await update_user(message.from_user.id, rel_xp=(user["rel_xp"] or 0) + xp)
            await update_user(target_id, rel_xp=(target["rel_xp"] or 0) + xp)
            user = await get_user(message.from_user.id)
    verb = inter["verb_f"] if user["gender"] == "female" else inter["verb_m"]
    emoji = inter["emoji"]
    xp_line = f"\n💕 +{xp} XP" if xp else ""
    if text_lower == "подарить цветок":
        sender_mention = _mention(message.from_user.id, user.get("username"),
                                  user.get("character_name"), message.from_user.first_name)
        target_mention = _mention(target_id, target.get("username"),
                                  target.get("character_name"), None)
        text = f"🌸 {sender_mention} {verb} цветок {target_mention}!\n\n💐 Орион тоже хочет цветочек..."
    else:
        text = f"{emoji} <b>{esc(user['character_name'])}</b> {verb} <b>{esc(target['character_name'])}</b>!{xp_line}"
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer(text, parse_mode="HTML")
    _inter_cooldown[message.from_user.id] = now
    return True


async def show_user_card(message, user, tg_user):
    name = esc(user["character_name"] or "Не выбран")
    gtext = "Мужской" if user["gender"] == "male" else ("Женский" if user["gender"] == "female" else "Не указан")
    if user["partner_id"]:
        status = "💍 В браке" if user["is_married"] else "💕 В отношениях"
        partner_line = f"❤️ {esc(user['partner_name'])} · {status}"
    else:
        partner_line = "❤️ Свободен(а)"
    child_line = ""
    if user["child_id"]:
        child_line = f"\n👶 {esc(user['child_name'])}"
    if user["guild_id"]:
        g = await get_guild(user["guild_id"])
        if g:
            guild_line = f"🏰 {esc(g['name'])} · 👑 {esc(user['guild_rank'])}"
        else:
            guild_line = "🏰 Без гильдии"
    else:
        guild_line = "🏰 Без гильдии"
    from db import get_rep_level
    rep_level = get_rep_level(user["reputation"])
    text = (
        f"🎴 КАРТОЧКА ПУТЕШЕСТВЕННИКА\n{DIV}\n\n"
        f"🎭 {name} · ⚧ {gtext}\n\n"
        f"{DIV}\n\n"
        f"💬 Сообщений: {user['messages_count']}\n"
        f"🎖️ Репутация: {rep_level} / 10\n"
        f"💰 Баланс: {user['balance']}\n\n"
        f"{DIV}\n\n"
        f"{partner_line}{child_line}\n"
        f"{guild_line}"
    )
    candidates = []
    if user["character_name"]:
        candidates.append(get_character_image(user["character_name"]))
    placeholder = get_placeholder_image()
    candidates.append(placeholder)
    candidates.append(None)

    for url in candidates:
        if url:
            try:
                if url in PLACEHOLDER_IMAGES:
                    await message.answer_photo(FSInputFile(url), caption=text, parse_mode="HTML")
                else:
                    await message.answer_photo(url, caption=text, parse_mode="HTML")
                return
            except Exception:
                continue
        else:
            try:
                await message.answer(text, parse_mode="HTML")
                return
            except Exception:
                await message.answer(text)
                return


async def check_board_auto(message):
    from state import get_board_lock
    async with get_board_lock(message.from_user.id):
        await _check_board_auto_locked(message)


async def _check_board_auto_locked(message):
    user = await get_user(message.from_user.id)
    if not user or not user["board_accepted"]:
        return
    accepted = user["board_accepted"].split(";") if user["board_accepted"] else []
    claimed = user["board_claimed"].split(";") if user["board_claimed"] else []
    if not accepted:
        return

    earn_b, _ = await get_total_bonuses(message.from_user.id)
    rep_earn, _, _ = get_reputation_bonuses(user["reputation"])
    _, food_value = await get_food_buff(message.from_user.id)
    total_earn = earn_b + rep_earn + food_value
    from constants import TASKS

    for t_id in accepted:
        if t_id in claimed or t_id not in TASKS:
            continue
        t = TASKS[t_id]
        if get_progress(user, t["cat"]) >= t["need"]:
            new_claimed = list(claimed) + [t_id]
            await update_user(message.from_user.id, board_claimed=";".join(new_claimed))
            claimed = new_claimed

            reward = t["reward"]
            if total_earn:
                reward = int(reward * (100 + total_earn) / 100)
            await increment_user_field(message.from_user.id, "balance", reward)
            await _gain_rep(message.from_user.id, message.chat.id, REP_PER_BOARD_TASK, message.from_user.first_name)
            mention = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'
            try:
                await message.answer(
                    f"🎉 {mention}, задание выполнено!\n\n«{t['text']}»\n💰 Награда: {reward} монет\n🎖️ +{REP_PER_BOARD_TASK} репутации",
                    parse_mode="HTML")
            except Exception:
                pass


@dp.chat_member()
async def on_chat_member_update(event: types.ChatMemberUpdated):
    try:
        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status
        was_in = old_status in ("member", "administrator", "creator", "restricted")
        is_gone = new_status in ("left", "kicked")
        if was_in and is_gone:
            user = await get_user(event.from_user.id)
            if user and user["character_name"]:
                old_name = user["character_name"]
                await update_user(event.from_user.id, character_name="", char_change_paid=0)
                try:
                    await bot.send_message(event.chat.id,
                                           f"🎭 Роль «{esc(old_name)}» освобождена —\nеё владелец покинул группу.",
                                           parse_mode="HTML")
                except Exception:
                    pass
                print(f"Освобождена роль {old_name} (user {event.from_user.id})")

                # АВТООБНОВЛЕНИЕ СПИСКА РОЛЕЙ ПРИ ВЫХОДЕ
                await update_chat_list(event.chat.id)

    except Exception as e:
        print(f"ChatMemberUpdate error: {e}")