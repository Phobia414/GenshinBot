from datetime import datetime, timezone, timedelta
import asyncio
import aiosqlite

from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import ChatPermissions
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from config import OWNER_ID, DB_PATH
from constants import DIV, WARN_LIMIT, WARN_MUTE_HOURS
from db import (
    get_user, create_user, update_user, add_warn, remove_warn,
    add_reputation, get_rep_level, RESIN_MAX, add_protected_user, remove_protected_user,
    update_primogems, get_guild_by_name, get_cleanup_settings, update_cleanup_settings,
    fetch_all, execute, fetch_one, add_trusted_admin, remove_trusted_admin
)
from helpers import (
    esc, is_chat_admin, _ensure_user, extract_target, resolve_user_id,
    get_ranks_config, has_permission, get_user_rank_data, parse_admin_target,
    apply_tg_rights, remove_tg_rights, _now_ts, update_user_tag
)
from keyboards import back_kb

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября",
          "декабря"]


# ==================== МОДЕРАЦИЯ ====================

async def check_mod_rights(message: types.Message, perm: str):
    if message.from_user.id == OWNER_ID: return True
    user = await get_user(message.from_user.id, message.chat.id)
    rank = await get_user_rank_data(user)
    if not has_permission(rank, perm):
        await message.reply(f"❌ У вас нет прав на эту команду ({perm}).")
        return False
    return True


async def log_action(chat_id, admin_name, action, target_id, reason):
    log_text = f"🛡 <b>ЛОГ МОДЕРАЦИИ</b>\n{DIV}\n👮‍♂️ Админ: {esc(admin_name)}\n⚔️ Действие: {action}\n🎯 Цель: <code>{target_id}</code>\n📝 Причина: {esc(reason)}"
    try:
        await bot.send_message(OWNER_ID, log_text, parse_mode="HTML")
    except:
        pass


@dp.message(Command("warn"))
async def cmd_warn(message: types.Message):
    if not await check_mod_rights(message, "warn"): return

    target_ref, reason = parse_admin_target(message)
    if not target_ref:
        return await message.reply("Используй: <code>/warn @user Причина</code> или ответом на сообщение.",
                                   parse_mode="HTML")

    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Игрок не найден.")
    if target_id == message.from_user.id: return await message.reply("❌ Себе нельзя.")

    user = await _ensure_user(target_id, message.chat.id)
    warns = await add_warn(target_id, message.chat.id, 1)
    mention = f'<a href="tg://user?id={target_id}">Игрок</a>'

    await log_action(message.chat.id, message.from_user.first_name, "Warn", target_id, reason)

    if warns >= WARN_LIMIT:
        mu = int((datetime.now(timezone.utc) + timedelta(hours=WARN_MUTE_HOURS)).timestamp())
        await update_user(target_id, message.chat.id, muted_until=mu, warns=0)
        try:
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=False), until_date=mu)
        except:
            pass
        await message.reply(
            f"⚠️ {mention} получил {WARN_LIMIT}-й варн и замучен на {WARN_MUTE_HOURS}ч.\nПричина: {reason}",
            parse_mode="HTML")
    else:
        await message.reply(f"⚠️ {mention} получил варн ({warns}/{WARN_LIMIT}).\nПричина: {reason}", parse_mode="HTML")


@dp.message(Command("unwarn"))
async def cmd_unwarn(message: types.Message):
    if not await check_mod_rights(message, "warn"): return
    target_ref, _ = parse_admin_target(message)
    if not target_ref: return await message.reply("Ответьте на сообщение или укажите @user.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Не найден.")

    warns = await remove_warn(target_id, message.chat.id, 1)
    await message.reply(f"✅ Снят 1 варн. Осталось: {warns}")


