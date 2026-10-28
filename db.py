import aiosqlite
from config import DB_PATH
from datetime import datetime, timezone


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        tables_to_migrate = {
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER, chat_id INTEGER DEFAULT 0, username TEXT DEFAULT '',
                    join_chat_id INTEGER DEFAULT 0, guild_bonus_claimed INTEGER DEFAULT 0, call_opt_out INTEGER DEFAULT 0,
                    gender TEXT, character_name TEXT, balance INTEGER DEFAULT 0, last_board INTEGER DEFAULT 0,
                    messages_count INTEGER DEFAULT 0, stickers_count INTEGER DEFAULT 0, replies_count INTEGER DEFAULT 0,
                    board_msgs INTEGER DEFAULT 0, board_sts INTEGER DEFAULT 0, board_reps INTEGER DEFAULT 0,
                    board_tasks TEXT DEFAULT '', board_claimed TEXT DEFAULT '', board_notified TEXT DEFAULT '',
                    board_accepted TEXT DEFAULT '', board_active TEXT DEFAULT '', last_msg_time INTEGER DEFAULT 0,
                    char_change_paid INTEGER DEFAULT 0, rest_active INTEGER DEFAULT 0, clean_exempt INTEGER DEFAULT 0,
                    partner_id INTEGER DEFAULT 0, partner_name TEXT DEFAULT '', rel_xp INTEGER DEFAULT 0,
                    is_married INTEGER DEFAULT 0, rel_started INTEGER DEFAULT 0, married_at INTEGER DEFAULT 0,
                    child_id INTEGER DEFAULT 0, child_name TEXT DEFAULT '', guild_id INTEGER DEFAULT 0,
                    guild_rank TEXT DEFAULT 'Участник', guild_contribution INTEGER DEFAULT 0, last_quiz INTEGER DEFAULT 0,
                    equip_flower INTEGER DEFAULT 0, equip_plume INTEGER DEFAULT 0, equip_sands INTEGER DEFAULT 0, equip_goblet INTEGER DEFAULT 0,
                    warns INTEGER DEFAULT 0, muted_until INTEGER DEFAULT 0, reputation INTEGER DEFAULT 0,
                    resin INTEGER DEFAULT 160, last_resin_update INTEGER DEFAULT 0,
                    ing_apple INTEGER DEFAULT 0, ing_mushroom INTEGER DEFAULT 0, ing_fish INTEGER DEFAULT 0,
                    ing_meat INTEGER DEFAULT 0, ing_wheat INTEGER DEFAULT 0, ing_honey INTEGER DEFAULT 0,
                    food_buff_name TEXT DEFAULT '', food_buff_value INTEGER DEFAULT 0, food_buff_until INTEGER DEFAULT 0,
                    primogems INTEGER DEFAULT 0, gacha_pity_4 INTEGER DEFAULT 0, gacha_pity_5 INTEGER DEFAULT 0,
                    gacha_guaranteed_5 INTEGER DEFAULT 0, gacha_lost_50_50 INTEGER DEFAULT 0, last_daily INTEGER DEFAULT 0,
                    guild_char_exp INTEGER DEFAULT 0, guild_rest_exp INTEGER DEFAULT 0, guild_clean_exp INTEGER DEFAULT 0,
                    first_seen INTEGER DEFAULT 0, rel_image TEXT DEFAULT '',
                    PRIMARY KEY (user_id, chat_id)
                )
            """,
            "guilds": """
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, name TEXT,
                    owner_id INTEGER, owner_name TEXT, created_at INTEGER, treasury INTEGER DEFAULT 0,
                    week_points INTEGER DEFAULT 0, description TEXT DEFAULT '', image_url TEXT DEFAULT '',
                    level INTEGER DEFAULT 1, max_members INTEGER DEFAULT 5, is_unbroken INTEGER DEFAULT 0,
                    ally_id INTEGER DEFAULT 0, UNIQUE(chat_id, name)
                )
            """,
            "artifacts": """
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER,
                    slot TEXT, rarity INTEGER, bonus_type TEXT, bonus_value INTEGER, name TEXT
                )
            """,
            "world_boss": """
                CREATE TABLE IF NOT EXISTS world_boss (
                    chat_id INTEGER PRIMARY KEY, boss_name TEXT DEFAULT '', current_hp INTEGER DEFAULT 0,
                    max_hp INTEGER DEFAULT 0, week_start INTEGER DEFAULT 0
                )
            """,
            "guild_boss": """
                CREATE TABLE IF NOT EXISTS guild_boss (
                    chat_id INTEGER PRIMARY KEY, boss_name TEXT DEFAULT '', current_hp INTEGER DEFAULT 0,
                    max_hp INTEGER DEFAULT 0, week_start INTEGER DEFAULT 0
                )
            """,
            "protected_users": """
                CREATE TABLE IF NOT EXISTS protected_users (
                    user_id INTEGER, chat_id INTEGER, owner_id INTEGER NOT NULL, PRIMARY KEY (user_id, chat_id)
                )
            """,
            "gacha_inventory": """
                CREATE TABLE IF NOT EXISTS gacha_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER,
                    item_name TEXT, item_type TEXT, rarity INTEGER, image_url TEXT
                )
            """,
            "applications": """
                CREATE TABLE IF NOT EXISTS applications (
                    user_id INTEGER,
                    chat_id INTEGER,
                    character_name TEXT,
                    age TEXT,
                    experience TEXT,
                    about TEXT,
                    timezone TEXT,
                    triggers TEXT,
                    metagaming TEXT,
                    activity TEXT,
                    status TEXT DEFAULT 'pending',
                    PRIMARY KEY (user_id, chat_id)
                )
            """
        }

        for table_name, create_sql in tables_to_migrate.items():
            try:
                async with db.execute(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'") as cur:
                    table_exists = bool(await cur.fetchone())

                async with db.execute(
                        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}_old'") as cur:
                    old_exists = bool(await cur.fetchone())

                if not table_exists:
                    await db.execute(create_sql)
                else:
                    async with db.execute(f"PRAGMA table_info({table_name})") as cur:
                        cols = [row[1] for row in await cur.fetchall()]

                    if "chat_id" not in cols and table_name not in ["applications", "bot_settings", "char_photos",
                                                                    "custom_chars", "gacha_gifs",
                                                                    "gacha_custom_images"]:
                        print(f"🔄 Миграция таблицы {table_name}...")
                        await db.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_old")
                        await db.execute(create_sql)
                        old_exists = True
                        async with db.execute(f"PRAGMA table_info({table_name})") as cur:
                            new_cols = [row[1] for row in await cur.fetchall()]
                        async with db.execute(f"PRAGMA table_info({table_name}_old)") as cur:
                            cols = [row[1] for row in await cur.fetchall()]
                    else:
                        async with db.execute(f"PRAGMA table_info({table_name})") as cur:
                            new_cols = [row[1] for row in await cur.fetchall()]
                        if old_exists:
                            async with db.execute(f"PRAGMA table_info({table_name}_old)") as cur:
                                cols = [row[1] for row in await cur.fetchall()]
                        else:
                            cols = []

                if old_exists and cols:
                    common_cols = [c for c in cols if c in new_cols and c != 'chat_id']
                    if common_cols:
                        cols_str = ", ".join(common_cols)
                        await db.execute(
                            f"INSERT OR IGNORE INTO {table_name} ({cols_str}, chat_id) SELECT {cols_str}, 0 FROM {table_name}_old")

                    await db.execute(f"DROP TABLE {table_name}_old")
                    print(f"✅ Таблица {table_name} успешно мигрирована.")

                await db.commit()
            except Exception as e:
                print(f"⚠️ Ошибка миграции {table_name}: {e}")

        try:
            await db.execute("ALTER TABLE users ADD COLUMN rel_image TEXT DEFAULT ''")
        except Exception:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_cleanup_settings (
                chat_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                min_messages INTEGER DEFAULT 100,
                frequency_days INTEGER DEFAULT 7,
                last_cleanup INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (chat_id INTEGER PRIMARY KEY, list_message_id INTEGER DEFAULT 0)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_channels (group_id INTEGER PRIMARY KEY, channel_id INTEGER, message_id INTEGER, font_style TEXT DEFAULT 'none', custom_alphabet TEXT DEFAULT '{}')
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_names (group_id INTEGER, default_name TEXT, custom_name TEXT, PRIMARY KEY (group_id, default_name))
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_alliances (id INTEGER PRIMARY KEY AUTOINCREMENT, guild1_id INTEGER, guild2_id INTEGER, created_at INTEGER)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_member_stats (guild_id INTEGER, user_id INTEGER, msgs INTEGER DEFAULT 0, stickers INTEGER DEFAULT 0, replies INTEGER DEFAULT 0, photos INTEGER DEFAULT 0, bosses INTEGER DEFAULT 0, PRIMARY KEY (guild_id, user_id))
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS char_photos (name TEXT PRIMARY KEY, image_url TEXT)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_chars (name TEXT PRIMARY KEY, region TEXT, image_url TEXT)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS gacha_gifs (rarity TEXT PRIMARY KEY, file_id TEXT)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS gacha_custom_images (item_name TEXT PRIMARY KEY, image_url TEXT)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS known_groups (chat_id INTEGER PRIMARY KEY)
        """)
        await db.commit()


