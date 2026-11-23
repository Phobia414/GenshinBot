from datetime import datetime, timezone, timedelta
import asyncio
import aiosqlite
import re

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
    fetch_all, execute, fetch_one, add_trusted_admin, remove_trusted_admin,
    add_user_warn, get_active_warns, clear_user_warns, remove_last_warn
)
from helpers import (
    esc, is_chat_admin, _ensure_user, extract_target, resolve_user_id,
    get_ranks_config, has_permission, get_user_rank_data, parse_admin_target,
    apply_tg_rights, remove_tg_rights, _now_ts, update_user_tag
)
from keyboards import back_kb

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября",
          "декабря"]


# ==================== МОДЕРАЦИЯ (WARN / MUTE / BAN) ====================

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

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return await message.reply(
            "⚠️ Вы ответили на сообщение бота. Ответьте на сообщение игрока или укажите @username.")

    target_ref, _ = parse_admin_target(message)
    if not target_ref:
        return await message.reply(
            "Используй: <code>/warn 1d Причина</code> (ответом) или <code>/warn @user 1d Причина</code>",
            parse_mode="HTML")

    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Игрок не найден.")
    if target_id == message.from_user.id: return await message.reply("❌ Себе нельзя.")

    # Парсим время и причину
    parts = message.text.split()
    args = parts[1:] if message.reply_to_message else parts[2:]

    duration_seconds = 0
    reason = "Не указана"

    if args:
        time_match = re.match(r"^(\d+)([mhd])$", args[0].lower())
        if time_match:
            amount = int(time_match.group(1))
            unit = time_match.group(2)
            if unit == 'm':
                duration_seconds = amount * 60
            elif unit == 'h':
                duration_seconds = amount * 3600
            elif unit == 'd':
                duration_seconds = amount * 86400
            reason = " ".join(args[1:])
        else:
            reason = " ".join(args)

    expires_at = 0
    if duration_seconds > 0:
        expires_at = int((datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)).timestamp())

    await add_user_warn(target_id, message.chat.id, message.from_user.id, f"[ВАРН] {reason}", expires_at)

    active_warns = await get_active_warns(target_id, message.chat.id)
    warns_count = len(active_warns)

    mention = f'<a href="tg://user?id={target_id}">Игрок</a>'

    exp_str = ""
    if duration_seconds > 0:
        if duration_seconds >= 86400:
            exp_str = f" (сгорит через {duration_seconds // 86400} дн.)"
        elif duration_seconds >= 3600:
            exp_str = f" (сгорит через {duration_seconds // 3600} ч.)"
        else:
            exp_str = f" (сгорит через {duration_seconds // 60} мин.)"
    else:
        exp_str = " (навсегда)"

    await log_action(message.chat.id, message.from_user.first_name, f"Warn", target_id, reason)

    if warns_count >= WARN_LIMIT:
        mu = int((datetime.now(timezone.utc) + timedelta(hours=WARN_MUTE_HOURS)).timestamp())
        await update_user(target_id, message.chat.id, muted_until=mu)
        await clear_user_warns(target_id, message.chat.id)
        try:
            await bot.restrict_chat_member(message.chat.id, target_id,
                                           permissions=ChatPermissions(can_send_messages=False), until_date=mu)
        except:
            pass
        await message.reply(
            f"⚠️ {mention} получил {WARN_LIMIT}-й варн и замучен на {WARN_MUTE_HOURS}ч.\nПричина: {reason}",
            parse_mode="HTML")
    else:
        await message.reply(f"⚠️ {mention} получил варн ({warns_count}/{WARN_LIMIT}){exp_str}.\nПричина: {reason}",
                            parse_mode="HTML")


@dp.message(Command("unwarn"))
async def cmd_unwarn(message: types.Message):
    if not await check_mod_rights(message, "warn"): return

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return await message.reply(
            "⚠️ Вы ответили на сообщение бота. Ответьте на сообщение игрока или укажите @username.")

    target_ref, _ = parse_admin_target(message)
    if not target_ref: return await message.reply("Ответьте на сообщение или укажите @user.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Не найден.")

    await remove_last_warn(target_id, message.chat.id)
    active_warns = await get_active_warns(target_id, message.chat.id)
    await message.reply(f"✅ Снят 1 последний варн. Осталось активных: {len(active_warns)}")


