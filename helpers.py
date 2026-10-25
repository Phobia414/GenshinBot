import asyncio
import html
import random
from datetime import datetime, timezone

import aiosqlite
from aiogram.types import InputMediaPhoto, FSInputFile

from bot_instance import bot
from config import DB_PATH
from constants import (
    DIV, PLACEHOLDER_IMAGES, TASKS,
    ARTIFACT_SLOTS, RARITY_BONUS, SLOT_SHORT,
)
from db import (
    get_user, create_user, update_user, increment_user_field,
    get_rep_level, RESIN_MAX,
)
from characters import REGIONS, get_character_region
from state import _username_cache


def get_placeholder_image():
    return random.choice(PLACEHOLDER_IMAGES)


def esc(s):
    return html.escape(str(s)) if s else ""


def _mention(user_id, username, character_name, first_name):
    if username:
        return f'<a href="tg://user?id={user_id}">@{esc(username)}</a>'
    if character_name:
        return f'<a href="tg://user?id={user_id}">{esc(character_name)}</a>'
    if first_name:
        return f'<a href="tg://user?id={user_id}">{esc(first_name)}</a>'
    return f'<a href="tg://user?id={user_id}">Игрок</a>'


def hp_bar(current_hp, max_hp):
    total = 10
    if max_hp <= 0:
        return "░" * total
    filled = round(current_hp / max_hp * total)
    if 0 < current_hp and filled == 0:
        filled = 1
    filled = min(filled, total)
    return "▓" * filled + "░" * (total - filled)


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def format_resin_time(seconds):
    if seconds <= 0:
        return "Смола полная!"
    m = seconds // 60
    s = seconds % 60
    if m > 60:
        h = m // 60
        m = m % 60
        return f"{h} ч. {m} мин."
    return f"{m} мин. {s} сек."


def user_display_name(user):
    """Возвращает имя персонажа или обращение по полу."""
    if user and user.get("character_name"):
        return user["character_name"]

    # Если персонаж не выбран, смотрим на пол
    if user and user.get("gender") == "female":
        return "Путешественница"
    elif user and user.get("gender") == "male":
        return "Путешественник"

    # Если пол неизвестен (например, только зашел)
    return "Путешественник"


def get_reputation_bonuses(rep):
    level = get_rep_level(rep)
    earn_bonus = drop_bonus = shop_discount = 0
    if level >= 3:
        earn_bonus = 5
    if level >= 5:
        shop_discount = 10
    if level >= 7:
        drop_bonus = 10
    return earn_bonus, drop_bonus, shop_discount


def get_reputation_title(rep, region_name):
    level = get_rep_level(rep)
    if level >= 10:
        return f"🏆 Герой {region_name}"
    if level >= 7:
        return f"⭐ Знаменитость {region_name}"
    if level >= 5:
        return f"🌟 Уважаемый житель {region_name}"
    if level >= 3:
        return f"✨ Известный в {region_name}"
    return f"🌱 Новичок в {region_name}"


def find_region_by_character(character):
    if not character:
        return None
    key = get_character_region(character)
    if key and key in REGIONS:
        return key, REGIONS[key]
    return None


async def _ensure_user(uid: int):
    u = await get_user(uid)
    if not u:
        await create_user(uid)
        u = await get_user(uid)
    return u


async def _gain_rep(user_id, chat_id, amount, tg_first_name=None):
    if amount <= 0:
        return
    u_before = await get_user(user_id)
    if not u_before:
        return
    old_rep = u_before["reputation"] or 0
    old_lvl = get_rep_level(old_rep)
    await increment_user_field(user_id, "reputation", amount)
    u_after = await get_user(user_id)
    new_rep = u_after["reputation"] or 0
    new_lvl = get_rep_level(new_rep)
    if new_lvl > old_lvl:
        rinfo = find_region_by_character(u_after["character_name"])
        rname = rinfo[1] if rinfo else "Тейвата"
        title = get_reputation_title(new_rep, rname)
        name = tg_first_name or u_after.get("character_name") or "Игрок"
        mention = f'<a href="tg://user?id={user_id}">{esc(name)}</a>'
        try:
            await bot.send_message(chat_id, f"🎖️ {mention}, репутация достигла {new_lvl}!\n{title}", parse_mode="HTML")
        except Exception:
            pass


