import html
import random
import aiohttp
import json # <--- ДОБАВЛЕНО
from datetime import datetime, timezone
from functools import wraps
from aiogram import types
from aiogram.types import FSInputFile, InputMediaPhoto, BufferedInputFile
from aiogram.exceptions import TelegramBadRequest
from aiogram import Bot # <--- ДОБАВЛЕНО
from bot_instance import bot
from config import DB_PATH
from constants import DIV, PLACEHOLDER_IMAGES, DEFAULT_ADMIN_RANKS # <--- ДОБАВЛЕНО
from db import (
    get_user, create_user, get_rep_level, get_local_setting,
    update_user, increment_user_field, get_guild, get_taken_characters,
    add_reputation
)
from characters import REGIONS, get_character_region
from state import _username_cache
import aiosqlite


def esc(s):
    return html.escape(str(s)) if s else ""


def get_placeholder_image():
    return random.choice(PLACEHOLDER_IMAGES)


async def get_section_image(section_key, fallback_image=None, chat_id=0):
    custom_img = await get_local_setting(f"image_{section_key}", chat_id)
    if custom_img:
        return custom_img
    if fallback_image:
        return fallback_image
    return ""


def user_display_name(user):
    if user and user.get("character_name"): return user["character_name"]
    if user and user.get("gender") == "female": return "Путешественница"
    if user and user.get("gender") == "male": return "Путешественник"
    return "Путешественник"


def format_text(template, user, div=None):
    name = esc(user_display_name(user)) if user else ""
    res = template.replace("{name}", name)
    if div: res = res.replace("{div}", div)
    return res


def _now_ts():
    return datetime.now(timezone.utc).timestamp()


async def _ensure_user(user_id, chat_id=0):
    user = await get_user(user_id, chat_id)
    if not user:
        await create_user(user_id, chat_id)
        user = await get_user(user_id, chat_id)
    return user


async def _gain_rep(user_id, chat_id, amount, name=""):
    if amount <= 0: return
    user = await get_user(user_id, chat_id)
    if not user: return
    old_level = get_rep_level(user.get("reputation", 0))
    new_rep = await add_reputation(user_id, chat_id, amount)
    new_level = get_rep_level(new_rep)
    if new_level > old_level and chat_id != 0:
        try:
            await bot.send_message(chat_id, f"🎖️ <b>{esc(name)}</b> повысил уровень репутации до <b>{new_level}</b>!", parse_mode="HTML")
        except Exception:
            pass


async def get_characters_status(chat_id=0):
    from characters import CHARACTERS, get_characters_by_region
    taken = await get_taken_characters(chat_id)
    occ, free = [], []
    for reg_key, reg_name in REGIONS.items():
        for name in get_characters_by_region(reg_key):
            if name in taken: occ.append((reg_name, name, 0))
            else: free.append((reg_name, name))
    return occ, free


def _mention(user_id, username, character_name, first_name):
    if username: return f'<a href="tg://user?id={user_id}">@{esc(username)}</a>'
    if character_name: return f'<a href="tg://user?id={user_id}">{esc(character_name)}</a>'
    if first_name: return f'<a href="tg://user?id={user_id}">{esc(first_name)}</a>'
    return f'<a href="tg://user?id={user_id}">Игрок</a>'


def hp_bar(current_hp, max_hp):
    total = 10
    if max_hp <= 0: return "░" * total
    filled = round(current_hp / max_hp * total)
    if 0 < current_hp and filled == 0: filled = 1
    filled = min(filled, total)
    return "▓" * filled + "░" * (total - filled)


def format_resin_time(seconds):
    if seconds <= 0: return "Смола полная!"
    m = seconds // 60
    s = seconds % 60
    if m > 60:
        h = m // 60
        m = m % 60
        return f"{h} ч. {m} мин."
    return f"{m} мин. {s} сек."