@dp.message(Command("mute"))
async def cmd_mute(message: types.Message):
    if not await check_mod_rights(message, "mute"): return

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return await message.reply(
            "⚠️ Вы ответили на сообщение бота. Ответьте на сообщение игрока или укажите @username.")

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
    if target_id == bot.id: return await message.reply("❌ Бота мутить нельзя.")

    mu = int((datetime.now(timezone.utc) + timedelta(minutes=minutes)).timestamp())
    await update_user(target_id, message.chat.id, muted_until=mu)
    await add_user_warn(target_id, message.chat.id, message.from_user.id, f"[МУТ на {minutes} мин.] {reason}", mu)
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

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return await message.reply(
            "⚠️ Вы ответили на сообщение бота. Ответьте на сообщение игрока или укажите @username.")

    target_ref, _ = parse_admin_target(message)
    if not target_ref: return await message.reply("Ответьте на сообщение или укажите @user.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)

    if target_id == bot.id: return await message.reply("❌ Я не могу размутить сам себя (я и так не замучен).")

    await update_user(target_id, message.chat.id, muted_until=0)
    try:
        await bot.restrict_chat_member(message.chat.id, target_id, permissions=ChatPermissions(can_send_messages=True))
        await message.reply("🔊 Игрок размучен.")
    except Exception as e:
        await message.reply(f"⚠️ {e}")


@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if not await check_mod_rights(message, "ban"): return

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return await message.reply(
            "⚠️ Вы ответили на сообщение бота. Ответьте на сообщение игрока или укажите @username.")

    target_ref, reason = parse_admin_target(message)
    if not target_ref: return await message.reply("Ответьте на сообщение или укажите @user.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)

    if target_id == bot.id: return await message.reply("❌ Меня забанить нельзя!")

    try:
        await bot.ban_chat_member(message.chat.id, target_id)
        await add_user_warn(target_id, message.chat.id, message.from_user.id, f"[БАН] {reason}", 0)
        await message.reply(f"⛔ Игрок забанен.\nПричина: {reason}")
        await log_action(message.chat.id, message.from_user.first_name, "BAN", target_id, reason)
    except Exception as e:
        await message.reply(f"⚠️ {e}")


@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if not await check_mod_rights(message, "ban"): return

    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        return await message.reply(
            "⚠️ Вы ответили на сообщение бота. Ответьте на сообщение игрока или укажите @username.")

    target_ref, _ = parse_admin_target(message)
    if not target_ref: return await message.reply("Укажите @user или ID.")
    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)

    try:
        await bot.unban_chat_member(message.chat.id, target_id)
        await message.reply("✅ Игрок разбанен.")
    except Exception as e:
        await message.reply(f"⚠️ {e}")


# ==================== НАЗНАЧЕНИЕ И СНЯТИЕ РАНГОВ ====================

# ВАЖНО: Добавлен фильтр ~F.text.startswith("!снять"), чтобы эта функция не перехватывала команду снятия
@dp.message(F.text.startswith("!") & ~F.text.startswith("!снять"))
async def cmd_set_rank(message: types.Message):
    if message.chat.type not in ("group", "supergroup"): return
    user = await get_user(message.from_user.id, message.chat.id)

    my_rank = await get_user_rank_data(user)
    if message.from_user.id == OWNER_ID:
        my_rank = {"weight": 100, "permissions": ["all"]}

    if not my_rank: return

    if message.from_user.id != OWNER_ID and my_rank.get("weight", 0) < 80:
        return await message.reply("❌ Выдавать должности может только Гл. Админ и выше.")

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

    if message.from_user.id != OWNER_ID:
        if target_rank_data["weight"] >= my_rank["weight"]:
            return await message.reply("❌ Вы не можете выдать ранг равный или выше вашего.")

    target_ref, _ = parse_admin_target(message)
    if not target_ref:
        return await message.reply("Ответьте на сообщение игрока или укажите @username.")

    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Игрок не найден.")

    try:
        await _ensure_user(target_id, message.chat.id)

        await update_user(target_id, message.chat.id, admin_rank=target_rank_key)
        target_user = await get_user(target_id, message.chat.id)

        err1 = await apply_tg_rights(bot, message.chat.id, target_id, target_rank_data)

        await asyncio.sleep(2)

        await update_user_tag(bot, message.chat.id, target_id, target_user)

        await message.reply(f"✅ Игроку назначен ранг: <b>{target_rank_data['name']}</b>\n{err1 if err1 else ''}",
                            parse_mode="HTML")

    except Exception as e:
        await message.reply(f"⚠️ Ошибка при выдаче ранга: {e}")


@dp.message(Command("demote"))
@dp.message(F.text.startswith("!снять"))
async def cmd_demote(message: types.Message):
    chat_id = message.chat.id

    # Проверка прав
    if message.from_user.id != OWNER_ID:
        user = await get_user(message.from_user.id, chat_id)
        if not user or user.get("admin_rank") in (None, "", "Игрок"):
            return await message.answer("❌ У вас нет прав для снятия должностей.")

    # Определяем цель
    target_ref, reason = parse_admin_target(message)
    if not target_ref:
        return await message.answer(
            "❌ Используй: <code>/demote</code> (ответом на сообщение) или <code>/demote @username</code>",
            parse_mode="HTML")

    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            return await message.answer("❌ Пользователь не найден в базе.")
    else:
        target_id = target_ref

    if target_id == OWNER_ID:
        return await message.answer("❌ Нельзя снять должность с владельца бота.")

    target_user = await get_user(target_id, chat_id)
    if not target_user:
        return await message.answer("❌ Пользователь не найден в базе этого чата.")

    if target_user.get("admin_rank") in (None, "", "Игрок"):
        return await message.answer("❌ У этого пользователя и так нет должности.")

    # 1. Снимаем ранг в базе
    await update_user(target_id, chat_id, admin_rank="Игрок")

    # 2. Снимаем права админа в Телеграме
    await remove_tg_rights(bot, chat_id, target_id)

    # 3. ЗАНОВО ПОЛУЧАЕМ ПОЛЬЗОВАТЕЛЯ ИЗ БАЗЫ (чтобы убрать старый ранг из тега)
    target_user = await get_user(target_id, chat_id)

    # 4. Обновляем тег в Telegram
    await update_user_tag(bot, chat_id, target_id, target_user)

    mention = f'<a href="tg://user?id={target_id}">{target_user.get("character_name") or "Игрок"}</a>'
    await message.answer(
        f"✅ С пользователя {mention} снята должность.\nТеперь он снова обычный игрок.",
        parse_mode="HTML",
        reply_markup=back_kb(message.from_user.id)
    )


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

    target_user = await get_user(target_id, message.chat.id)
    await update_user_tag(bot, message.chat.id, target_id, target_user)

    await message.reply("✅ С игрока сняты все админ-права.")


# ==================== ЧИСТКА И СТАТИСТИКА ====================

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
    four_days_ago = now - timedelta(days=4)

    kick_list = []
    norm_list = []
    newbie_list = []

    for u in users:
        name = u['character_name']
        msgs = u['msgs_week'] or 0
        username = u.get('username')

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

        if fs > four_days_ago:
            newbie_list.append(f"🛡 {user_link} — {msgs} сообщ. (С {date_str})")
        elif msgs >= NORM_MSGS:
            norm_list.append(f"✅ {user_link} — {msgs} сообщ.")
        else:
            kick_list.append(f"❌ {user_link} — {msgs} сообщ. (С {date_str})")

    text = f"📋 СПИСОК ДЛЯ РУЧНОЙ ЧИСТКИ\n"
    text += f"Норма: {NORM_MSGS} сообщ. за неделю. Бот никого не кикает.\n\n"

    text += f"❌ Кандидаты на исключение ({len(kick_list)}):\n"
    if kick_list:
        text += "\n".join(kick_list[:40])
        if len(kick_list) > 40:
            text += f"\n... и еще {len(kick_list) - 40} чел."
    else:
        text += "Все молодцы, неактивных нет!\n"

    text += f"\n\n🛡 Защищенные новички (< 4 дней):\n"
    if newbie_list:
        text += "\n".join(newbie_list[:10])
    else:
        text += "Нет новичков.\n"

    text += f"\n\n✅ Набрали норму: {len(norm_list)} чел."

    if len(text) > 4000:
        text = text[:4000] + "\n\n... (сообщение обрезано)"

    await message.answer(text)


@dp.message(Command("resetstats"))
async def cmd_reset_stats(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("❌ Эта команда доступна только владельцу бота.")

    b = InlineKeyboardBuilder()
    b.button(text="Сбросить День", callback_data="resetstats_day")
    b.button(text="Сбросить Неделю", callback_data="resetstats_week")
    b.button(text="Сбросить Месяц", callback_data="resetstats_month")
    b.button(text="Сбросить ВСЁ", callback_data="resetstats_all")
    b.adjust(1)

    await message.answer(
        f"⚠️ <b>ВЫБЕРИТЕ, ЧТО СБРОСИТЬ</b>\n{DIV}\n"
        f"<i>Действие нельзя отменить!</i>",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("resetstats_"))
async def cb_resetstats_confirm(query: types.CallbackQuery):
    if query.from_user.id != OWNER_ID: return

    action = query.data.replace("resetstats_", "")

    # Если это уже подтверждение
    if action.startswith("confirm_"):
        target = action.replace("confirm_", "")

        if target == "day":
            await execute("UPDATE users SET msgs_day = 0")
            msg = "Ежедневная статистика сброшена."
        elif target == "week":
            await execute("UPDATE users SET msgs_week = 0")
            msg = "Недельная статистика сброшена."
        elif target == "month":
            await execute("UPDATE users SET msgs_month = 0")
            msg = "Месячная статистика сброшена."
        elif target == "all":
            await execute("UPDATE users SET messages_count = 0, msgs_day = 0, msgs_week = 0, msgs_month = 0")
            msg = "ВСЯ статистика (день, неделя, месяц, всего) сброшена."

        await query.message.edit_text(f"✅ <b>УСПЕШНО</b>\n{DIV}\n{msg}", parse_mode="HTML")
        return

    # Иначе показываем подтверждение
    names = {"day": "ЗА ДЕНЬ", "week": "ЗА НЕДЕЛЮ", "month": "ЗА МЕСЯЦ", "all": "ЗА ВСЁ ВРЕМЯ"}
    b = InlineKeyboardBuilder()
    b.button(text="✅ Да, сбросить", callback_data=f"resetstats_confirm_{action}")
    b.button(text="❌ Отмена", callback_data="resetstats_cancel")
    b.adjust(2)

    await query.message.edit_text(
        f"⚠️ <b>ПОДТВЕРЖДЕНИЕ</b>\n{DIV}\n"
        f"Вы точно хотите сбросить статистику <b>{names.get(action, action)}</b> у всех игроков?",
        reply_markup=b.as_markup(), parse_mode="HTML"
    )


@dp.callback_query(F.data == "resetstats_cancel")
async def cb_resetstats_cancel(query: types.CallbackQuery):
    if query.from_user.id != OWNER_ID: return
    await query.message.edit_text("❌ Сброс статистики отменен.")

# ==================== ЭКОНОМИКА И ВЛАДЕЛЕЦ ====================

@dp.message(Command("addmoney"))
async def cmd_addmoney(message: types.Message):
    if message.from_user.id != OWNER_ID:
        await message.answer("❌ Только владелец")
        return
    chat_id = message.chat.id

    target_ref, display = extract_target(message)

    if target_ref is None:
        # Если не указан юзер, выдаем себе
        target_id = message.from_user.id
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer(
                "Используй: <code>/addmoney Сумма</code> (ответом на сообщение) или <code>/addmoney @username Сумма</code>",
                parse_mode="HTML")
            return
        amount = int(parts[1])
    else:
        # Если юзер указан, берем последнее слово как сумму
        if isinstance(target_ref, str):
            target_id = await resolve_user_id(target_ref)
            if not target_id:
                await message.answer("❌ Игрок не найден.")
                return
        else:
            target_id = target_ref

        parts = message.text.split()
        if not parts[-1].isdigit():
            await message.answer("Укажи сумму в конце.")
            return
        amount = int(parts[-1])

    user = await get_user(target_id, chat_id)
    if not user:
        await _ensure_user(target_id, chat_id)
        user = await get_user(target_id, chat_id)

    await update_user(target_id, chat_id, balance=user["balance"] + amount)

    mention = f'<a href="tg://user?id={target_id}">{esc(user["character_name"] or display or "Игрок")}</a>'
    await message.answer(
        f"✅ Выдано <b>+{amount}</b> монет игроку {mention}.\n💰 Новый баланс: <b>{user['balance'] + amount}</b>",
        parse_mode="HTML", reply_markup=back_kb(message.from_user.id))


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


# ==================== АВТО-ЧИСТКА И ДОВЕРЕННЫЕ ====================

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
            f"Посмотреть купивших защиту: /cleanup_protected")
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
    )
    await message.answer("✅ Настройки авто-чистки обновлены. Таймер запущен заново.",
                         reply_markup=back_kb(message.from_user.id))


