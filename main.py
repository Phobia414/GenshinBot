import asyncio
import logging
import random
from datetime import datetime, timezone

from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot_instance import bot, dp
from config import OWNER_ID, SENTRY_DSN
from db import (
    init_db, get_world_boss, set_world_boss, get_guild_boss, set_guild_boss,
)
from bosses import WORLD_BOSSES, BOSS_ROTATION_DAY, BOSS_ROTATION_HOUR
from state import (
    _cb_cooldown, _cmd_cooldown, _propose_cooldown, _duel_cooldown,
    _boss_cooldown, _inter_cooldown, _call_cooldown,
)
from constants import CALL_COOLDOWN
from helpers import _now_ts
from logger import setup_logging, get_logger

# Импорт middlewares регистрирует middleware на dp
from middlewares import *  # noqa: F401,F403

# Импорт handlers регистрирует все handlers на dp
import handlers  # noqa: F401


log = get_logger(__name__)


# ==================== КОМАНДЫ В МЕНЮ TELEGRAM ====================
async def set_bot_commands():
    user_commands = [
        BotCommand(command="start",        description="Открыть главное меню"),
        BotCommand(command="propose",      description="Предложить отношения"),
        BotCommand(command="duel",         description="Дуэль"),
        BotCommand(command="call",         description="📢 Созвать всех (в группе)"),
        BotCommand(command="callon",       description="🔔 Включить уведомления позывного"),
        BotCommand(command="calloff",      description="🔕 Отключить уведомления позывного"),
        BotCommand(command="createguild",  description="Создать гильдию"),
        BotCommand(command="donate",       description="Пополнить казну"),
        BotCommand(command="freerole",     description="Освободить роль"),
        BotCommand(command="disbandguild", description="Распустить гильдию"),
        BotCommand(command="stats",        description="Топы"),
    ]
    try:
        await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    except Exception as e:
        log.error(f"set_my_commands (default) error: {e}")

    admin_commands = user_commands + [
        BotCommand(command="addmoney",     description="[Админ] Начислить монеты"),
        BotCommand(command="setmoney",     description="[Админ] Установить баланс"),
        BotCommand(command="addrep",       description="[Админ] Начислить репутацию"),
        BotCommand(command="addresin",     description="[Админ] Выдать смолу"),
        BotCommand(command="warn",         description="[Админ] Выдать предупреждение"),
        BotCommand(command="unwarn",       description="[Админ] Снять предупреждение"),
        BotCommand(command="mute",         description="[Админ] Мут"),
        BotCommand(command="unmute",       description="[Админ] Размут"),
        BotCommand(command="protect",      description="[Админ] Защитить юзера"),
        BotCommand(command="unprotect",    description="[Админ] Снять защиту"),
        BotCommand(command="checkimages",  description="[Админ] Проверить ссылки картинок"),
    ]
    try:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=OWNER_ID))
    except Exception as e:
        log.error(f"set_my_commands (owner) error: {e}")


# ==================== ПЛАНИРОВЩИК ЗАДАЧ ====================
async def rotate_bosses():
    """Ротация мирового и гильдейского босса. Запускается раз в неделю."""
    try:
        boss_name = random.choice(list(WORLD_BOSSES.keys()))
        boss = WORLD_BOSSES[boss_name]
        now_ts = int(datetime.now(timezone.utc).timestamp())
        await set_world_boss(boss_name, boss["hp"], now_ts)
        await set_guild_boss(boss_name, boss["hp"], now_ts)
        log.info(f"🐉 Новый мировой босс: {boss_name} ({boss['hp']} HP)")
    except Exception as e:
        log.exception(f"Boss rotation error: {e}")


async def cleanup_cooldowns():
    """Очистка старых записей из словарей кулдаунов. Запускается раз в час."""
    try:
        now = _now_ts()
        for d, ttl in (
            (_cb_cooldown, 120),
            (_cmd_cooldown, 120),
            (_propose_cooldown, 120),
            (_duel_cooldown, 120),
            (_boss_cooldown, 120),
            (_inter_cooldown, 120),
            (_call_cooldown, CALL_COOLDOWN + 60),
        ):
            for k in list(d.keys()):
                try:
                    if now - d[k] > ttl:
                        del d[k]
                except Exception:
                    del d[k]
        log.debug("Кулдауны очищены")
    except Exception as e:
        log.exception(f"cleanup_cooldowns error: {e}")


# ==================== SENTRY ====================
def setup_sentry():
    """Инициализация Sentry. Если SENTRY_DSN пустой — тихо пропускаем."""
    if not SENTRY_DSN:
        log.info("ℹ️ Sentry отключён (SENTRY_DSN не задан)")
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            # Логи уровня ERROR автоматически уходят как события
            # Логи уровня INFO+ попадают в breadcrumbs
            send_default_pii=True,
        )
        log.info("✅ Sentry подключён — ошибки будут отправляться на сервер")
    except ImportError as e:
        log.warning(f"⚠️ sentry-sdk не установлен: {e}")
    except Exception as e:
        log.exception(f"Sentry init error: {e}")

# ==================== ЗАПУСК ====================
async def main():
    setup_logging()
    log.info("=== БОТ ЗАПУСКАЕТСЯ ===")

    setup_sentry()

    await init_db()
    log.info("✅ База данных инициализирована")

    wb = await get_world_boss()
    if not wb or not wb["boss_name"]:
        boss_name = random.choice(list(WORLD_BOSSES.keys()))
        boss = WORLD_BOSSES[boss_name]
        now_ts = int(datetime.now(timezone.utc).timestamp())
        await set_world_boss(boss_name, boss["hp"], now_ts)
        await set_guild_boss(boss_name, boss["hp"], now_ts)
        log.info(f"🐉 Стартовый босс: {boss_name}")

    await set_bot_commands()
    log.info("✅ Команды в меню Telegram обновлены")

    # APScheduler вместо while True
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    scheduler.add_job(
        rotate_bosses,
        CronTrigger(day_of_week="sat", hour=BOSS_ROTATION_HOUR, minute=0),
        id="boss_rotation",
        name="Ротация мировых боссов",
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        cleanup_cooldowns,
        IntervalTrigger(hours=1),
        id="cleanup_cooldowns",
        name="Очистка кулдаунов",
    )

    scheduler.start()
    log.info("✅ Планировщик запущен (ротация боссов + очистка кулдаунов)")

    log.info("=== БОТ ЗАПУЩЕН ===")

    # aiogram логирует ошибки через стандартный logging
    # → они попадут в Sentry через LoggingIntegration (встроено по умолчанию)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    try:
         # Ошибки в хэндлерах будут логироваться через log.exception
        # → попадут в файл и в Sentry
        await dp.start_polling(bot)
    finally:
        log.info("=== ОСТАНОВКА БОТА ===")
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("Бот остановлен пользователем")