@dp.message(Command("mute"))
async def cmd_mute(message: types.Message):
    if not await check_mod_rights(message, "mute"): return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.reply("Используй: <code>/mute 15 Причина</code> (ответом или @user)", parse_mode="HTML")

    minutes = int(parts[1])
    rest_text = " ".join(parts[2:])

    target_ref = None
    reason = rest_text if rest_text else "Не указана"

    if message.reply_to_message:
        target_ref = message.reply_to_message.from_user.id
        reason = " ".join(parts[1:])
        if not reason: reason = "Не указана"
        minutes = 60
        if parts[1].isdigit():
            minutes = int(parts[1])
            reason = " ".join(parts[2:])
    elif len(parts) > 2 and parts[1].isdigit() and parts[2].startswith("@"):
        target_ref = parts[2]
        reason = " ".join(parts[3:])
    else:
        return await message.reply("Укажи время, юзера и причину.")

    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Игрок не найден.")

    mu = int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp())
    await update_user(target_id, message.chat.id, muted_until=mu)
    try:
        await bot.restrict_chat_member(message.chat.id, target_id, permissions=ChatPermissions(can_send_messages=False),
                                       until_date=mu)
        await message.reply(f"🔇 Игрок замучен на {minutes} мин.\nПричина: {reason}")
        await log_action(message.chat.id, message.from_user.first_name, f"Mute {minutes}m", target_id, reason)
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {e}")