@dp.message(Command("cleanup_protected"))
async def cmd_cleanup_protected(message: types.Message):
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


@dp.message(Command("resetapps"))
async def cmd_reset_apps(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return

    # Определяем, кому сбрасываем
    target_ref, _ = extract_target(message)
    if target_ref is None:
        target_id = message.from_user.id
    elif isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
    else:
        target_id = target_ref

    if not target_id:
        return await message.answer("❌ Пользователь не найден.")

    from db import reset_user_applications
    await reset_user_applications(target_id)

    await message.answer(
        f"✅ <b>АНКЕТЫ СБРОШЕНЫ</b>\n{DIV}\n"
        f"Пользователь <code>{target_id}</code> теперь может подать анкеты заново.",
        parse_mode="HTML", reply_markup=back_kb(message.from_user.id)
    )
# ==================== ИСТОРИЯ НАРУШЕНИЙ ====================

@dp.message(Command("mywarns"))
async def cmd_mywarns(message: types.Message):
    chat_id = message.chat.id
    warns = await get_user_warns(message.from_user.id, chat_id)

    if not warns:
        return await message.answer("✅ У вас нет истории нарушений в этом чате.", reply_markup=back_kb(message.from_user.id))

    lines = [f"📋 <b>ВАША ИСТОРИЯ НАРУШЕНИЙ</b>\n{DIV}\n"]
    now = int(datetime.now(timezone.utc).timestamp())

    # Показываем последние 10 записей, чтобы не превысить лимит сообщения
    for w in warns[:10]:
        admin = await get_user(w['admin_id'], chat_id)
        admin_name = admin['character_name'] if admin and admin['character_name'] else "Неизвестный"
        date = datetime.fromtimestamp(w['created_at'], timezone.utc).strftime('%d.%m.%Y %H:%M')

        if w['expires_at'] == 0:
            status = "⛔ Навсегда"
        elif w['expires_at'] > now:
            left = (w['expires_at'] - now) // 60
            if left > 60:
                status = f"🟢 Активно (осталось {left // 60} ч.)"
            else:
                status = f"🟢 Активно (осталось {left} мин.)"
        else:
            status = "🔴 Истекло"

        lines.append(f"📅 {date} | {status}\n👮 Админ: {esc(admin_name)}\n📝 {esc(w['reason'])}\n")

    if len(warns) > 10:
        lines.append(f"... и еще {len(warns) - 10} записей.")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back_kb(message.from_user.id))