def get_reputation_bonuses(rep):
    level = get_rep_level(rep)
    earn_bonus = drop_bonus = shop_discount = 0
    if level >= 3: earn_bonus = 5
    if level >= 5: shop_discount = 10
    if level >= 7: drop_bonus = 10
    return earn_bonus, drop_bonus, shop_discount


def get_reputation_title(rep, region_name):
    level = get_rep_level(rep)
    cases = {
        "Мондштадт": ("Мондштадте", "Мондштадта"), "Ли Юэ": ("Ли Юэ", "Ли Юэ"),
        "Инадзума": ("Инадзуме", "Инадзумы"), "Сумеру": ("Сумеру", "Сумеру"),
        "Фонтейн": ("Фонтейне", "Фонтейна"), "Натлан": ("Натлане", "Натлана"),
        "Нод-Край": ("Нод-Крае", "Нод-Края"), "Снежная": ("Снежной", "Снежной"),
        "Тейват": ("Тейвате", "Тейвата"),
    }
    prep, gen = cases.get(region_name, (region_name, region_name))
    if level >= 10: return f"🏆 Герой {gen}"
    if level >= 7: return f"⭐ Знаменитость {gen}"
    if level >= 5: return f"🌟 Уважаемый житель {gen}"
    if level >= 3: return f"✨ Известный в {prep}"
    return f"🌱 Новичок в {prep}"


def find_region_by_character(character):
    if not character: return None
    key = get_character_region(character)
    if key and key in REGIONS:
        if key == "other": return key, "Тейват"
        return key, REGIONS[key]
    return None


def generate_tasks():
    from constants import TASKS
    msg = [k for k, v in TASKS.items() if v["cat"] == "msg"]
    st = [k for k, v in TASKS.items() if v["cat"] == "st"]
    rep = [k for k, v in TASKS.items() if v["cat"] == "rep"]
    return [random.choice(msg), random.choice(st), random.choice(rep)]


def get_progress(user, cat):
    if cat == "msg": return user["board_msgs"]
    if cat == "st": return user["board_sts"]
    if cat == "rep": return user["board_reps"]
    return 0


async def is_chat_admin(chat_id, user_id):
    try:
        m = await bot.get_chat_member(chat_id, user_id)
        return m.status in ("administrator", "creator")
    except Exception:
        return False


def roll_rarity(drop_bonus=0):
    bonus = 1 + drop_bonus / 100.0
    r = random.random()
    if r < 0.05 * bonus: return 5
    if r < 0.30: return 4
    return 3


def roll_artifact(drop_bonus=0, set_name=""):
    from constants import ARTIFACT_SLOTS, RARITY_BONUS, SLOT_SHORT
    slot = random.choice(list(ARTIFACT_SLOTS.keys()))
    rarity = roll_rarity(drop_bonus)
    bonus_type = ARTIFACT_SLOTS[slot]["bonus_type"]
    bonus_value = RARITY_BONUS[rarity]
    slot_short = SLOT_SHORT.get(slot, slot)
    name = f"{slot_short} [{set_name}] ({rarity}★)" if set_name else f"{slot_short} ({rarity}★)"
    return slot, rarity, bonus_type, bonus_value, name


def extract_target(message):
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.first_name
    text = message.text or ""
    for ent in (message.entities or []):
        if ent.type == "text_mention" and ent.user: return ent.user.id, ent.user.first_name
    for ent in (message.entities or []):
        if ent.type == "mention":
            uname = text[ent.offset + 1: ent.offset + ent.length]
            return uname, uname
    return None, None


async def resolve_user_id(username):
    if not username: return None
    key = username.lstrip("@").lower()
    if key in _username_cache: return _username_cache[key]
    res = await get_user_by_username(key)
    return res