@dp.message(Command("unmute"))
async def cmd_unmute(message: types.Message):
    if not await check_mod_rights(message, "mute"): return
    target_ref, _ = parse_admin_target(message)
    if not target_ref: return await message.reply("Ответьте на сообщение или укажите @user.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)

    await update_user(target_id, message.chat.id, muted_until=0)
    try:
        await bot.restrict_chat_member(message.chat.id, target_id, permissions=ChatPermissions(can_send_messages=True))
        await message.reply("🔊 Игрок размучен.")
    except Exception as e:
        await message.reply(f"⚠️ {e}")


@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if not await check_mod_rights(message, "ban"): return
    target_ref, reason = parse_admin_target(message)
    if not target_ref: return await message.reply("Ответьте на сообщение или укажите @user.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)

    try:
        await bot.ban_chat_member(message.chat.id, target_id)
        await message.reply(f"⛔ Игрок забанен.\nПричина: {reason}")
        await log_action(message.chat.id, message.from_user.first_name, "BAN", target_id, reason)
    except Exception as e:
        await message.reply(f"⚠️ {e}")


@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if not await check_mod_rights(message, "ban"): return
    target_ref, _ = parse_admin_target(message)
    if not target_ref: return await message.reply("Укажите @user или ID.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)

    try:
        await bot.unban_chat_member(message.chat.id, target_id)
        await message.reply("✅ Игрок разбанен.")
    except Exception as e:
        await message.reply(f"⚠️ {e}")


# ==================== НАЗНАЧЕНИЕ РАНГОВ ====================

@dp.message(F.text.startswith("!"))
async def cmd_set_rank(message: types.Message):
    if message.chat.type not in ("group", "supergroup"): return
    user = await get_user(message.from_user.id, message.chat.id)

    my_rank = await get_user_rank_data(user)
    if message.from_user.id == OWNER_ID:
        my_rank = {"weight": 100, "permissions": ["all"]}

    if not my_rank: return

    parts = message.text.split(maxsplit=1)
    cmd = parts[0].lower()

    ranks_config = await get_ranks_config()
    target_rank_key = None
    for r_key, r_data in ranks_config.items():
        if r_data.get("cmd", "").lower() == cmd:
            target_rank_key = r_key
            break

    if not target_rank_key: return

    target_rank_data = ranks_config[target_rank_key]

    if "all" not in my_rank["permissions"]:
        if "assign_lower" not in my_rank["permissions"]:
            return await message.reply("❌ У вас нет прав на назначение должностей.")
        if target_rank_data["weight"] >= my_rank["weight"]:
            return await message.reply("❌ Вы не можете выдать ранг равный или выше вашего.")

    target_ref, _ = parse_admin_target(message)
    if not target_ref:
        return await message.reply("Ответьте на сообщение игрока или укажите @username.")

    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Игрок не найден.")

    await _ensure_user(target_id, message.chat.id)
    await update_user(target_id, message.chat.id, admin_rank=target_rank_key)

    target_user = await get_user(target_id, message.chat.id)
    await apply_tg_rights(bot, message.chat.id, target_id, target_rank_data)

    await message.reply(f"✅ Игроку назначен ранг: <b>{target_rank_data['name']}</b>", parse_mode="HTML")


@dp.message(Command("unsetsrank"))
async def cmd_unset_rank(message: types.Message):
    user = await get_user(message.from_user.id, message.chat.id)
    my_rank = await get_user_rank_data(user)
    if message.from_user.id != OWNER_ID and not has_permission(my_rank, "assign_lower"):
        return await message.reply("❌ Нет прав.")

    target_ref, _ = parse_admin_target(message)
    if not target_ref: return await message.reply("Ответьте или укажите @user.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)

    await update_user(target_id, message.chat.id, admin_rank="")
    await remove_tg_rights(bot, message.chat.id, target_id)

    # Обновляем тег до обычного имени
    target_user = await get_user(target_id, message.chat.id)
    await update_user_tag(bot, message.chat.id, target_id, target_user)

    await message.reply("✅ С игрока сняты все админ-права.")


@dp.message(Command("resetstats"))
async def cmd_reset_stats(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("❌ Эта команда доступна только владельцу бота.")

    await execute("UPDATE users SET messages_count = 0, msgs_week = 0, msgs_month = 0")

    await message.answer(
        f"✅ <b>СБРОС СТАТИСТИКИ</b>\n{DIV}\n\n"
        f"Счётчики сообщений (всего, за неделю и за месяц) обнулены у всех.\n"
        f"Счетчик сообщений за сегодня (день) остался без изменений.",
        parse_mode="HTML"
    )


@dp.message(Command("kicklist", "cleanup_list"))
async def cmd_kicklist(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return await message.answer("❌ Только для групп.")
    if not await is_chat_admin(message.chat.id, message.from_user.id) and message.from_user.id != OWNER_ID:
        return await message.answer("❌ Только для админов.")

    chat_id = message.chat.id
    NORM_MSGS = 150

    users = await fetch_all(
        "SELECT user_id, username, character_name, msgs_week, first_seen FROM users "
        "WHERE chat_id = ? AND character_name IS NOT NULL AND character_name != '' "
        "ORDER BY IFNULL(msgs_week, 0) ASC",
        (chat_id,)
    )

    if not users:
        return await message.answer("В группе нет зарегистрированных участников.")

    now = datetime.now(timezone.utc)
    two_days_ago = now - timedelta(days=2)

    kick_list = []
    norm_list = []
    newbie_list = []

    for u in users:
        name = u['character_name']  # Без HTML-экранирования, чтобы не ломались теги
        msgs = u['msgs_week'] or 0
        username = u.get('username')

        # Если есть юзернейм - пишем его. Если нет - имя и ID.
        if username:
            user_link = f"@{username}"
        else:
            user_link = f"{name} (ID: {u['user_id']})"

        if u['first_seen']:
            fs = datetime.fromtimestamp(u['first_seen'], timezone.utc)
            date_str = f"{fs.day} {MONTHS[fs.month - 1]}"
        else:
            fs = now - timedelta(days=30)
            date_str = "неизвестно"

        if fs > two_days_ago:
            newbie_list.append(f"🛡 {user_link} — {msgs} сообщ. (С {date_str})")
        elif msgs >= NORM_MSGS:
            norm_list.append(f"✅ {user_link} — {msgs} сообщ.")
        else:
            kick_list.append(f"❌ {user_link} — {msgs} сообщ. (С {date_str})")

    # Формируем текст БЕЗ HTML (просто обычный текст)
    text = f"📋 СПИСОК ДЛЯ РУЧНОЙ ЧИСТКИ\n"
    text += f"Норма: {NORM_MSGS} сообщ. за неделю. Бот никого не кикает.\n\n"

    text += f"❌ Кандидаты на исключение ({len(kick_list)}):\n"
    if kick_list:
        text += "\n".join(kick_list[:40])
        if len(kick_list) > 40:
            text += f"\n... и еще {len(kick_list) - 40} чел."
    else:
        text += "Все молодцы, неактивных нет!\n"

    text += f"\n\n🛡 Защищенные новички (< 2 дней):\n"
    if newbie_list:
        text += "\n".join(newbie_list[:10])
    else:
        text += "Нет новичков.\n"

    text += f"\n\n✅ Набрали норму: {len(norm_list)} чел."

    # Обрезаем, если слишком длинно
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (сообщение обрезано)"

    # Отправляем БЕЗ parse_mode (как обычный текст)
    await message.answer(text)

@dp.message(Command("addmoney"))
async def cmd_addmoney(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /addmoney Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid, chat_id)
    if not user:
        await message.answer("❌ Нет пользователя")
        return
    await update_user(tid, chat_id, balance=user["balance"] + amount)
    await message.answer(f"✅ +{amount} монет. Баланс: {user['balance'] + amount}",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("setmoney"))
async def cmd_setmoney(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /setmoney Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid, chat_id)
    if not user:
        await message.answer("❌ Нет")
        return
    await update_user(tid, chat_id, balance=amount)
    await message.answer(f"✅ Баланс = {amount}", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("addrep"))
async def cmd_addrep(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /addrep Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid, chat_id)
    if not user:
        await message.answer("❌ Нет")
        return
    await add_reputation(tid, chat_id, amount)
    await message.answer(f"✅ +{amount} репутации. Всего: {(user['reputation'] or 0) + amount}",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("addresin"))
async def cmd_addresin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /addresin Сумма")
        return
    amount = int(parts[1])
    tid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(tid, chat_id)
    if not user:
        await message.answer("❌ Нет")
        return
    nr = min(RESIN_MAX, (user["resin"] or 0) + amount)
    await update_user(tid, chat_id, resin=nr)
    await message.answer(f"✅ Смола: {nr}/{RESIN_MAX}", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("addgems"))
async def cmd_addgems(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    chat_id = message.chat.id
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: `/addgems <сумма>` (ответом на сообщение) или `/addgems <сумма> @user`")
        return

    amount = int(parts[1])

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    elif len(parts) > 2:
        target_id = await resolve_user_id(parts[2])
        if not target_id:
            await message.answer("❌ Игрок не найден.")
            return
    else:
        target_id = message.from_user.id

    await update_primogems(target_id, chat_id, amount)
    await message.answer(f"✅ Выдано **{amount}** примогемов игроку <code>{target_id}</code>!", parse_mode="HTML",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("delguild"))
async def cmd_delguild(message: types.Message):
    if message.from_user.id != OWNER_ID: return
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используй: /delguild <Название>")
        return
    name = parts[1].strip()
    g = await get_guild_by_name(name, chat_id)
    if not g:
        await message.answer("❌ Гильдия не найдена.")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET guild_id = 0, guild_rank = 'Участник', guild_contribution = 0 WHERE guild_id = ? AND chat_id = ?",
            (g['guild_id'], chat_id))
        await db.execute("DELETE FROM guilds WHERE guild_id = ?", (g['guild_id'],))
        await db.execute("DELETE FROM guild_member_stats WHERE guild_id = ?", (g['guild_id'],))
        await db.commit()
    await message.answer(f"✅ Гильдия «{esc(name)}» удалена.", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("warn"), IsChatAdmin())
async def cmd_warn(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение нарушителя.")
        return
    chat_id = message.chat.id
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        await message.answer("❌ Себе нельзя.")
        return
    if target.is_bot:
        await message.answer("❌ Боту нельзя.")
        return
    user = await get_user(target.id, chat_id)
    if not user:
        await create_user(target.id, chat_id)
        user = await get_user(target.id, chat_id)
    warns = await add_warn(target.id, chat_id, 1)
    mention = f'【0†{esc(target.first_name)}†tg:】'
    if warns >= WARN_LIMIT:
        mu = int((datetime.now(timezone.utc) + timedelta(hours=WARN_MUTE_HOURS)).timestamp())
        await update_user(target.id, chat_id, muted_until=mu, warns=0)
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id, user_id=target.id,
                permissions=ChatPermissions(can_send_messages=False), until_date=mu
            )
        except Exception as e:
            await message.answer(f"⚠️ Мут не удался: {e}", reply_markup=back_kb(message.from_user.id))
            return
        await message.answer(f" {mention} получил 3 варна и замучен на 24 часа!", parse_mode="HTML",
                             reply_markup=back_kb(message.from_user.id))
    else:
        await message.answer(f"⚠️ {mention}: {warns}/{WARN_LIMIT}", parse_mode="HTML",
                             reply_markup=back_kb(message.from_user.id))


@dp.message(Command("unwarn"), IsChatAdmin())
async def cmd_unwarn(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение.")
        return
    chat_id = message.chat.id
    target = message.reply_to_message.from_user
    warns = await remove_warn(target.id, chat_id, 1)
    await message.answer(f"✅ Снято. Осталось: {warns}", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("mute"), IsChatAdmin())
async def cmd_mute(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение и напиши /mute <мин>")
        return
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /mute <мин>")
        return
    minutes = int(parts[1])
    if minutes <= 0 or minutes > 10080:
        await message.answer("❌ 1-10080")
        return
    target = message.reply_to_message.from_user
    if target.id == message.from_user.id:
        await message.answer("❌ Себе")
        return
    mu = int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp())
    await update_user(target.id, chat_id, muted_until=mu)
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id, user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False), until_date=mu
        )
    except Exception as e:
        await message.answer(f"⚠️ {e}", reply_markup=back_kb(message.from_user.id))
        return
    mention = f'【0†{esc(target.first_name)}†tg:】'
    await message.answer(f" {mention} замучен на {minutes} мин.", parse_mode="HTML",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("unmute"), IsChatAdmin())
async def cmd_unmute(message: types.Message):
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение.")
        return
    chat_id = message.chat.id
    target = message.reply_to_message.from_user
    await update_user(target.id, chat_id, muted_until=0)
    try:
        await bot.restrict_chat_member(
            chat_id=chat_id, user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True, can_change_info=False, can_invite_users=True, can_pin_messages=False
            )
        )
    except Exception as e:
        await message.answer(f"⚠️ {e}", reply_markup=back_kb(message.from_user.id))
        return
    await message.answer(f"✅ Размучен.", parse_mode="HTML", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("stats"), IsChatAdmin())
async def cmd_stats(message: types.Message):
    chat_id = message.chat.id
    tb = await get_top_balance(chat_id, 5)
    tm = await get_top_messages(chat_id, 5)
    tr = await get_top_reputation(chat_id, 5)
    lines = [f"📊 СТАТИСТИКА\n{DIV}\n", "🏆 ТОП-5 БАЛАНС"]
    for i, u in enumerate(tb, 1):
        lines.append(f"{i}. {esc(u['character_name'] or '?')} — {u['balance']}")
    lines.append("\n💬 ТОП-5 СООБЩЕНИЯ")
    for i, u in enumerate(tm, 1):
        lines.append(f"{i}. {esc(u['character_name'] or '?')} — {u['messages_count']}")
    lines.append("\n⭐ ТОП-5 РЕПУТАЦИЯ")
    for i, u in enumerate(tr, 1):
        lines.append(f"{i}. {esc(u['character_name'] or '?')} — ур. {get_rep_level(u['reputation'] or 0)}")
    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("protect"))
async def cmd_protect(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец.")
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь реплаем на сообщение того, кого хочешь защитить.")
        return
    chat_id = message.chat.id
    target = message.reply_to_message.from_user
    if target.id == OWNER_ID:
        await message.answer("❌ Себя защищать не надо.")
        return
    if target.is_bot:
        await message.answer("❌ Бота нельзя.")
        return
    await _ensure_user(target.id, chat_id)
    await add_protected_user(target.id, chat_id, message.from_user.id)
    await message.answer(
        f"✅ {esc(target.first_name)} теперь под защитой. Никто кроме тебя не сможет предложить ему отношения.",
        reply_markup=back_kb(message.from_user.id))


@dp.message(Command("unprotect"))
async def cmd_unprotect(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец.")
        return
    if not message.reply_to_message:
        await message.answer("❌ Ответь на сообщение.")
        return
    chat_id = message.chat.id
    target = message.reply_to_message.from_user
    await remove_protected_user(target.id, chat_id)
    await message.answer(f"✅ {esc(target.first_name)} больше не под защитой.",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("cleanup"))
async def cmd_cleanup(message: types.Message):
    if not await is_chat_admin(message.chat.id, message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    chat_id = message.chat.id
    settings = await get_cleanup_settings(chat_id)
    status = "Включена" if settings["enabled"] else "Выключена"
    last = datetime.fromtimestamp(settings['last_cleanup']).strftime('%d.%m.%Y %H:%M') if settings[
        'last_cleanup'] else 'Никогда'

    text = (f"🧹 АВТО-ЧИСТКА\n{DIV}\n\n"
            f"Статус: {status}\n"
            f"Мин. сообщений: {settings['min_messages']}\n"
            f"Частота: раз в {settings['frequency_days']} дн.\n"
            f"Последняя: {last}\n\n"
            f"Настройка: <code>/cleanup_set on 100 7</code>\n"
            f"(Вкл/Выкл, мин.сообщений, раз в N дней)\n\n"
            f"Посмотреть купивших защиту: /cleanup_list")
    await message.answer(text, parse_mode="HTML", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("cleanup_set"))
async def cmd_cleanup_set(message: types.Message):
    if not await is_chat_admin(message.chat.id, message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts) != 4:
        await message.answer("Формат: <code>/cleanup_set on 100 7</code>", parse_mode="HTML")
        return

    enabled_state = 1 if parts[1].lower() == "on" else 0
    try:
        min_msgs = int(parts[2])
        days = int(parts[3])
    except ValueError:
        await message.answer("Ошибка в числах.")
        return

    now_ts = int(datetime.now(timezone.utc).timestamp())

    await update_cleanup_settings(
        message.chat.id,
        enabled=enabled_state,
        min_messages=min_msgs,
        frequency_days=days,
        last_cleanup=now_ts
    )
    await message.answer("✅ Настройки авто-чистки обновлены. Таймер запущен заново.",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("cleanup_list"))
async def cmd_cleanup_list(message: types.Message):
    if not await is_chat_admin(message.chat.id, message.from_user.id) and message.from_user.id != OWNER_ID:
        return
    chat_id = message.chat.id
    users = await fetch_all(
        "SELECT user_id, character_name, rest_active, clean_exempt FROM users WHERE chat_id = ? AND (rest_active = 1 OR clean_exempt = 1)",
        (chat_id,)
    )
    if not users:
        await message.answer("Нет пользователей с активной защитой.", reply_markup=back_kb(message.from_user.id))
        return
    lines = [f"🛡 СПИСОК ЗАЩИЩЕННЫХ\n{DIV}\n"]
    for u in users:
        name = esc(u["character_name"] or "Игрок")
        tags = []
        if u["rest_active"]: tags.append("😴 Рест")
        if u["clean_exempt"]: tags.append("🧹 Чистка")
        lines.append(f"• {name} — {', '.join(tags)}")
    await message.answer("\n".join(lines), reply_markup=back_kb(message.from_user.id))


@dp.message(Command("applylink"))
async def cmd_applylink(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Эта команда работает только в группе.")
        return

    if not await is_chat_admin(message.chat.id, message.from_user.id) and message.from_user.id != OWNER_ID:
        await message.answer("❌ Только для администраторов группы.")
        return

    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=apply_{message.chat.id}"

    text = (
        f"🔗 <b>ССЫЛКА ДЛЯ НАБОРА В АНКЕТУ</b>\n{DIV}\n\n"
        f"Отправьте эту ссылку в рекламный пост. Все, кто по ней перейдут, "
        f"смогут заполнить анкету именно для вашей ролевой.\n\n"
        f"<code>{link}</code>\n\n"
        f"<i>Анкеты будут приходить в ЛС всем доверенным админам.</i>"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("trust"))
async def cmd_trust(message: types.Message):
    if message.from_user.id != OWNER_ID: return

    parts = message.text.split()
    if len(parts) < 2 and not message.reply_to_message:
        return await message.answer("Используй: <code>/trust @username</code> или ответом на сообщение",
                                    parse_mode="HTML")

    target_ref, display = extract_target(message)
    if target_ref is None:
        return await message.answer("❌ Ответь на сообщение или укажи @username")

    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            return await message.answer(f"❌ Не нашёл @{target_ref}")
    else:
        target_id = target_ref

    await add_trusted_admin(target_id)
    await message.answer(f"✅ Пользователь {esc(display)} теперь доверенный админ (будет получать анкеты).")


@dp.message(Command("untrust"))
async def cmd_untrust(message: types.Message):
    if message.from_user.id != OWNER_ID: return

    target_ref, display = extract_target(message)
    if target_ref is None:
        return await message.answer("❌ Ответь на сообщение или укажи @username")

    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            return await message.answer(f"❌ Не нашёл @{target_ref}")
    else:
        target_id = target_ref

    await remove_trusted_admin(target_id)
    await message.answer(f"✅ Пользователь {esc(display)} больше не получает анкеты.")