import random
import aiosqlite
from datetime import datetime, timezone

from aiogram import types, F
from aiogram.types import FSInputFile
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from config import ANTISPAM_SECONDS, DB_PATH
from constants import (
    INTERACTIONS, INGREDIENT_DROP_CHANCE, REP_PER_MESSAGE,
    REP_PER_BOARD_TASK, DIV, PLACEHOLDER_IMAGES, QUIZ_REWARD
)
from db import (
    get_user, update_user, increment_user_field,
    get_guild, update_guild,
    add_ingredient, get_ingredients, INGREDIENTS,
    get_food_buff, get_total_bonuses, update_primogems,
    get_application, update_application_status, get_taken_characters
)
from helpers import (
    esc, _mention, extract_target, resolve_user_id,
    _gain_rep, get_progress, get_reputation_bonuses, inject_user
)
from state import _inter_cooldown
import state
from characters import get_character_image, CHARACTERS
from helpers import get_placeholder_image
from handlers.chat_list import update_chat_list
from handlers.fun import start_duel_logic
from keyboards import back_kb


@dp.callback_query(F.data == "quiz_answer")
async def cb_quiz_answer(query: types.CallbackQuery):
    await query.answer("✍️ Просто напиши правильный ответ в чат!", show_alert=True)


@dp.message(StateFilter(None), F.text & ~F.text.startswith("/"))
@inject_user
async def track_text(message: types.Message, user: dict, chat_id: int):
    is_group = message.chat.type in ("group", "supergroup")

    if message.from_user.username:
        try:
            await update_user(message.from_user.id, chat_id, username=message.from_user.username)
        except Exception:
            pass

    if not user.get("first_seen"):
        await update_user(message.from_user.id, chat_id, first_seen=int(datetime.now(timezone.utc).timestamp()))
        user = await get_user(message.from_user.id, chat_id)

    if is_group and not user["character_name"]:
        try:
            await message.delete()
        except Exception:
            pass
        return

    now = int(datetime.now(timezone.utc).timestamp())
    if user["muted_until"] and user["muted_until"] > now:
        try:
            await message.delete()
        except Exception:
            pass
        return

    text_lower = (message.text or "").lower().strip()

    # ===== ПРОВЕРКА ВИКТОРИНЫ =====
    quiz = state._active_quizzes.get(message.chat.id)
    if quiz:
        correct_answer = quiz.get("answer", "")
        is_correct = False
        if correct_answer:
            if text_lower == correct_answer:
                is_correct = True
            elif text_lower in correct_answer:
                is_correct = True
            elif correct_answer in text_lower:
                is_correct = True
            else:
                for word in correct_answer.split():
                    if len(word) > 2 and word in text_lower:
                        is_correct = True
                        break

        if is_correct:
            reward = quiz.get("reward", QUIZ_REWARD)
            await update_user(message.from_user.id, chat_id, balance=user["balance"] + reward)
            await update_primogems(message.from_user.id, chat_id, 40)

            mention = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'

            await message.answer(
                f"🎉 <b>ПРАВИЛЬНЫЙ ОТВЕТ!</b>\n\n"
                f"{mention} быстрее всех ответил и получает "
                f"<b>{reward} монет</b> и <b>40 Примогемов</b>! 💰💎",
                parse_mode="HTML",
                reply_markup=back_kb(message.from_user.id)
            )
            state._active_quizzes.pop(message.chat.id, None)
            return
    # ====================================================

    if "вызвать на дуэль" in text_lower and is_group:
        parts = text_lower.split()
        bet = 0
        if parts[-1].isdigit():
            bet = int(parts[-1])

        if bet > 0:
            target_ref, display = extract_target(message)
            if target_ref is None:
                for ent in (message.entities or []):
                    if ent.type == "mention":
                        uname = message.text[ent.offset + 1: ent.offset + ent.length]
                        target_ref = uname
                        display = uname
                        break

            if target_ref:
                await start_duel_logic(message, target_ref, display, bet)
                return
            else:
                await message.reply(
                    "⚔️ Чтобы вызвать на дуэль, ответь на сообщение игрока или укажи @username, и напиши сумму (например: Вызвать на дуэль 500)")
                return

    matched = None
    for phrase in sorted(INTERACTIONS.keys(), key=len, reverse=True):
        if text_lower == phrase or text_lower.startswith(phrase + " "):
            matched = phrase
            break
    if matched or text_lower in ("усыновить", "удочерить"):
        if await handle_interaction(message, user, matched or text_lower, chat_id):
            return
    if text_lower == "кто я":
        await show_user_card(message, user, message.from_user, chat_id)
        return
    if text_lower == "кто ты" and message.reply_to_message:
        target = await get_user(message.reply_to_message.from_user.id, chat_id)
        if target:
            await show_user_card(message, target, message.reply_to_message.from_user, chat_id)
            return
        else:
            await message.answer("❌ Игрок ещё не зарегистрирован.", reply_markup=back_kb(message.from_user.id))
            return

    if now - user["last_msg_time"] < ANTISPAM_SECONDS:
        return

    await increment_user_field(message.from_user.id, chat_id, "messages_count", 1)
    await increment_user_field(message.from_user.id, chat_id, "board_msgs", 1)
    await update_user(message.from_user.id, chat_id, last_msg_time=now)
    await _gain_rep(message.from_user.id, chat_id, REP_PER_MESSAGE, message.from_user.first_name)

    if random.random() < INGREDIENT_DROP_CHANCE:
        await add_ingredient(message.from_user.id, chat_id, random.choice(list(INGREDIENTS.keys())))

    if message.reply_to_message:
        await increment_user_field(message.from_user.id, chat_id, "replies_count", 1)
        await increment_user_field(message.from_user.id, chat_id, "board_reps", 1)

    user = await get_user(message.from_user.id, chat_id)
    if user["guild_id"]:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_member_stats (guild_id, user_id, msgs, replies) 
                VALUES (?, ?, 1, ?) 
                ON CONFLICT(guild_id, user_id) DO UPDATE SET msgs = msgs + 1, replies = replies + ?
            """, (user["guild_id"], user["user_id"], 1 if message.reply_to_message else 0,
                  1 if message.reply_to_message else 0))
            await db.commit()
    await check_board_auto(message)


@dp.message(StateFilter(None), F.sticker)
@inject_user
async def track_sticker(message: types.Message, user: dict, chat_id: int):
    is_group = message.chat.type in ("group", "supergroup")

    if is_group and not user["character_name"]:
        try:
            await message.delete()
        except:
            pass
        return

    now = int(datetime.now(timezone.utc).timestamp())
    if user["muted_until"] and user["muted_until"] > now:
        try:
            await message.delete()
        except:
            pass
        return

    if now - user["last_msg_time"] < ANTISPAM_SECONDS: return

    await increment_user_field(message.from_user.id, chat_id, "stickers_count", 1)
    await increment_user_field(message.from_user.id, chat_id, "board_sts", 1)
    await update_user(message.from_user.id, chat_id, last_msg_time=now)

    if user["guild_id"]:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_member_stats (guild_id, user_id, stickers) 
                VALUES (?, ?, 1) 
                ON CONFLICT(guild_id, user_id) DO UPDATE SET stickers = stickers + 1
            """, (user["guild_id"], user["user_id"]))
            await db.commit()

    await check_board_auto(message)