async def get_user_by_username(username):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (username,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


def inject_user(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if 'user' in kwargs and 'chat_id' in kwargs:
            return await func(*args, **kwargs)
        event = next((a for a in args if isinstance(a, (types.CallbackQuery, types.Message))), None)
        if not event: return await func(*args, **kwargs)
        chat_id = event.message.chat.id if isinstance(event, types.CallbackQuery) and event.message else event.chat.id
        user = await get_user(event.from_user.id, chat_id)
        if not user:
            await create_user(event.from_user.id, chat_id)
            user = await get_user(event.from_user.id, chat_id)
        return await func(*args, user=user, chat_id=chat_id, **kwargs)
    return wrapper


async def download_image(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return BufferedInputFile(data, filename="image.jpg")
                else:
                    print(f"❌ Ошибка скачивания картинки (Status {resp.status}): {url}")
                    return None
    except Exception as e:
        print(f"❌ Ошибка скачивания картинки: {e}")
        return None


async def edit_or_send(query, text, kb, image_url=None):
    if not query.message:
        try: await bot.send_message(query.from_user.id, text, reply_markup=kb, parse_mode="HTML")
        except: pass
        return

    chat_id = query.message.chat.id
    has_photo = bool(getattr(query.message, "photo", None))

    media = None
    if image_url:
        if image_url.startswith("http"):
            media = await download_image(image_url)
        elif image_url.startswith("images/"):
            try:
                media = FSInputFile(image_url)
            except Exception as e:
                print(f"❌ Ошибка загрузки локального файла: {e}")
        else:
            # Если это file_id (загружено через админку)
            media = image_url

    # РЕЖИМ 1: Без картинки (только текст)
    if not media:
        if has_photo:
            try: await query.message.delete()
            except: pass
            await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        else:
            try:
                await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except TelegramBadRequest as e:
                if "message is not modified" in str(e): return
                await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        return

    # РЕЖИМ 2: С картинкой
    if has_photo:
        if len(text) > 1024:
            try: await query.message.delete()
            except: pass
            await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        else:
            try:
                # ИСПРАВЛЕНИЕ: Используем edit_media, чтобы принудительно поменять картинку!
                input_media = InputMediaPhoto(media=media, caption=text, parse_mode="HTML")
                await query.message.edit_media(media=input_media, reply_markup=kb)
            except TelegramBadRequest as e:
                if "message is not modified" in str(e): return
                # Если не удалось отредактировать медиа - удаляем и шлем заново
                try: await query.message.delete()
                except: pass
                await bot.send_photo(chat_id, media, caption=text, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                print(f"❌ Ошибка edit_media: {e}")
                try: await query.message.delete()
                except: pass
                await bot.send_photo(chat_id, media, caption=text, reply_markup=kb, parse_mode="HTML")
    else:
        try: await query.message.delete()
        except: pass
        if len(text) > 1024:
            await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")
        else:
            try:
                await bot.send_photo(chat_id, media, caption=text, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                print(f"❌ Ошибка отправки фото: {e}")
                await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML")


import json
from aiogram import Bot


# ================= НОВЫЕ ФУНКЦИИ ДЛЯ РАНГОВ =================
async def get_ranks_config():
    from db import get_setting
    default_json = json.dumps(DEFAULT_ADMIN_RANKS)
    conf = await get_setting("admin_ranks_config", default_json)
    try:
        return json.loads(conf)
    except:
        return DEFAULT_ADMIN_RANKS


async def save_ranks_config(config):
    from db import set_setting
    await set_setting("admin_ranks_config", json.dumps(config))


async def get_user_rank_data(user):
    if not user: return None
    rank_key = user.get("admin_rank")
    if not rank_key: return None
    ranks = await get_ranks_config()
    return ranks.get(rank_key)


def has_permission(rank_data, permission):
    if not rank_data: return False
    perms = rank_data.get("permissions", [])
    if "all" in perms or permission in perms:
        return True
    return False


def parse_admin_target(message):
    parts = message.text.split(maxsplit=2)
    if message.reply_to_message:
        reason = message.text.split(maxsplit=1)[1] if len(parts) > 1 else "Не указана"
        return message.reply_to_message.from_user.id, reason

    if len(parts) > 1 and parts[1].startswith("@"):
        username = parts[1].replace("@", "")
        reason = parts[2] if len(parts) > 2 else "Не указана"
        return username, reason

    return None, None


async def update_user_tag(bot, chat_id: int, user_id: int, user: dict = None):
    if not user:
        from db import get_user
        user = await get_user(user_id, chat_id)
    if not user: return

    char_name = user.get("character_name", "") or ""
    rank_key = user.get("admin_rank", "")

    NAME_ABBREVIATIONS = {
        "Аяка Камисато": "Аяка",
        "Аято Камисато": "Аято",
        "Дайнслейф": "Дайн",
        "Рэйндоттир": "Рэйн"
    }

    rank_name = ""
    if rank_key:
        ranks = await get_ranks_config()
        if rank_key in ranks:
            raw_rank = ranks[rank_key]["name"]
            rank_name = "".join([c for c in raw_rank if c.isalnum() or c in (".", " ", "-")]).strip()

    tag = ""
    if rank_name:
        if char_name in NAME_ABBREVIATIONS:
            short_name = NAME_ABBREVIATIONS[char_name]
        else:
            max_char_len = 16 - len(rank_name) - 1
            if max_char_len >= 3:
                short_name = char_name[:max_char_len].strip()
            else:
                short_name = "Админ"
        tag = f"{short_name} {rank_name}"
    else:
        tag = char_name[:16]

    try:
        await bot.promote_chat_member(
            chat_id=chat_id, user_id=user_id,
            can_change_info=False, can_delete_messages=False, can_invite_users=False,
            can_restrict_members=False, can_pin_messages=False, can_promote_members=False,
            can_manage_chat=False, can_manage_video_chats=False, can_manage_topics=False
        )
        if tag:
            await bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=user_id, custom_title=tag)
        else:
            await bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=user_id, custom_title="")
    except Exception as e:
        print(f"⚠️ Ошибка установки тега: {e}")


async def apply_tg_rights(bot: Bot, chat_id: int, user_id: int, rank_data: dict):
    if not rank_data: return False
    rights = rank_data.get("tg_rights", {})
    try:
        await bot.promote_chat_member(
            chat_id=chat_id, user_id=user_id,
            can_change_info=False,
            can_delete_messages=rights.get("can_delete_messages", False),
            can_invite_users=False,
            can_restrict_members=rights.get("can_restrict_members", False),
            can_pin_messages=False, can_promote_members=False,
            can_manage_chat=False, can_manage_video_chats=False, can_manage_topics=False
        )
        await update_user_tag(bot, chat_id, user_id)
        return True
    except Exception as e:
        print(f"Ошибка выдачи прав ТГ: {e}")
        return False


async def remove_tg_rights(bot: Bot, chat_id: int, user_id: int):
    try:
        await bot.promote_chat_member(
            chat_id=chat_id, user_id=user_id,
            can_change_info=False, can_delete_messages=False, can_invite_users=False,
            can_restrict_members=False, can_pin_messages=False, can_promote_members=False,
            can_manage_chat=False, can_manage_video_chats=False, can_manage_topics=False
        )
        await bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=user_id, custom_title="")
        return True
    except Exception:
        return False


# ==========================================
# ИСПРАВЛЕННЫЕ ФУНКЦИИ ДЛЯ ВЫДАЧИ РАНГОВ
# (Вставлено в конец файла для перезаписи старых версий)
# ==========================================

async def apply_tg_rights(bot, chat_id, user_id, rank_data):
    """Выдает права в Telegram на основе конфигурации ранга"""
    tg_rights = rank_data.get("tg_rights", {})

    if not tg_rights:
        await remove_tg_rights(bot, chat_id, user_id)
        return

    try:
        await bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_manage_chat=True,
            can_delete_messages=tg_rights.get("can_delete_messages", False),
            can_restrict_members=tg_rights.get("can_restrict_members", False),
            can_manage_tags=tg_rights.get("can_manage_tags", False),
            can_invite_users=True,
            can_pin_messages=True
        )
    except Exception as e:
        print(f"[Ошибка выдачи прав] Не удалось выдать права {user_id}: {e}")


async def remove_tg_rights(bot, chat_id, user_id):
    """Полностью снимает админку с пользователя"""
    try:
        await bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_invite_users=False,
            can_pin_messages=False,
            can_change_info=False,
            can_promote_members=False,
            can_manage_video_chats=False,
            can_manage_topics=False,
            is_anonymous=False,
            can_manage_tags=False
        )
    except Exception:
        pass


