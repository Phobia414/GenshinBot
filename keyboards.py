from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import (
    MenuCB, RegionCB, CharCB, TaskCB, ShopCB, RelCB, GiftCB,
    GuildCB, FunCB, CasinoCB, TopCB, DungeonCB, CookCB,
    ArtCB, ArtifactCB, ListsCB, CmdCatCB,
)
from characters import REGIONS, get_characters_by_region
from constants import (
    TASKS, GIFTS, DUNGEONS, PLAYER_COMMANDS,
    XP_PER_LEVEL, MAX_LEVEL, WEDDING_LEVEL,
)
from config import (
    PRICE_ROLE_CHANGE, PRICE_REST, PRICE_CLEAN, OWNER_ID,
)
from db import RESIN_COST_DUNGEON, RECIPES, INGREDIENTS


def main_menu_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="👤 Профиль ›", callback_data=MenuCB(action="profile", owner_id=uid))
    b.button(text="🏛 Гильдия искателей ›", callback_data=MenuCB(action="adventurers", owner_id=uid))
    b.button(text="💕 Отношения ›", callback_data=MenuCB(action="relations", owner_id=uid))
    b.button(text="🎲 Развлечения ›", callback_data=MenuCB(action="fun", owner_id=uid))
    b.button(text="🏆 Топы ›", callback_data=MenuCB(action="tops", owner_id=uid))
    b.button(text="📖 Списки ›", callback_data=MenuCB(action="lists", owner_id=uid))
    b.button(text="🛒 Лавка Тейвата ›", callback_data=MenuCB(action="shop", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def adventurers_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="⚔ Подземелья ›", callback_data=MenuCB(action="dungeons", owner_id=uid))
    b.button(text="📋 Доска занятости ›", callback_data=MenuCB(action="board", owner_id=uid))
    b.button(text="🎒 Артефакты ›", callback_data=MenuCB(action="artifacts", owner_id=uid))
    b.button(text="🐉 Мировые боссы ›", callback_data=MenuCB(action="world_boss", owner_id=uid))
    b.button(text="🏰 Гильдии ›", callback_data=MenuCB(action="guild", owner_id=uid))
    b.button(text="🎖 Репутация ›", callback_data=MenuCB(action="reputation", owner_id=uid))
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def lists_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="📜 Команды ›", callback_data=ListsCB(action="commands", owner_id=uid))
    b.button(text="🎭 Персонажи ›", callback_data=ListsCB(action="characters", owner_id=uid))
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def back_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    return b.as_markup()


def profile_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="🎭 Освободить роль", callback_data=MenuCB(action="freerole", owner_id=uid))
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def gender_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="👨 Мужской", callback_data=MenuCB(action="gender_male", owner_id=uid))
    b.button(text="👩 Женский", callback_data=MenuCB(action="gender_female", owner_id=uid))
    b.adjust(2)
    return b.as_markup()


def regions_kb(uid):
    b = InlineKeyboardBuilder()
    for key, name in REGIONS.items():
        b.button(text=name, callback_data=RegionCB(region=key, owner_id=uid))
    b.adjust(2)
    return b.as_markup()


def characters_kb(uid, region_key, taken):
    b = InlineKeyboardBuilder()
    for ch in get_characters_by_region(region_key):
        if ch in taken:
            continue
        b.button(text=ch, callback_data=CharCB(character=ch, owner_id=uid))
    b.button(text="‹ К регионам", callback_data=MenuCB(action="regions", owner_id=uid))
    b.adjust(2) # <--- ВОЗВРАЩЕНО 2 КОЛОНКИ
    return b.as_markup()


