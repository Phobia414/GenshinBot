import asyncio
import logging
import random
from datetime import datetime, timezone

from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot_instance import bot, dp
from config import OWNER_ID, SENTRY_DSN, QUIZ_CHAT_ID
from db import (
    init_db, init_settings_db, load_custom_data_to_state, get_setting, init_known_groups_db,
    init_gacha_db, init_gacha_images_db, load_gacha_images,
    get_world_boss, set_world_boss, get_guild_boss, set_guild_boss, get_known_groups,
    fetch_all, execute, update_user
)
from bosses import WORLD_BOSSES, BOSS_ROTATION_DAY, BOSS_ROTATION_HOUR
from state import (
    _cb_cooldown, _cmd_cooldown, _propose_cooldown, _duel_cooldown,
    _boss_cooldown, _inter_cooldown, _call_cooldown
)
import state
from constants import CALL_COOLDOWN, QUIZ_QUESTIONS, QUIZ_WEIGHTS
from helpers import _now_ts
from logger import setup_logging, get_logger

from middlewares import *  # noqa: F401,F403
import handlers  # noqa: F401

log = get_logger(__name__)


async def set_bot_commands():
    user_commands = [
        BotCommand(command="start", description="Открыть главное меню"),
        BotCommand(command="propose", description="Предложить отношения"),
        BotCommand(command="duel", description="Дуэль"),
        BotCommand(command="call", description="📢 Созвать всех (в группе)"),
        BotCommand(command="callon", description="🔔 Включить уведомления позывного"),
        BotCommand(command="calloff", description="🔕 Отключить уведомления позывного"),
        BotCommand(command="createguild", description="Создать гильдию"),
        BotCommand(command="donate", description="Пополнить казну"),
        BotCommand(command="transfer_ally", description="Передать деньги союзу"),
        BotCommand(command="freerole", description="Освободить роль"),
        BotCommand(command="disbandguild", description="Распустить гильдию"),
        BotCommand(command="stats", description="Топы"),
        BotCommand(command="daily", description="Ежедневная награда"),
        BotCommand(command="gacha", description="Молитвы"),
        BotCommand(command="give", description="Передать примогемы"),
        BotCommand(command="cleanup", description="🧹 Настройки авто-чистки (для админов)"),
        BotCommand(command="cleanup_list", description="🛡 Кто купил защиту от чистки"),
        BotCommand(command="applylink", description="🔗 Создать ссылку для набора (для админов)"),
    ]
    try:
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    except Exception as e:
        log.error(f"set_my_commands (default) error: {e}")

    admin_commands = user_commands + [
        BotCommand(command="admin", description="⚙️ Админ-панель (ЛС)"),
        BotCommand(command="addmoney", description="[Админ] Начислить монеты"),
        BotCommand(command="setmoney", description="[Админ] Установить баланс"),
        BotCommand(command="addrep", description="[Админ] Начислить репутацию"),
        BotCommand(command="addresin", description="[Админ] Выдать смолу"),
        BotCommand(command="addgems", description="[Админ] Выдать примогемы"),
        BotCommand(command="warn", description="[Админ] Выдать предупреждение"),
        BotCommand(command="unwarn", description="[Админ] Снять предупреждение"),
        BotCommand(command="mute", description="[Админ] Мут"),
        BotCommand(command="unmute", description="[Админ] Размут"),
        BotCommand(command="protect", description="[Админ] Защитить юзера"),
        BotCommand(command="unprotect", description="[Админ] Снять защиту"),
    ]
    try:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=OWNER_ID))
    except Exception as e:
        log.error(f"set_my_commands (owner) error: {e}")


async def restore_chat_lists():
    """Автоматически обновляет списки ролей во всех привязанных каналах при запуске бота"""
    try:
        groups = await fetch_all(
            "SELECT group_id FROM group_channels WHERE channel_id IS NOT NULL AND message_id IS NOT NULL")
        from handlers.chat_list import update_chat_list

        for g in groups:
            try:
                await update_chat_list(g['group_id'])
            except Exception as e:
                log.error(f"Ошибка авто-обновления списка для группы {g['group_id']}: {e}")

        log.info(f"✅ Списки ролей обновлены в {len(groups)} каналах.")
    except Exception as e:
        log.error(f"Ошибка при восстановлении списков: {e}")