async def update_user_tag(bot, chat_id, user_id, user):
    """Ставит тег или должность. Срабатывает после выдачи ранга."""
    if not user or not user.get("character_name"):
        return

    tag = user["character_name"][:16]

    try:
        member = await bot.get_chat_member(chat_id, user_id)

        if member.status in ("administrator", "creator"):
            await bot.set_chat_administrator_custom_title(
                chat_id=chat_id,
                user_id=user_id,
                custom_title=tag
            )
        else:
            await bot.set_chat_member_tag(
                chat_id=chat_id,
                user_id=user_id,
                tag=tag
            )
    except Exception:
        pass


# ==========================================
# ИСПРАВЛЕННЫЕ И ДОБАВЛЕННЫЕ ФУНКЦИИ (Вставить в конец helpers.py)
# ==========================================
import json
from constants import DEFAULT_ADMIN_RANKS
from db import get_setting, set_setting


async def get_ranks_config():
    config = await get_setting("admin_ranks")
    if config:
        try:
            return json.loads(config)
        except:
            pass
    return DEFAULT_ADMIN_RANKS


async def save_ranks_config(ranks):
    await set_setting("admin_ranks", json.dumps(ranks))


async def apply_tg_rights(bot, chat_id, user_id, rank_data):
    tg_rights = rank_data.get("tg_rights", {})
    if not tg_rights:
        await remove_tg_rights(bot, chat_id, user_id)
        return "⚠️ В настройках ранга нет прав Телеграма."

    try:
        await bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_manage_chat=True,
            can_delete_messages=tg_rights.get("can_delete_messages", False),
            can_restrict_members=tg_rights.get("can_restrict_members", False),
            can_manage_tags=tg_rights.get("can_manage_tags", False),
            can_invite_users=True,
            can_pin_messages=True
        )
        return ""
    except Exception as e:
        return f"❌ Ошибка прав Телеграм: {e}. (Проверь, есть ли у бота галочка 'Добавлять администраторов')"


