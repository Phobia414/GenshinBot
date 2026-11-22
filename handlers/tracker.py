import random
import aiosqlite
from datetime import datetime, timezone

from aiogram import types, F
from aiogram.types import FSInputFile
from aiogram.filters import StateFilter, Command

from bot_instance import bot, dp
from config import ANTISPAM_SECONDS, DB_PATH, OWNER_ID
from constants import (
    INTERACTIONS, INGREDIENT_DROP_CHANCE, REP_PER_MESSAGE,
    REP_PER_BOARD_TASK, DIV, PLACEHOLDER_IMAGES, QUIZ_REWARD
)
from db import (
    get_user, update_user, increment_user_field,
    get_guild, update_guild,
    add_ingredient, get_ingredients, INGREDIENTS,
    get_food_buff, get_total_bonuses, update_primogems,
    get_application, update_application_status, get_all_custom_interactions,
    execute  # <--- ДОБАВЛЕНО ДЛЯ ИСПРАВЛЕНИЯ БЛОКИРОВКИ БД
)
from helpers import (
    esc, _mention, extract_target, resolve_user_id,
    _gain_rep, get_progress, get_reputation_bonuses, inject_user,
    get_ranks_config
)
from state import _inter_cooldown
import state
from characters import get_character_image
from helpers import get_placeholder_image
from handlers.chat_list import update_chat_list
from handlers.fun import start_duel_logic
from keyboards import back_kb, regions_kb, gender_kb

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября",
          "декабря"]


@dp.callback_query(F.data == "quiz_answer")
async def cb_quiz_answer(query: types.CallbackQuery):
    await query.answer("✍️ Просто напиши правильный ответ в чат!", show_alert=True)


@dp.message(Command("rppartner"))
async def cmd_rppartner(message: types.Message):
    chat_id = message.chat.id
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("❌ Только в группе.")

    user = await get_user(message.from_user.id, chat_id)
    if not user or not user["character_name"]:
        return await message.answer("❌ Сначала выбери персонажа!")

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Использование:\n"
            "<code>/rppartner Имя_Роли</code> — искать напарника (можно несколько через запятую)\n"
            "<code>/rppartner off</code> — отменить поиск",
            parse_mode="HTML"
        )
        return

    target = parts[1].strip()
    if target.lower() == "off":
        await update_user(message.from_user.id, chat_id, search_rp_partner="")
        await message.answer("✅ Поиск со-роли отменен.")
    else:
        await update_user(message.from_user.id, chat_id, search_rp_partner=target)
        await message.answer(f"✅ Теперь ты ищешь со-роль: <b>{esc(target)}</b>! Твоя роль в списке помечена как ⨂.",
                             parse_mode="HTML")

    await update_chat_list(chat_id)