async def rotate_bosses():
    try:
        boss_name = random.choice(list(WORLD_BOSSES.keys()))
        boss = WORLD_BOSSES[boss_name]
        now_ts = int(datetime.now(timezone.utc).timestamp())

        groups = await get_known_groups()
        groups.append(0)

        for chat_id in groups:
            await set_world_boss(chat_id, boss_name, boss["hp"], now_ts)
            await set_guild_boss(chat_id, boss_name, boss["hp"], now_ts)

        log.info(f"🐉 Новый мировой босс: {boss_name} ({boss['hp']} HP) для всех чатов")
    except Exception as e:
        log.exception(f"Boss rotation error: {e}")


async def cleanup_cooldowns():
    try:
        now = _now_ts()
        for d, ttl in (
                (_cb_cooldown, 120), (_cmd_cooldown, 120), (_propose_cooldown, 120),
                (_duel_cooldown, 120), (_boss_cooldown, 120), (_inter_cooldown, 120),
                (_call_cooldown, CALL_COOLDOWN + 60),
        ):
            for k in list(d.keys()):
                try:
                    if now - d[k] > ttl:
                        del d[k]
                except Exception:
                    del d[k]
    except Exception as e:
        log.exception(f"cleanup_cooldowns error: {e}")


async def send_quiz_question():
    try:
        target_groups = []
        if QUIZ_CHAT_ID != OWNER_ID:
            target_groups = [QUIZ_CHAT_ID]
        else:
            target_groups = list(state._known_groups)

        if not target_groups:
            return

        for chat_id in target_groups:
            difficulties = ["easy", "medium", "hard"]
            difficulty = random.choices(difficulties, weights=QUIZ_WEIGHTS, k=1)[0]

            q_data = random.choice(QUIZ_QUESTIONS[difficulty])

            if difficulty == "easy":
                coins, primo, title = 50, 10, "🌱 ЛЕГКИЙ"
            elif difficulty == "medium":
                coins, primo, title = 100, 20, "⚖️ СРЕДНИЙ"
            else:
                coins, primo, title = 200, 40, "💀 СЛОЖНЫЙ"

            state._active_quizzes[chat_id] = {
                "question": q_data["q"],
                "answers": [a.lower().strip() for a in q_data["answers"]],
                "coins": coins,
                "primo": primo
            }

            text = (
                f"🧠 **ЕЖЕЧАСНАЯ ВИКТОРИНА!**\n"
                f"Сложность: **{title}**\n\n"
                f"❓ Вопрос: {q_data['q']}\n\n"
                f"💰 Награда: {coins} монет и **{primo} Примогемов** 💎!\n"
                f"⚡ Кто первый ответит в чат, тот и заберет награду!"
            )
            b = InlineKeyboardBuilder()
            b.button(text="✍️ Написать ответ", callback_data="quiz_answer")
            try:
                await bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=b.as_markup())
            except Exception as e:
                log.error(f"Не удалось отправить викторину в {chat_id}: {e}")
    except Exception as e:
        log.error(f"Глобальная ошибка викторины: {e}")