async def remove_tg_rights(bot, chat_id, user_id):
    try:
        await bot.promote_chat_member(
            chat_id=chat_id, user_id=user_id,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False, can_change_info=False,
            can_promote_members=False, can_manage_video_chats=False, can_manage_topics=False,
            is_anonymous=False, can_manage_tags=False
        )
    except Exception:
        pass


async def update_user_tag(bot, chat_id, user_id, user):
    if not user: return ""
    char_name = user.get("character_name", "")
    rank_key = user.get("admin_rank", "")

    tag_parts = []
    if char_name: tag_parts.append(char_name)
    if rank_key:
        ranks = await get_ranks_config()
        rank_name = ranks.get(rank_key, {}).get("name", "")
        if rank_name:
            clean_rank = rank_name.replace("👑 ", "").replace("🛡 ", "").replace("⚔ ", "").replace("⚙ ", "").replace("🔨 ",
                                                                                                                   "").replace(
                "🔧 ", "").replace("📝 ", "").strip()
            tag_parts.append(clean_rank)

    if not tag_parts: return ""
    tag = " | ".join(tag_parts)[:16]

    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ("administrator", "creator"):
            await bot.set_chat_administrator_custom_title(chat_id=chat_id, user_id=user_id, custom_title=tag)
        else:
            await bot.set_chat_member_tag(chat_id=chat_id, user_id=user_id, tag=tag)
        return ""
    except Exception as e:
        return f"⚠️ Ошибка тега: {e}"