@dp.message(StateFilter(None), F.text & ~F.text.startswith("/") & ~F.text.startswith("!"))
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

    quiz = state._active_quizzes.get(message.chat.id)
    if quiz:
        correct_answers = quiz.get("answers", [])
        is_correct = False

        for answer in correct_answers:
            if not answer:
                continue
            if text_lower == answer or text_lower in answer or answer in text_lower:
                is_correct = True
                break
            else:
                for word in answer.split():
                    if len(word) > 2 and word in text_lower:
                        is_correct = True
                        break
            if is_correct:
                break

        if is_correct:
            reward_coins = quiz.get("coins", 50)
            # reward_primo = quiz.get("primo", 10) <--- УДАЛЕНО

            await update_user(message.from_user.id, chat_id, balance=user["balance"] + reward_coins)
            # await update_primogems(message.from_user.id, chat_id, reward_primo) <--- УДАЛЕНО

            mention = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'

            await bot.send_message(
                chat_id=chat_id,
                text=f"🎉 <b>ПРАВИЛЬНЫЙ ОТВЕТ!</b>\n\n"
                     f"{mention} быстрее всех ответил и получает "
                     f"<b>{reward_coins} монет</b>! 💰",  # <--- Убрали текст про примогемы
                parse_mode="HTML",
                reply_markup=back_kb(message.from_user.id)
            )
            state._active_quizzes.pop(message.chat.id, None)
            return

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
    custom_inter = None

    all_customs = await get_all_custom_interactions(chat_id)
    all_customs.sort(key=lambda x: len(x['name']), reverse=True)

    for ci in all_customs:
        ci_name = ci['name']
        if text_lower == ci_name or text_lower.startswith(ci_name + " "):
            if ci['is_private'] and ci['creator_id'] != message.from_user.id:
                continue
            custom_inter = ci
            matched = ci_name
            break

    if not matched:
        for phrase in sorted(INTERACTIONS.keys(), key=len, reverse=True):
            if text_lower == phrase or text_lower.startswith(phrase + " "):
                matched = phrase
                break

    if matched or text_lower in ("усыновить", "удочерить"):
        if custom_inter:
            if await handle_interaction(message, user, matched, chat_id, custom_inter=custom_inter):
                return
        else:
            if await handle_interaction(message, user, matched or text_lower, chat_id):
                return

    if text_lower == "кто я":
        await show_user_card(message, user, message.from_user, chat_id)
        return

    if text_lower.startswith("кто ты"):
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        else:
            target_ref, _ = extract_target(message)
            if isinstance(target_ref, str):
                target_id = await resolve_user_id(target_ref)
            elif isinstance(target_ref, int):
                target_id = target_ref

        if target_id:
            target = await get_user(target_id, chat_id)
            if target:
                await show_user_card(message, target, message.from_user, chat_id)
            else:
                await message.answer("❌ Игрок не найден в базе.", reply_markup=back_kb(message.from_user.id))
        else:
            await message.answer("❌ Ответь на сообщение игрока или укажи @username.",
                                 reply_markup=back_kb(message.from_user.id))
        return

    if now - user["last_msg_time"] < ANTISPAM_SECONDS:
        return

    await increment_user_field(message.from_user.id, chat_id, "messages_count", 1)
    await increment_user_field(message.from_user.id, chat_id, "board_msgs", 1)
    await increment_user_field(message.from_user.id, chat_id, "msgs_week", 1)
    await increment_user_field(message.from_user.id, chat_id, "msgs_month", 1)
    await increment_user_field(message.from_user.id, chat_id, "msgs_day", 1)

    await update_user(message.from_user.id, chat_id, last_msg_time=now)
    await _gain_rep(message.from_user.id, chat_id, REP_PER_MESSAGE, message.from_user.first_name)

    if random.random() < INGREDIENT_DROP_CHANCE:
        await add_ingredient(message.from_user.id, chat_id, random.choice(list(INGREDIENTS.keys())))

    if message.reply_to_message:
        await increment_user_field(message.from_user.id, chat_id, "replies_count", 1)
        await increment_user_field(message.from_user.id, chat_id, "board_reps", 1)

    user = await get_user(message.from_user.id, chat_id)
    if user["guild_id"]:
        await execute("""
            INSERT INTO guild_member_stats (guild_id, user_id, msgs, replies) 
            VALUES (?, ?, 1, ?) 
            ON CONFLICT(guild_id, user_id) DO UPDATE SET msgs = msgs + 1, replies = replies + ?
        """, (user["guild_id"], user["user_id"], 1 if message.reply_to_message else 0,
              1 if message.reply_to_message else 0))
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
        await execute("""
            INSERT INTO guild_member_stats (guild_id, user_id, stickers) 
            VALUES (?, ?, 1) 
            ON CONFLICT(guild_id, user_id) DO UPDATE SET stickers = stickers + 1
        """, (user["guild_id"], user["user_id"]))

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
        await execute("""
            INSERT INTO guild_member_stats (guild_id, user_id, photos) 
            VALUES (?, ?, 1) 
            ON CONFLICT(guild_id, user_id) DO UPDATE SET photos = photos + 1
        """, (user["guild_id"], user["user_id"]))