@dp.message(StateFilter(None), F.photo)
@inject_user
async def track_photo(message: types.Message, user: dict, chat_id: int):
    is_group = message.chat.type in ("group", "supergroup")
    if is_group and not user["character_name"]:
        return

    now = int(datetime.now(timezone.utc).timestamp())
    if user["muted_until"] and user["muted_until"] > now:
        return

    if user["guild_id"]:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO guild_member_stats (guild_id, user_id, photos) 
                VALUES (?, ?, 1) 
                ON CONFLICT(guild_id, user_id) DO UPDATE SET photos = photos + 1
            """, (user["guild_id"], user["user_id"]))
            await db.commit()


async def handle_interaction(message, user, text_lower, chat_id):
    target_ref, target_disp = extract_target(message)
    target_id = None
    if isinstance(target_ref, int):
        target_id = target_ref
    elif isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            await message.reply(f"❌ Не нашёл @{target_ref}. Пусть игрок напишет в чат с ботом.")
            return True
    if not target_id: return False
    if target_id == message.from_user.id:
        await message.reply("🙃 С собой так нельзя.")
        return True
    target = await get_user(target_id, chat_id)
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
        await update_user(message.from_user.id, chat_id, child_id=target_id, child_name=target["character_name"])
        await update_user(target_id, chat_id, child_id=message.from_user.id, child_name=user["character_name"])
        verb = "усыновил" if user["gender"] == "male" else ("удочерил" if user["gender"] == "female" else "усыновил(а)")
        await message.answer(
            f"👶 {esc(user['character_name'])} {verb} {esc(target['character_name'])}!\n\nОрион плачет от умиления 💛",
            reply_markup=back_kb(message.from_user.id))
        return True
    inter = INTERACTIONS.get(text_lower)
    if not inter: return False
    now = int(datetime.now(timezone.utc).timestamp())
    last = _inter_cooldown.get(message.from_user.id, 0)
    if now - last < 2:
        try:
            await message.delete()
        except:
            pass
        return True
    xp = inter.get("xp", 0)
    if inter.get("pair_only"):
        if user["partner_id"] != target_id:
            await message.reply("💕 Это взаимодействие только для пары.")
            return True
        if xp:
            await update_user(message.from_user.id, chat_id, rel_xp=(user["rel_xp"] or 0) + xp)
            await update_user(target_id, chat_id, rel_xp=(target["rel_xp"] or 0) + xp)
            user = await get_user(message.from_user.id, chat_id)
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
    await message.answer(text, parse_mode="HTML", reply_markup=back_kb(message.from_user.id))
    _inter_cooldown[message.from_user.id] = now
    return True


async def show_user_card(message, user, tg_user, chat_id):
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
                    await message.answer_photo(FSInputFile(url), caption=text, parse_mode="HTML",
                                               reply_markup=back_kb(message.from_user.id))
                else:
                    await message.answer_photo(url, caption=text, parse_mode="HTML",
                                               reply_markup=back_kb(message.from_user.id))
                return
            except Exception:
                continue
        else:
            try:
                await message.answer(text, parse_mode="HTML", reply_markup=back_kb(message.from_user.id))
                return
            except Exception:
                await message.answer(text, reply_markup=back_kb(message.from_user.id))
                return


async def check_board_auto(message):
    from state import get_board_lock
    async with get_board_lock(message.from_user.id):
        await _check_board_auto_locked(message)


async def _check_board_auto_locked(message):
    chat_id = message.chat.id
    user = await get_user(message.from_user.id, chat_id)
    if not user or not user["board_accepted"]:
        return
    accepted = user["board_accepted"].split(";") if user["board_accepted"] else []
    claimed = user["board_claimed"].split(";") if user["board_claimed"] else []
    if not accepted:
        return

    earn_b, _ = await get_total_bonuses(message.from_user.id, chat_id)
    rep_earn, _, _ = get_reputation_bonuses(user["reputation"])
    _, food_value = await get_food_buff(message.from_user.id, chat_id)
    total_earn = earn_b + rep_earn + food_value
    from constants import TASKS

    for t_id in accepted:
        if t_id in claimed or t_id not in TASKS:
            continue
        t = TASKS[t_id]
        if get_progress(user, t["cat"]) >= t["need"]:
            new_claimed = list(claimed) + [t_id]
            await update_user(message.from_user.id, chat_id, board_claimed=";".join(new_claimed))
            claimed = new_claimed

            coins_reward = random.randint(100, 300)
            primo_reward = random.randint(20, 60)

            await increment_user_field(message.from_user.id, chat_id, "balance", coins_reward)
            await update_primogems(message.from_user.id, chat_id, primo_reward)
            await _gain_rep(message.from_user.id, chat_id, REP_PER_BOARD_TASK, message.from_user.first_name)

            mention = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'
            try:
                await message.answer(
                    f"🎉 {mention}, задание выполнено!\n\n«{t['text']}»\n💰 Награда: {coins_reward} монет\n💎 +{primo_reward} Примогемов\n🎖️ +{REP_PER_BOARD_TASK} репутации",
                    parse_mode="HTML",
                    reply_markup=back_kb(message.from_user.id)
                )
            except Exception:
                pass


@dp.chat_member()
async def on_chat_member_update(event: types.ChatMemberUpdated):
    try:
        affected_user = event.new_chat_member.user
        if affected_user.is_bot:
            return

        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status

        was_in = old_status in ("member", "administrator", "creator", "restricted")
        is_gone = new_status in ("left", "kicked")
        is_new = old_status in ("left", "kicked") and new_status in ("member", "administrator", "creator")

        if was_in and is_gone:
            user = await get_user(affected_user.id, event.chat.id)
            if user and user["character_name"]:
                old_name = user["character_name"]
                await update_user(affected_user.id, event.chat.id, character_name="", char_change_paid=0)
                try:
                    await bot.send_message(
                        event.chat.id,
                        f"🎭 Роль «{esc(old_name)}» освобождена —\nеё владелец покинул группу.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                await update_chat_list(event.chat.id)

        # --- ВЫБОР РОЛИ ПРИ ВХОДЕ ---
        elif is_new:
            app = await get_application(affected_user.id, event.chat.id)
            if app and app['status'] == 'accepted':
                taken = await get_taken_characters(event.chat.id)
                free_chars = [name for name in CHARACTERS.keys() if name not in taken]

                if not free_chars:
                    await bot.send_message(event.chat.id,
                                           "😔 Свободных ролей нет. Ожидайте, пока кто-нибудь освободит роль.")
                    return

                b = InlineKeyboardBuilder()
                # Выводим первые 15 свободных персонажей
                for ch in free_chars[:15]:
                    b.button(text=ch, callback_data=f"newchar_{affected_user.id}_{event.chat.id}_{ch}")
                b.adjust(2)

                mention = f'<a href="tg://user?id={affected_user.id}">{esc(affected_user.first_name)}</a>'
                await bot.send_message(
                    event.chat.id,
                    f"🎉 {mention}, твоя анкета одобрена!\n\nПожалуйста, выбери своего персонажа из списка ниже:",
                    reply_markup=b.as_markup(), parse_mode="HTML"
                )
                await update_application_status(affected_user.id, event.chat.id, 'waiting_char')
        # -------------------------------------
    except Exception as e:
        print(f"ChatMemberUpdate error: {e}")


@dp.callback_query(F.data.startswith("newchar_"))
async def cb_newchar(query: types.CallbackQuery):
    parts = query.data.split("_")
    uid = int(parts[1])
    chat_id = int(parts[2])
    char_name = "_".join(parts[3:])

    if query.from_user.id != uid:
        await query.answer("❌ Это не твоя анкета!", show_alert=True)
        return

    # Проверяем, не заняли ли роль
    taken = await get_taken_characters(chat_id)
    if char_name in taken:
        await query.answer("❌ Увы, эту роль только что заняли. Выберите другую.", show_alert=True)
        return

    await update_user(uid, chat_id, character_name=char_name)
    await update_application_status(uid, chat_id, 'joined')

    # Получаем анкету для отправки в чат
    app = await get_application(uid, chat_id)

    if not app:
        await query.answer("❌ Ошибка: анкета не найдена.", show_alert=True)
        return

    text = (
        f"🎉 <b>У нас новенький! Встречайте!</b>\n\n"
        f"🎭 <b>Роль:</b> {esc(char_name)}\n\n"
        f"📖 <b>Опыт:</b> {esc(app['experience'])}\n"
        f"🌟 <b>О себе:</b> {esc(app['about'])}\n"
        f"🕒 <b>Часовой пояс:</b> {esc(app['timezone'])}\n"
        f"⚠️ <b>Триггеры:</b> {esc(app['triggers'])}\n"
        f"🚫 <b>Метагейминг:</b> {esc(app['metagaming'])}\n"
        f"⚡ <b>Активность:</b> {esc(app['activity'])}"
    )

    try:
        await query.message.delete()
    except:
        pass

    await bot.send_message(chat_id, text, parse_mode="HTML")
    await update_chat_list(chat_id)