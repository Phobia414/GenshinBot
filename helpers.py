import html
import random
from datetime import datetime, timezone
from functools import wraps
from aiogram import types
from aiogram.types import FSInputFile, InputMediaPhoto
from bot_instance import bot
from config import DB_PATH
from constants import PLACEHOLDER_IMAGES, DIV
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
    if custom_img: return custom_img
    if fallback_image: return fallback_image
    return get_placeholder_image()


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
            await bot.send_message(
                chat_id,
                f"🎖️ <b>{esc(name)}</b> повысил уровень репутации до <b>{new_level}</b>!",
                parse_mode="HTML"
            )
        except Exception:
            pass


async def get_characters_status(chat_id=0):
    from characters import CHARACTERS, get_characters_by_region
    taken = await get_taken_characters(chat_id)
    occ = []
    free = []
    for reg_key, reg_name in REGIONS.items():
        for name in get_characters_by_region(reg_key):
            if name in taken:
                occ.append((reg_name, name, 0))
            else:
                free.append((reg_name, name))
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


# ==========================================
# ОБНОВЛЕННАЯ ПРОГРЕССИЯ РАНГОВ
# ==========================================
def get_reputation_title(rep, region_name):
    level = get_rep_level(rep)

    ranks = {
        1: "🌱 Новичок",
        2: "🍃 Путник",
        3: "🗺️ Искатель",
        4: "⚔️ Защитник",
        5: "🛡️ Ветеран",
        6: "✨ Знаток",
        7: "🏅 Почетный житель",
        8: "⭐ Знаменитость",
        9: "👑 Мастер",
        10: "🏆 Герой"
    }

    # Если уровень выше 10, оставляем 10-й
    rank_name = ranks.get(level, "🏆 Герой")

    return f"{rank_name} {region_name}"


def find_region_by_character(character):
    if not character: return None
    key = get_character_region(character)
    if key and key in REGIONS:
        if key == "other": return key, "Тейвате"
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
    if set_name:
        name = f"{slot_short} [{set_name}] ({rarity}★)"
    else:
        name = f"{slot_short} ({rarity}★)"
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
        event = next((a for a in args if isinstance(a, (types.CallbackQuery, types.Message))), None)
        if not event: return await func(*args, **kwargs)

        if isinstance(event, types.CallbackQuery):
            chat_id = event.message.chat.id if event.message else 0
        else:
            chat_id = event.chat.id

        user = await get_user(event.from_user.id, chat_id)
        if not user:
            await create_user(event.from_user.id, chat_id)
            user = await get_user(event.from_user.id, chat_id)
        return await func(*args, user=user, chat_id=chat_id, **kwargs)

    return wrapper


async def edit_or_send(query, text, kb, image_url=None):
    if image_url is None: image_url = get_placeholder_image()
    if image_url and len(text) > 1024: image_url = None

    if not query.message:
        try:
            await bot.send_message(query.from_user.id, text, reply_markup=kb, parse_mode="HTML")
        except:
            pass
        return

    chat_id = query.message.chat.id
    has_photo = bool(getattr(query.message, "photo", None))
    is_local = image_url and image_url in PLACEHOLDER_IMAGES
    is_file_id = image_url and not image_url.startswith("http") and not is_local
    if not image_url:
        candidates = [None]
    elif is_local:
        candidates = [FSInputFile(image_url), None]
    elif is_file_id:
        candidates = [image_url, None]
    else:
        candidates = [image_url, FSInputFile(get_placeholder_image()), None]

    for media in candidates:
        if media and has_photo:
            try:
                await query.message.edit_media(media=InputMediaPhoto(media=media, caption=text, parse_mode="HTML"),
                                               reply_markup=kb)
                return
            except:
                pass
        elif not media and not has_photo:
            try:
                await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
                return
            except:
                pass
        try:
            await query.message.delete()
        except:
            pass
        has_photo = False
        if media:
            try:
                await bot.send_photo(chat_id=chat_id, photo=media, caption=text, reply_markup=kb, parse_mode="HTML")
                return
            except:
                pass
        else:
            try:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")
                return
            except:
                pass
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except:
        pass