def generate_tasks():
    msg = [k for k, v in TASKS.items() if v["cat"] == "msg"]
    st = [k for k, v in TASKS.items() if v["cat"] == "st"]
    rep = [k for k, v in TASKS.items() if v["cat"] == "rep"]
    return [random.choice(msg), random.choice(st), random.choice(rep)]


def get_progress(user, cat):
    if cat == "msg":
        return user["board_msgs"]
    if cat == "st":
        return user["board_sts"]
    if cat == "rep":
        return user["board_reps"]
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
    if r < 0.05 * bonus:
        return 5
    if r < 0.30:
        return 4
    return 3


def roll_artifact(drop_bonus=0, set_name=""):
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


async def edit_or_send(query, text, kb, image_url=None):
    if image_url is None:
        image_url = get_placeholder_image()
    if image_url and len(text) > 1024:
        image_url = None

    chat_id = query.message.chat.id
    has_photo = bool(getattr(query.message, "photo", None))

    is_local = image_url and image_url in PLACEHOLDER_IMAGES

    if not image_url:
        candidates = [None]
    elif is_local:
        candidates = [FSInputFile(image_url), None]
    else:
        candidates = [image_url, FSInputFile(get_placeholder_image()), None]

    for media in candidates:
        if media and has_photo:
            try:
                await query.message.edit_media(
                    media=InputMediaPhoto(media=media, caption=text, parse_mode="HTML"),
                    reply_markup=kb)
                return
            except Exception:
                try:
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=media, caption=text),
                        reply_markup=kb)
                    return
                except Exception:
                    pass
        elif not media and not has_photo:
            try:
                await query.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                try:
                    await query.message.edit_text(text, reply_markup=kb)
                    return
                except Exception:
                    pass

        try:
            await query.message.delete()
        except Exception:
            pass
        has_photo = False

        if media:
            try:
                await bot.send_photo(chat_id=chat_id, photo=media, caption=text,
                                     reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                try:
                    await bot.send_photo(chat_id=chat_id, photo=media, caption=text,
                                         reply_markup=kb)
                    return
                except Exception:
                    pass
        else:
            try:
                await bot.send_message(chat_id=chat_id, text=text,
                                       reply_markup=kb, parse_mode="HTML")
                return
            except Exception:
                try:
                    await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)
                    return
                except Exception:
                    pass

    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        pass


async def get_characters_status():
    from characters import get_characters_by_region
    taken = {}
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT user_id, character_name FROM users "
                "WHERE character_name IS NOT NULL AND character_name != ''"
        ) as cur:
            for row in await cur.fetchall():
                taken[row["character_name"]] = row["user_id"]
    occupied, free = [], []
    for key, name in REGIONS.items():
        for ch in get_characters_by_region(key):
            if ch in taken:
                occupied.append((name, ch, taken[ch]))
            else:
                free.append((name, ch))
    return occupied, free


async def resolve_user_id(username):
    if not username:
        return None
    key = username.lstrip("@").lower()
    if key in _username_cache:
        return _username_cache[key]
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        try:
            async with db.execute("SELECT user_id FROM users WHERE LOWER(username) = ?", (key,)) as cur:
                row = await cur.fetchone()
                return row["user_id"] if row else None
        except Exception:
            return None


def extract_target(message):
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.first_name
    text = message.text or ""
    for ent in (message.entities or []):
        if ent.type == "text_mention" and ent.user:
            return ent.user.id, ent.user.first_name
    for ent in (message.entities or []):
        if ent.type == "mention":
            uname = text[ent.offset + 1: ent.offset + ent.length]
            return uname, uname
    return None, None