async def handle_interaction(message, user, matched_phrase, chat_id, custom_inter=None):
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

    # ===== СИСТЕМА УСЫНОВЛЕНИЯ =====
    if matched_phrase in ("усыновить", "удочерить"):
        if not user["is_married"] and user["child_id"]:
            await message.reply("👶 До брака можно усыновить только одного ребенка. Сыграйте свадьбу для второго!")
            return True

        if str(target_id) in str(user["child_id"]).split(","):
            await message.reply("👶 Вы уже усыновили этого игрока.")
            return True

        current_ids = str(user["child_id"]).split(",") if user["child_id"] else []
        current_names = str(user["child_name"]).split(",") if user["child_name"] else []

        current_ids = [i for i in current_ids if i != "0" and i != ""]
        current_names = [n for n in current_names if n != ""]

        if len(current_ids) >= 2:
            await message.reply("👶 У вас уже максимум детей (2).")
            return True

        current_ids.append(str(target_id))
        current_names.append(target["character_name"])

        new_id_str = ",".join(current_ids)
        new_name_str = ",".join(current_names)

        await update_user(message.from_user.id, chat_id, child_id=new_id_str, child_name=new_name_str)
        await update_user(target_id, chat_id, child_id=str(message.from_user.id), child_name=user["character_name"])

        verb = "усыновил" if user["gender"] == "male" else ("удочерил" if user["gender"] == "female" else "усыновил(а)")

        beautiful_text = (
            f"👨‍👩‍👧 СЧАСТЛИВАЯ СЕМЬЯ\n{DIV}\n\n"
            f"🎉 {esc(user['character_name'])} {verb} {esc(target['character_name'])}!\n"
            f"Теперь они одна семья. Орион плачет от умиления 💛\n\n"
            f"👶 Всего детей в семье: {len(current_ids)}/2"
        )

        await message.answer(beautiful_text, reply_markup=back_kb(message.from_user.id))
        return True

    if custom_inter:
        inter = {
            "emoji": custom_inter['emoji'],
            "verb_m": custom_inter.get('action_text') or custom_inter['name'],
            "verb_f": custom_inter.get('action_text') or custom_inter['name']
        }
        xp = 0
    else:
        inter = INTERACTIONS.get(matched_phrase)
        if not inter: return False

        xp = inter.get("xp", 0)
        if inter.get("pair_only"):
            if user["partner_id"] != target_id:
                await message.reply("💕 Это взаимодействие только для пары.")
                return True
            if xp:
                await update_user(message.from_user.id, chat_id, rel_xp=(user["rel_xp"] or 0) + xp)
                await update_user(target_id, chat_id, rel_xp=(target["rel_xp"] or 0) + xp)
                user = await get_user(message.from_user.id, chat_id)

    now = int(datetime.now(timezone.utc).timestamp())
    last = _inter_cooldown.get(message.from_user.id, 0)
    if now - last < 2:
        try:
            await message.delete()
        except:
            pass
        return True

    verb = inter["verb_f"] if user["gender"] == "female" else inter["verb_m"]
    emoji = inter["emoji"]
    xp_line = f"\n💕 +{xp} XP" if xp else ""

    original_text = message.text or ""

    text_lower = original_text.lower().strip()
    reply_text = original_text[len(matched_phrase):].strip()

    if isinstance(target_ref, str) and target_ref:
        reply_text = reply_text.replace(f"@{target_ref}", "").strip()

    sender_mention = f'<a href="tg://user?id={message.from_user.id}">{esc(user["character_name"])}</a>'
    target_mention = f'<a href="tg://user?id={target_id}">{esc(target["character_name"])}</a>'

    if text_lower == "подарить цветок":
        text = f"🌸 {sender_mention} {verb} цветок {target_mention}!"
    else:
        text = f"{emoji} {sender_mention} {verb} {target_mention}!{xp_line}"

    if reply_text:
        reply_text = reply_text.strip("()[] ")
        if reply_text:
            text += f"\n💬 <i>«{esc(reply_text)}»</i>"

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
        if user["gender"] == "male":
            partner_line = "❤️ Свободен"
        elif user["gender"] == "female":
            partner_line = "❤️ Свободна"
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
    from helpers import get_ranks_config

    rep_level = get_rep_level(user["reputation"])

    admin_rank_text = ""
    if user.get("user_id") == OWNER_ID:
        admin_rank_text = "👑 Должность: <b>Владелец</b>\n\n"
    elif user.get("admin_rank"):
        ranks = await get_ranks_config()
        r_data = ranks.get(user["admin_rank"])
        if r_data:
            emoji = "👑" if r_data.get("weight", 0) >= 80 else "🛡"
            raw_name = r_data.get("name", "").strip()
            for e in ["👑", "🛡", "⚔", "⚙", "🔨", "🔧", "📝"]:
                raw_name = raw_name.replace(e, "")
            clean_rank = raw_name.strip()
            admin_rank_text = f"{emoji} Должность: <b>{clean_rank}</b>\n\n"

    join_date = ""
    if user.get("first_seen"):
        fs = datetime.fromtimestamp(user["first_seen"], timezone.utc)
        join_date = f"📅 В группе с: {fs.day} {MONTHS[fs.month - 1]}\n"

    text = (
        f"🎭 {name} · ⚧ {gtext}\n"
        f"{admin_rank_text}"
        f"{join_date}\n"
        f"💬 Всего сообщений: {user['messages_count']}\n"
        f"☀️ За сегодня: {user.get('msgs_day', 0)}\n"
        f"📅 За неделю: {user.get('msgs_week', 0)}\n"
        f"🗓 За месяц: {user.get('msgs_month', 0)}\n\n"
        f"🎖️ Репутация: {rep_level} / 10\n"
        f"💰 Баланс: {user['balance']}\n\n"
        f"{partner_line}{child_line}\n"
        f"{guild_line}"
    )

    if len(text) > 1024:
        await message.answer(text, parse_mode="HTML", reply_markup=back_kb(message.from_user.id))
        return

    candidates = []
    if user["character_name"]: candidates.append(get_character_image(user["character_name"]))
    candidates.append(get_placeholder_image())
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

    from constants import TASKS

    for t_id in accepted:
        if t_id in claimed or t_id not in TASKS:
            continue
        t = TASKS[t_id]

        if get_progress(user, t["cat"]) >= t["need"]:
            coins_reward = random.randint(100, 300)
            # primo_reward = random.randint(20, 60) <--- УДАЛЕНО

            try:
                # 1. СНАЧАЛА начисляем награду
                await increment_user_field(message.from_user.id, chat_id, "balance", coins_reward)
                # await update_primogems(message.from_user.id, chat_id, primo_reward) <--- УДАЛЕНО
                await _gain_rep(message.from_user.id, chat_id, REP_PER_BOARD_TASK, message.from_user.first_name)

                # 2. ТОЛЬКО ПОСЛЕ ЭТОГО ставим отметку "получено"
                new_claimed = list(claimed) + [t_id]
                await update_user(message.from_user.id, chat_id, board_claimed=";".join(new_claimed))
                claimed = new_claimed

                # 3. Отправляем уведомление
                mention = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'
                await bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🎉 {mention}, задание выполнено!\n\n"
                        f"«{t['text']}»\n"
                        f"💰 Награда: {coins_reward} монет\n"
                        # f"💎 +{primo_reward} Примогемов\n" <--- УДАЛЕНО
                        f"🎖️ +{REP_PER_BOARD_TASK} репутации"
                    ),
                    parse_mode="HTML",
                    reply_markup=back_kb(message.from_user.id)
                )
            except Exception as e:
                print(f"Ошибка при выдаче награды за задание {t_id}: {e}")