def board_kb(uid, user, tasks, accepted, claimed):
    from helpers import get_progress
    b = InlineKeyboardBuilder()
    for t_id in tasks:
        t = TASKS[t_id]
        if t_id in claimed:
            b.button(text=f"✅ {t['text']} · получено", callback_data=TaskCB(task_id=t_id, owner_id=uid))
        elif t_id in accepted:
            progress = get_progress(user, t["cat"])
            b.button(text=f"⏳ {t['text']} · {progress}/{t['need']}", callback_data=TaskCB(task_id=t_id, owner_id=uid))
        else:
            b.button(text=f"📌 Принять · {t['text']}", callback_data=TaskCB(task_id=t_id, owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def shop_kb(uid, discount=0):
    def p(x):
        return int(x * (100 - discount) / 100) if discount else x
    b = InlineKeyboardBuilder()
    b.button(text=f"🎭 Смена персонажа · {p(PRICE_ROLE_CHANGE)}", callback_data=ShopCB(item="role", owner_id=uid))
    b.button(text=f"😴 Рест · {p(PRICE_REST)}", callback_data=ShopCB(item="rest", owner_id=uid))
    b.button(text=f"🧹 Освобождение от чистки · {p(PRICE_CLEAN)}", callback_data=ShopCB(item="clean", owner_id=uid))
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def relations_kb(uid, has_partner, married, can_marry, has_child, gender):
    b = InlineKeyboardBuilder()
    if has_partner:
        b.button(text="🎁 Подарить подарок ›", callback_data=RelCB(action="gifts", owner_id=uid))
        if can_marry and not married:
            b.button(text="💍 Сыграть свадьбу ›", callback_data=RelCB(action="marry", owner_id=uid))
        if married and not has_child:
            if gender == "male":
                b.button(text="👶 Усыновить ›", callback_data=RelCB(action="adopt_hint", owner_id=uid))
            elif gender == "female":
                b.button(text="👶 Удочерить ›", callback_data=RelCB(action="adopt_hint", owner_id=uid))
            else:
                b.button(text="👶 Усыновить/Удочерить ›", callback_data=RelCB(action="adopt_hint", owner_id=uid))
        b.button(text="💔 Разорвать отношения", callback_data=RelCB(action="breakup", owner_id=uid))
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def gifts_kb(uid):
    b = InlineKeyboardBuilder()
    for k, g in GIFTS.items():
        b.button(text=f"{g['name']} · {g['price']}", callback_data=GiftCB(item=k, owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="relations", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def guild_menu_kb(uid, has_guild, is_owner):
    b = InlineKeyboardBuilder()
    if has_guild:
        b.button(text="ℹ О гильдии ›", callback_data=GuildCB(action="info", owner_id=uid))
        b.button(text="👥 Состав ›", callback_data=GuildCB(action="members", owner_id=uid))
        b.button(text="💰 Казна ›", callback_data=GuildCB(action="treasury", owner_id=uid))
        b.button(text="🐉 Босс гильдии ›", callback_data=GuildCB(action="boss", owner_id=uid))
        if is_owner:
            b.button(text="⚙ Управление ›", callback_data=GuildCB(action="manage", owner_id=uid))
        b.button(text="🚪 Выйти из гильдии", callback_data=GuildCB(action="leave", owner_id=uid))
    else:
        b.button(text="➕ Создать гильдию · 700", callback_data=GuildCB(action="create", owner_id=uid))
        b.button(text="📜 Список гильдий ›", callback_data=GuildCB(action="list", owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def guild_list_kb(uid, guilds):
    b = InlineKeyboardBuilder()
    for g in guilds:
        b.button(text=f"🏰 {g['name']} · 💰 {g['treasury']}",
                 callback_data=GuildCB(action="join", owner_id=uid, guild_id=g["guild_id"]))
    b.button(text="‹ Назад", callback_data=MenuCB(action="guild", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def fun_menu_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="🎰 Казино ›", callback_data=FunCB(action="casino", owner_id=uid))
    b.button(text="🧠 Викторина ›", callback_data=FunCB(action="quiz", owner_id=uid))
    b.button(text="⚔ Дуэль ›", callback_data=FunCB(action="duel_help", owner_id=uid))
    b.button(text="🍳 Кулинария ›", callback_data=MenuCB(action="cook", owner_id=uid))
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def casino_kb(uid):
    b = InlineKeyboardBuilder()
    for game, label in [("roulette", "🎡 Рулетка x2"), ("slots", "🎰 Слоты x3"), ("dice", "🎲 Кости x2")]:
        for bet in (100, 500, 1000):
            b.button(text=f"{label} · {bet}", callback_data=CasinoCB(game=game, bet=bet, owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="fun", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def tops_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="💰 По балансу ›", callback_data=TopCB(action="balance", owner_id=uid))
    b.button(text="💬 По сообщениям ›", callback_data=TopCB(action="messages", owner_id=uid))
    b.button(text="🎖 По репутации ›", callback_data=TopCB(action="reputation", owner_id=uid))
    b.button(text="🏰 По гильдиям ›", callback_data=TopCB(action="guilds", owner_id=uid))
    b.button(text="‹ Назад в меню", callback_data=MenuCB(action="menu", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def reputation_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="🏆 Топ по репутации ›", callback_data=TopCB(action="reputation", owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def dungeons_kb(uid):
    b = InlineKeyboardBuilder()
    for key, d in DUNGEONS.items():
        b.button(text=f"{d['name']} · {RESIN_COST_DUNGEON}💧",
                 callback_data=DungeonCB(action="enter", dungeon=key, owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def cook_kb(uid, ing):
    b = InlineKeyboardBuilder()
    for k, r in RECIPES.items():
        need = r["need"]
        can = all(ing.get(x, 0) >= v for x, v in need.items())
        b.button(text=f"{r['name']} · +{r['buff_value']}%{'' if can else ' ❌'}",
                 callback_data=CookCB(action="cook", recipe=k, owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="fun", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def artifacts_menu_kb(uid, has):
    b = InlineKeyboardBuilder()
    if has:
        b.button(text="🎒 Инвентарь ›", callback_data=ArtCB(action="inventory", owner_id=uid))
    b.button(text="⚔ В подземелья ›", callback_data=MenuCB(action="dungeons", owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def inventory_kb(uid, arts):
    b = InlineKeyboardBuilder()
    for a in arts:
        b.button(text=f"{a['name']} · +{a['bonus_value']}%",
                 callback_data=ArtifactCB(action="view", art_id=a["artifact_id"], owner_id=uid))
    b.button(text="‹ Назад", callback_data=MenuCB(action="artifacts", owner_id=uid))
    b.adjust(1)
    return b.as_markup()


def artifact_view_kb(uid, art_id, equipped):
    b = InlineKeyboardBuilder()
    if equipped:
        b.button(text="⏏ Снять", callback_data=ArtifactCB(action="unequip", art_id=art_id, owner_id=uid))
    else:
        b.button(text="⬆ Экипировать", callback_data=ArtifactCB(action="equip", art_id=art_id, owner_id=uid))
    b.button(text="💰 Продать", callback_data=ArtifactCB(action="sell", art_id=art_id, owner_id=uid))
    b.button(text="‹ К инвентарю", callback_data=ArtCB(action="inventory", owner_id=uid))
    b.adjust(2, 1)
    return b.as_markup()


def commands_cats_kb(uid):
    b = InlineKeyboardBuilder()
    b.button(text="🎮 Основные ›", callback_data=CmdCatCB(cat="main", owner_id=uid))
    b.button(text="🎭 Взаимодействия ›", callback_data=CmdCatCB(cat="interactions", owner_id=uid))
    b.button(text="💕 Отношения ›", callback_data=CmdCatCB(cat="relations", owner_id=uid))
    b.button(text="🏰 Гильдия ›", callback_data=CmdCatCB(cat="guild", owner_id=uid))
    b.button(text="⚔ Дуэль ›", callback_data=CmdCatCB(cat="duel", owner_id=uid))
    b.button(text="🍳 Кулинария ›", callback_data=CmdCatCB(cat="cooking", owner_id=uid))
    b.button(text="📢 Позывной ›", callback_data=CmdCatCB(cat="call", owner_id=uid))
    if uid == OWNER_ID:
        b.button(text="⚙ Админ-команды ›", callback_data=CmdCatCB(cat="admin", owner_id=uid))
    b.button(text="‹ К спискам", callback_data=MenuCB(action="lists", owner_id=uid))
    b.adjust(2, 2, 2, 2, 1)
    return b.as_markup()