async def auto_cleanup_job():
    try:
        chats = await fetch_all("SELECT * FROM chat_cleanup_settings WHERE enabled = 1")
        now = int(datetime.now(timezone.utc).timestamp())

        for c in chats:
            if now - c["last_cleanup"] >= c["frequency_days"] * 86400:
                chat_id = c["chat_id"]
                min_msgs = c["min_messages"]

                admin_ids = set()
                try:
                    admins = await bot.get_chat_administrators(chat_id)
                    admin_ids = {a.user.id for a in admins}
                except Exception as e:
                    log.warning(f"Не удалось получить админов чата {chat_id}: {e}")
                    continue

                # НЕ КИКАЕМ ТЕХ, КТО ЗАШЕЛ МЕНЬШЕ 24 ЧАСОВ НАЗАД
                min_time_to_kick = now - 86400

                users_to_kick = await fetch_all(
                    "SELECT user_id FROM users WHERE chat_id = ? AND messages_count < ? "
                    "AND (rest_active = 0 OR rest_active IS NULL) "
                    "AND (clean_exempt = 0 OR clean_exempt IS NULL) "
                    "AND (first_seen < ? OR first_seen IS NULL)",
                    (chat_id, min_msgs, min_time_to_kick)
                )

                if users_to_kick:
                    kicked_count = 0
                    for u in users_to_kick:
                        if u["user_id"] in admin_ids or u["user_id"] == OWNER_ID:
                            continue

                        try:
                            await bot.ban_chat_member(chat_id, u["user_id"])
                            await bot.unban_chat_member(chat_id, u["user_id"])
                            await update_user(u["user_id"], chat_id, messages_count=0, character_name="")
                            kicked_count += 1
                        except Exception as e:
                            log.error(f"Не удалось исключить {u['user_id']} из {chat_id}: {e}")

                    if kicked_count > 0:
                        try:
                            await bot.send_message(
                                chat_id,
                                f"🧹 <b>АВТО-ЧИСТКА</b>\n\nИз группы было исключено <b>{kicked_count}</b> чел., не набравших {min_msgs} сообщений за {c['frequency_days']} дн.\n\nКупить рест или защиту от чистки можно в лавке!",
                                parse_mode="HTML"
                            )
                        except:
                            pass

                await execute("UPDATE chat_cleanup_settings SET last_cleanup = ? WHERE chat_id = ?", (now, chat_id))
                log.info(f"🧹 Авто-чистка проведена в чате {chat_id}. Исключено: {kicked_count if users_to_kick else 0}")

    except Exception as e:
        log.exception(f"Auto cleanup error: {e}")


async def reset_weekly_stats():
    try:
        await execute("UPDATE users SET msgs_week = 0")
        log.info("📊 Недельная статистика сообщений сброшена.")
    except Exception as e:
        log.error(f"Ошибка сброса недельной статистики: {e}")


async def reset_monthly_stats():
    try:
        await execute("UPDATE users SET msgs_month = 0")
        log.info("📊 Месячная статистика сообщений сброшена.")
    except Exception as e:
        log.error(f"Ошибка сброса месячной статистики: {e}")


def setup_sentry():
    if not SENTRY_DSN:
        return
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1, profiles_sample_rate=0.1, send_default_pii=True)
    except Exception:
        pass


async def main():
    setup_logging()
    log.info("=== БОТ ЗАПУСКАЕТСЯ ===")
    setup_sentry()

    await init_db()
    await init_settings_db()
    await init_known_groups_db()
    await init_gacha_db()
    await init_gacha_images_db()
    await load_gacha_images()
    await load_custom_data_to_state()

    hidden_str = await get_setting("hidden_buttons", "")
    if hidden_str:
        state._hidden_buttons = set(hidden_str.split(","))

    log.info("✅ База данных инициализирована")

    groups = await get_known_groups()
    groups.append(0)

    for chat_id in groups:
        wb = await get_world_boss(chat_id)
        if not wb or not wb["boss_name"]:
            boss_name = random.choice(list(WORLD_BOSSES.keys()))
            boss = WORLD_BOSSES[boss_name]
            now_ts = int(datetime.now(timezone.utc).timestamp())
            await set_world_boss(chat_id, boss_name, boss["hp"], now_ts)
            await set_guild_boss(chat_id, boss_name, boss["hp"], now_ts)

    await restore_chat_lists()
    await set_bot_commands()

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(rotate_bosses, CronTrigger(day_of_week="sat", hour=BOSS_ROTATION_HOUR, minute=0),
                      id="boss_rotation", misfire_grace_time=3600)

    scheduler.add_job(cleanup_cooldowns, IntervalTrigger(hours=1), id="cleanup_cooldowns")
    scheduler.add_job(send_quiz_question, CronTrigger(minute=0), id="hourly_quiz", misfire_grace_time=300)
    scheduler.add_job(auto_cleanup_job, IntervalTrigger(hours=1), id="auto_cleanup")

    # Сброс статистики
    scheduler.add_job(reset_weekly_stats, CronTrigger(day_of_week="mon", hour=0, minute=0), id="reset_week")
    scheduler.add_job(reset_monthly_stats, CronTrigger(day=1, hour=0, minute=0), id="reset_month")

    scheduler.start()

    log.info("=== БОТ ЗАПУЩЕН ===")
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    try:
        await dp.start_polling(bot)
    finally:
        log.info("=== ОСТАНОВКА БОТА ===")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Бот остановлен пользователем")