@dp.message(Command("warns"))
async def cmd_check_warns(message: types.Message):
    if not await check_mod_rights(message, "warn"): return

    target_ref, display = parse_admin_target(message)
    if not target_ref:
        return await message.reply("Используй: <code>/warns @user</code> или ответом на сообщение", parse_mode="HTML")

    target_id = target_ref if isinstance(target_ref, int) else await resolve_user_id(target_ref)
    if not target_id: return await message.reply("❌ Игрок не найден.")

    warns = await get_user_warns(target_id, message.chat.id)
    if not warns:
        return await message.reply(f"✅ У игрока {esc(display)} нет нарушений.")

    lines = [f"📋 <b>ИСТОРИЯ НАРУШЕНИЙ: {esc(display)}</b>\n{DIV}\n"]
    now = int(datetime.now(timezone.utc).timestamp())

    for w in warns[:10]:
        admin = await get_user(w['admin_id'], message.chat.id)
        admin_name = admin['character_name'] if admin and admin['character_name'] else "Неизвестный"
        date = datetime.fromtimestamp(w['created_at'], timezone.utc).strftime('%d.%m.%Y %H:%M')

        if w['expires_at'] == 0:
            status = "⛔ Навсегда"
        elif w['expires_at'] > now:
            left = (w['expires_at'] - now) // 60
            if left > 60:
                status = f"🟢 Активно (осталось {left // 60} ч.)"
            else:
                status = f"🟢 Активно (осталось {left} мин.)"
        else:
            status = "🔴 Истекло"

        lines.append(f"📅 {date} | {status}\n👮 Админ: {esc(admin_name)}\n📝 {esc(w['reason'])}\n")

    if len(warns) > 10:
        lines.append(f"... и еще {len(warns) - 10} записей.")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back_kb(message.from_user.id))