# ============ ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ИНИЦИАЛИЗАЦИИ ============
async def init_settings_db(): pass


async def init_known_groups_db(): pass


async def init_gacha_db(): pass


async def init_gacha_images_db(): pass


async def load_gacha_images():
    import state
    rows = await fetch_all("SELECT item_name, image_url FROM gacha_custom_images")
    for r in rows:
        state._gacha_images[r['item_name']] = r['image_url']


# ============ ШОРТКАТЫ ДЛЯ БД ============
async def fetch_one(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def fetch_all(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def execute(query, params=()):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.lastrowid


# ============ CLEANUP SETTINGS ============
async def get_cleanup_settings(chat_id):
    res = await fetch_one("SELECT * FROM chat_cleanup_settings WHERE chat_id = ?", (chat_id,))
    if not res:
        await execute("INSERT OR IGNORE INTO chat_cleanup_settings (chat_id) VALUES (?)", (chat_id,))
        res = await fetch_one("SELECT * FROM chat_cleanup_settings WHERE chat_id = ?", (chat_id,))
    return res


async def update_cleanup_settings(chat_id, **kwargs):
    if not kwargs: return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [chat_id]
    await execute(f"UPDATE chat_cleanup_settings SET {fields} WHERE chat_id = ?", values)


# ============ USERS ============
async def get_user(user_id, chat_id=0):
    return await fetch_one("SELECT * FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))


async def create_user(user_id, chat_id=0):
    now = int(datetime.now(timezone.utc).timestamp())
    await execute(
        "INSERT OR IGNORE INTO users (user_id, chat_id, resin, last_resin_update, first_seen) VALUES (?, ?, 160, ?, ?)",
        (user_id, chat_id, now, now))


async def update_user(user_id, chat_id=0, **kwargs):
    if not kwargs: return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [user_id, chat_id]
    await execute(f"UPDATE users SET {fields} WHERE user_id = ? AND chat_id = ?", values)


async def increment_user_field(user_id, chat_id, field, amount=1):
    await execute(f"UPDATE users SET {field} = IFNULL({field}, 0) + ? WHERE user_id = ? AND chat_id = ?",
                  (amount, user_id, chat_id))


async def is_character_taken(character, chat_id=0):
    res = await fetch_one("SELECT user_id FROM users WHERE character_name = ? AND chat_id = ?", (character, chat_id))
    return res is not None


async def get_taken_characters(chat_id=0):
    rows = await fetch_all(
        "SELECT character_name FROM users WHERE character_name IS NOT NULL AND character_name != '' AND chat_id = ?",
        (chat_id,))
    return {r['character_name'] for r in rows}


async def get_top_balance(chat_id=0, limit=10):
    return await fetch_all(
        "SELECT user_id, character_name, balance FROM users WHERE chat_id = ? ORDER BY balance DESC LIMIT ?",
        (chat_id, limit))


async def get_top_messages(chat_id=0, limit=10):
    return await fetch_all(
        "SELECT user_id, character_name, messages_count FROM users WHERE chat_id = ? ORDER BY messages_count DESC LIMIT ?",
        (chat_id, limit))


async def get_top_reputation(chat_id=0, limit=10):
    return await fetch_all(
        "SELECT user_id, character_name, reputation FROM users WHERE chat_id = ? ORDER BY reputation DESC LIMIT ?",
        (chat_id, limit))


# ============ CHAT LIST / GROUP SETTINGS ============
async def set_group_channel(group_id, channel_id, message_id):
    await execute("INSERT OR REPLACE INTO group_channels (group_id, channel_id, message_id) VALUES (?, ?, ?)",
                  (group_id, channel_id, message_id))


async def get_group_channel(group_id):
    res = await fetch_one("SELECT channel_id, message_id FROM group_channels WHERE group_id = ?", (group_id,))
    if res: return res['channel_id'], res['message_id']
    return None, None


async def set_group_font(group_id, font_style):
    await execute(
        "INSERT INTO group_channels (group_id, font_style) VALUES (?, ?) ON CONFLICT(group_id) DO UPDATE SET font_style = excluded.font_style",
        (group_id, font_style))


async def get_group_font(group_id):
    res = await fetch_one("SELECT font_style FROM group_channels WHERE group_id = ?", (group_id,))
    return res['font_style'] if res else "none"


async def set_custom_name(group_id, default_name, custom_name):
    await execute("INSERT OR REPLACE INTO custom_names (group_id, default_name, custom_name) VALUES (?, ?, ?)",
                  (group_id, default_name, custom_name))


async def get_custom_names(group_id):
    rows = await fetch_all("SELECT default_name, custom_name FROM custom_names WHERE group_id = ?", (group_id,))
    return {r['default_name']: r['custom_name'] for r in rows}


# ============ GUILDS ============
async def get_guild(guild_id):
    return await fetch_one("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,))


async def get_guild_by_name(name, chat_id):
    return await fetch_one("SELECT * FROM guilds WHERE name = ? AND chat_id = ?", (name, chat_id))


async def create_guild(name, owner_id, owner_name, chat_id):
    now = int(datetime.now(timezone.utc).timestamp())
    return await execute("INSERT INTO guilds (chat_id, name, owner_id, owner_name, created_at) VALUES (?, ?, ?, ?, ?)",
                         (chat_id, name, owner_id, owner_name, now))


async def update_guild(guild_id, **kwargs):
    if not kwargs: return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [guild_id]
    await execute(f"UPDATE guilds SET {fields} WHERE guild_id = ?", values)


async def get_all_guilds(chat_id, limit=20):
    return await fetch_all(
        "SELECT g.*, (SELECT COUNT(*) FROM users WHERE guild_id = g.guild_id AND chat_id = g.chat_id) as members FROM guilds g WHERE g.chat_id = ? ORDER BY g.level DESC, g.treasury DESC LIMIT ?",
        (chat_id, limit))


async def get_guild_members(guild_id):
    return await fetch_all(
        "SELECT user_id, character_name, guild_rank, guild_contribution FROM users WHERE guild_id = ? ORDER BY guild_contribution DESC",
        (guild_id,))


async def get_guild_craft_stats(guild_id):
    row = await fetch_one(
        "SELECT SUM(msgs) as m, SUM(stickers) as s, SUM(replies) as r, SUM(photos) as p, SUM(bosses) as b FROM guild_member_stats WHERE guild_id = ?",
        (guild_id,))
    if not row or row['m'] is None: return {"m": 0, "s": 0, "r": 0, "p": 0, "b": 0}
    return row


# ============ ARTIFACTS ============
async def add_artifact(user_id, chat_id, slot, rarity, bonus_type, bonus_value, name):
    return await execute(
        "INSERT INTO artifacts (user_id, chat_id, slot, rarity, bonus_type, bonus_value, name) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, chat_id, slot, rarity, bonus_type, bonus_value, name))


async def get_artifact(artifact_id):
    return await fetch_one("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,))


async def get_user_artifacts(user_id, chat_id):
    return await fetch_all("SELECT * FROM artifacts WHERE user_id = ? AND chat_id = ? ORDER BY slot, rarity DESC",
                           (user_id, chat_id))


async def delete_artifact(artifact_id):
    await execute("DELETE FROM artifacts WHERE artifact_id = ?", (artifact_id,))


async def get_total_bonuses(user_id, chat_id):
    user = await get_user(user_id, chat_id)
    if not user: return 0, 0
    earn, drop = 0, 0
    for field in ["equip_flower", "equip_plume", "equip_sands", "equip_goblet"]:
        art_id = user.get(field, 0) or 0
        if art_id:
            art = await get_artifact(art_id)
            if art:
                if art["bonus_type"] == "earn":
                    earn += art["bonus_value"]
                elif art["bonus_type"] == "drop":
                    drop += art["bonus_value"]
    return earn, drop


# ============ WARNS / REPUTATION ============
async def add_warn(user_id, chat_id, amount=1):
    user = await get_user(user_id, chat_id)
    if not user: return 0
    new_warns = (user["warns"] or 0) + amount
    await update_user(user_id, chat_id, warns=new_warns)
    return new_warns


async def remove_warn(user_id, chat_id, amount=1):
    user = await get_user(user_id, chat_id)
    if not user: return 0
    new_warns = max(0, (user["warns"] or 0) - amount)
    await update_user(user_id, chat_id, warns=new_warns)
    return new_warns


def get_rep_level(reputation):
    if reputation is None: reputation = 0
    return min(10, reputation // 500 + 1)


def get_rep_progress(reputation):
    if reputation is None: reputation = 0
    level = get_rep_level(reputation)
    if level >= 10: return 10, reputation - 4500, 500
    current = reputation % 500
    return level, current, 500


async def add_reputation(user_id, chat_id, amount=1):
    user = await get_user(user_id, chat_id)
    if not user: return 0
    new_rep = (user["reputation"] or 0) + amount
    await update_user(user_id, chat_id, reputation=new_rep)
    return new_rep


# ============ RESIN ============
RESIN_MAX = 160
RESIN_REGEN_SECONDS = 480
RESIN_COST_DUNGEON = 40


async def update_resin(user_id, chat_id):
    user = await get_user(user_id, chat_id)
    if not user: return 0
    now = int(datetime.now(timezone.utc).timestamp())
    last = user["last_resin_update"] or now
    current = user["resin"] if user["resin"] is not None else RESIN_MAX
    if current >= RESIN_MAX:
        await update_user(user_id, chat_id, resin=RESIN_MAX, last_resin_update=now)
        return RESIN_MAX
    elapsed = now - last
    gained = elapsed // RESIN_REGEN_SECONDS
    if gained > 0:
        new_resin = min(RESIN_MAX, current + gained)
        new_last = last + gained * RESIN_REGEN_SECONDS
        await update_user(user_id, chat_id, resin=new_resin, last_resin_update=new_last)
        return new_resin
    return current


# ============ COOKING ============
INGREDIENTS = {
    "apple": {"name": "🍎 Яблоко", "emoji": "🍎"}, "mushroom": {"name": "🍄 Гриб", "emoji": "🍄"},
    "fish": {"name": "🐟 Рыба", "emoji": "🐟"}, "meat": {"name": "🥩 Мясо", "emoji": "🥩"},
    "wheat": {"name": "🌾 Пшеница", "emoji": "🌾"}, "honey": {"name": "🍯 Мёд", "emoji": "🍯"},
}
RECIPES = {
    "soup": {"name": "🍲 Похлёбка", "need": {"mushroom": 2, "meat": 1}, "buff_value": 10, "duration": 3600},
    "steamed_fish": {"name": "🐟 Рыба на пару", "need": {"fish": 2, "wheat": 1}, "buff_value": 15, "duration": 3600},
    "steak": {"name": "🍖 Стейк", "need": {"meat": 2, "wheat": 1}, "buff_value": 20, "duration": 3600},
    "honey_pie": {"name": "🍰 Медовый пирог", "need": {"wheat": 2, "honey": 1}, "buff_value": 25, "duration": 3600},
    "apple_pie": {"name": "🍎 Яблочный пирог", "need": {"apple": 3, "honey": 1}, "buff_value": 30, "duration": 3600},
}


async def add_ingredient(user_id, chat_id, ing_key):
    user = await get_user(user_id, chat_id)
    if not user: return
    field = f"ing_{ing_key}"
    await update_user(user_id, chat_id, **{field: (user.get(field, 0) or 0) + 1})


async def get_ingredients(user_id, chat_id):
    user = await get_user(user_id, chat_id)
    if not user: return {}
    return {key: (user.get(f"ing_{key}", 0) or 0) for key in INGREDIENTS.keys()}


async def use_ingredients(user_id, chat_id, need):
    user = await get_user(user_id, chat_id)
    if not user: return False
    for key, amount in need.items():
        if (user.get(f"ing_{key}", 0) or 0) < amount: return False
    updates = {}
    for key, amount in need.items():
        updates[f"ing_{key}"] = (user.get(f"ing_{key}", 0) or 0) - amount
    await update_user(user_id, chat_id, **updates)
    return True


async def set_food_buff(user_id, chat_id, name, value, duration):
    until = int(datetime.now(timezone.utc).timestamp()) + duration
    await update_user(user_id, chat_id, food_buff_name=name, food_buff_value=value, food_buff_until=until)


async def get_food_buff(user_id, chat_id):
    user = await get_user(user_id, chat_id)
    if not user: return "", 0
    now = int(datetime.now(timezone.utc).timestamp())
    until = user.get("food_buff_until", 0) or 0
    if until > now: return user.get("food_buff_name", "") or "", user.get("food_buff_value", 0) or 0
    if until > 0: await update_user(user_id, chat_id, food_buff_name="", food_buff_value=0, food_buff_until=0)
    return "", 0


# ============ BOSSES ============
async def get_world_boss(chat_id):
    return await fetch_one("SELECT * FROM world_boss WHERE chat_id = ?", (chat_id,))


async def set_world_boss(chat_id, boss_name, hp, week_start):
    await execute(
        "INSERT OR REPLACE INTO world_boss (chat_id, boss_name, current_hp, max_hp, week_start) VALUES (?, ?, ?, ?, ?)",
        (chat_id, boss_name, hp, hp, week_start))


async def damage_world_boss(chat_id, amount):
    wb = await get_world_boss(chat_id)
    if not wb: return 0
    new_hp = max(0, wb["current_hp"] - amount)
    await execute("UPDATE world_boss SET current_hp = ? WHERE chat_id = ?", (new_hp, chat_id))
    return new_hp


async def get_guild_boss(chat_id):
    return await fetch_one("SELECT * FROM guild_boss WHERE chat_id = ?", (chat_id,))


async def set_guild_boss(chat_id, boss_name, hp, week_start):
    await execute(
        "INSERT OR REPLACE INTO guild_boss (chat_id, boss_name, current_hp, max_hp, week_start) VALUES (?, ?, ?, ?, ?)",
        (chat_id, boss_name, hp, hp, week_start))


async def damage_guild_boss(chat_id, amount):
    gb = await get_guild_boss(chat_id)
    if not gb: return 0
    new_hp = max(0, gb["current_hp"] - amount)
    await execute("UPDATE guild_boss SET current_hp = ? WHERE chat_id = ?", (new_hp, chat_id))
    return new_hp


# ============ PROTECTED USERS / SETTINGS ============
async def add_protected_user(user_id, chat_id, owner_id):
    await execute("INSERT OR REPLACE INTO protected_users (user_id, chat_id, owner_id) VALUES (?, ?, ?)",
                  (user_id, chat_id, owner_id))


async def remove_protected_user(user_id, chat_id):
    await execute("DELETE FROM protected_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))


async def get_protected_owner(user_id, chat_id):
    res = await fetch_one("SELECT owner_id FROM protected_users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    return res['owner_id'] if res else None


async def get_setting(key, default=""):
    res = await fetch_one("SELECT value FROM bot_settings WHERE key = ?", (key,))
    return res['value'] if res else default


async def set_setting(key, value):
    await execute("INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))


async def get_local_setting(key, chat_id=0, default=""):
    if chat_id:
        local_val = await get_setting(f"chat_{chat_id}_{key}")
        if local_val: return local_val
    return await get_setting(key, default)


async def set_local_setting(key, value, chat_id=0):
    if chat_id:
        await set_setting(f"chat_{chat_id}_{key}", value)
    else:
        await set_setting(key, value)


# ============ CUSTOM DATA ============
async def load_custom_data_to_state():
    import state
    rows = await fetch_all("SELECT name, image_url FROM char_photos")
    for r in rows: state._char_photos[r['name']] = r['image_url']
    rows = await fetch_all("SELECT name, region, image_url FROM custom_chars")
    for r in rows: state._custom_chars[r['name']] = {"region": r['region'], "image": r['image_url']}
    rows = await fetch_all("SELECT item_name, image_url FROM gacha_custom_images")
    for r in rows: state._gacha_images[r['item_name']] = r['image_url']


async def save_char_photo(name, url):
    import state
    state._char_photos[name] = url
    await execute("INSERT OR REPLACE INTO char_photos (name, image_url) VALUES (?, ?)", (name, url))


async def save_custom_char(name, region, url):
    import state
    state._custom_chars[name] = {"region": region, "image": url}
    await execute("INSERT OR REPLACE INTO custom_chars (name, region, image_url) VALUES (?, ?, ?)", (name, region, url))


async def delete_custom_char(name):
    import state
    if name in state._custom_chars: del state._custom_chars[name]
    await execute("DELETE FROM custom_chars WHERE name = ?", (name,))
    await execute("DELETE FROM char_photos WHERE name = ?", (name,))


async def save_gacha_image(name, url):
    import state
    state._gacha_images[name] = url
    await execute("INSERT OR REPLACE INTO gacha_custom_images (item_name, image_url) VALUES (?, ?)", (name, url))


# ============ GROUPS / GACHA ============
async def add_known_group(chat_id):
    await execute("INSERT OR IGNORE INTO known_groups (chat_id) VALUES (?)", (chat_id,))


async def get_known_groups():
    rows = await fetch_all("SELECT chat_id FROM known_groups")
    return [r['chat_id'] for r in rows]


async def update_primogems(user_id, chat_id, amount):
    await execute("UPDATE users SET primogems = IFNULL(primogems, 0) + ? WHERE user_id = ? AND chat_id = ?",
                  (amount, user_id, chat_id))


async def get_gacha_gif(rarity):
    res = await fetch_one("SELECT file_id FROM gacha_gifs WHERE rarity = ?", (rarity,))
    return res['file_id'] if res else None


async def set_gacha_gif(rarity, file_id):
    await execute("INSERT OR REPLACE INTO gacha_gifs (rarity, file_id) VALUES (?, ?)", (rarity, file_id))


async def add_gacha_item(user_id, chat_id, item_name, item_type, rarity, image_url):
    await execute(
        "INSERT INTO gacha_inventory (user_id, chat_id, item_name, item_type, rarity, image_url) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, chat_id, item_name, item_type, rarity, image_url))


async def get_gacha_inventory(user_id, chat_id):
    return await fetch_all("SELECT * FROM gacha_inventory WHERE user_id = ? AND chat_id = ? ORDER BY id DESC",
                           (user_id, chat_id))


# ============ APPLICATIONS ============
async def save_application(user_id, chat_id, character_name, age, experience, about, timezone, triggers, metagaming,
                           activity):
    await execute("""
        INSERT OR REPLACE INTO applications (user_id, chat_id, character_name, age, experience, about, timezone, triggers, metagaming, activity, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    """, (user_id, chat_id, character_name, age, experience, about, timezone, triggers, metagaming, activity))


async def get_application(user_id, chat_id):
    return await fetch_one("SELECT * FROM applications WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))


async def update_application_status(user_id, chat_id, status):
    await execute("UPDATE applications SET status = ? WHERE user_id = ? AND chat_id = ?", (status, user_id, chat_id))