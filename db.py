import aiosqlite
from config import DB_PATH


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                join_chat_id INTEGER DEFAULT 0,
                guild_bonus_claimed INTEGER DEFAULT 0,
                call_opt_out INTEGER DEFAULT 0,
                gender TEXT,
                character_name TEXT,
                balance INTEGER DEFAULT 0,
                last_board INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                stickers_count INTEGER DEFAULT 0,
                replies_count INTEGER DEFAULT 0,
                board_msgs INTEGER DEFAULT 0,
                board_sts INTEGER DEFAULT 0,
                board_reps INTEGER DEFAULT 0,
                board_tasks TEXT DEFAULT '',
                board_claimed TEXT DEFAULT '',
                board_notified TEXT DEFAULT '',
                board_accepted TEXT DEFAULT '',
                board_active TEXT DEFAULT '',
                last_msg_time INTEGER DEFAULT 0,
                char_change_paid INTEGER DEFAULT 0,
                rest_active INTEGER DEFAULT 0,
                clean_exempt INTEGER DEFAULT 0,
                partner_id INTEGER DEFAULT 0,
                partner_name TEXT DEFAULT '',
                rel_xp INTEGER DEFAULT 0,
                is_married INTEGER DEFAULT 0,
                rel_started INTEGER DEFAULT 0,
                married_at INTEGER DEFAULT 0,
                child_id INTEGER DEFAULT 0,
                child_name TEXT DEFAULT '',
                guild_id INTEGER DEFAULT 0,
                guild_rank TEXT DEFAULT 'Участник',
                guild_contribution INTEGER DEFAULT 0,
                last_quiz INTEGER DEFAULT 0,
                equip_flower INTEGER DEFAULT 0,
                equip_plume INTEGER DEFAULT 0,
                equip_sands INTEGER DEFAULT 0,
                equip_goblet INTEGER DEFAULT 0,
                warns INTEGER DEFAULT 0,
                muted_until INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                resin INTEGER DEFAULT 160,
                last_resin_update INTEGER DEFAULT 0,
                ing_apple INTEGER DEFAULT 0,
                ing_mushroom INTEGER DEFAULT 0,
                ing_fish INTEGER DEFAULT 0,
                ing_meat INTEGER DEFAULT 0,
                ing_wheat INTEGER DEFAULT 0,
                ing_honey INTEGER DEFAULT 0,
                food_buff_name TEXT DEFAULT '',
                food_buff_value INTEGER DEFAULT 0,
                food_buff_until INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS guilds (
                guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                owner_id INTEGER,
                owner_name TEXT,
                created_at INTEGER,
                treasury INTEGER DEFAULT 0,
                week_points INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                slot TEXT,
                rarity INTEGER,
                bonus_type TEXT,
                bonus_value INTEGER,
                name TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS world_boss (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                boss_name TEXT DEFAULT '',
                current_hp INTEGER DEFAULT 0,
                max_hp INTEGER DEFAULT 0,
                week_start INTEGER DEFAULT 0
            )
        """)
        await db.execute(
            "INSERT OR IGNORE INTO world_boss (id, boss_name, current_hp, max_hp, week_start) VALUES (1, '', 0, 0, 0)"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_boss (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                boss_name TEXT DEFAULT '',
                current_hp INTEGER DEFAULT 0,
                max_hp INTEGER DEFAULT 0,
                week_start INTEGER DEFAULT 0
            )
        """)
        await db.execute(
            "INSERT OR IGNORE INTO guild_boss (id, boss_name, current_hp, max_hp, week_start) VALUES (1, '', 0, 0, 0)"
        )

        await db.execute("""
            CREATE TABLE IF NOT EXISTS protected_users (
                user_id INTEGER PRIMARY KEY,
                owner_id INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                list_message_id INTEGER DEFAULT 0
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_channels (
                group_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                message_id INTEGER,
                font_style TEXT DEFAULT 'none',
                custom_alphabet TEXT DEFAULT '{}'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_names (
                group_id INTEGER,
                default_name TEXT,
                custom_name TEXT,
                PRIMARY KEY (group_id, default_name)
            )
        """)

        await db.commit()

        # ===== МИГРАЦИИ =====
        async with db.execute("PRAGMA table_info(users)") as cur:
            cols = [row[1] for row in await cur.fetchall()]
        if "username" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN username TEXT DEFAULT ''")
            await db.commit()
        if "join_chat_id" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN join_chat_id INTEGER DEFAULT 0")
            await db.commit()
        if "guild_bonus_claimed" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN guild_bonus_claimed INTEGER DEFAULT 0")
            await db.commit()
        if "call_opt_out" not in cols:
            await db.execute("ALTER TABLE users ADD COLUMN call_opt_out INTEGER DEFAULT 0")
            await db.commit()


# ============ USERS ============
async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        from datetime import datetime, timezone
        now = int(datetime.now(timezone.utc).timestamp())
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, resin, last_resin_update) VALUES (?, 160, ?)",
            (user_id, now)
        )
        await db.commit()


async def update_user(user_id, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
        await db.commit()


async def increment_user_field(user_id, field, amount=1):
    if not field.replace("_", "").isalnum():
        raise ValueError(f"Invalid field name: {field}")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {field} = IFNULL({field}, 0) + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await db.commit()


async def is_character_taken(character):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE character_name = ?", (character,)) as cur:
            return await cur.fetchone() is not None


async def get_taken_characters():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT character_name FROM users WHERE character_name IS NOT NULL AND character_name != ''"
        ) as cur:
            rows = await cur.fetchall()
            return {r[0] for r in rows}


async def get_top_balance(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT user_id, character_name, balance FROM users ORDER BY balance DESC LIMIT ?",
                (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_top_messages(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT user_id, character_name, messages_count FROM users ORDER BY messages_count DESC LIMIT ?",
                (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_top_reputation(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT user_id, character_name, reputation FROM users ORDER BY reputation DESC LIMIT ?",
                (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ============ GUILDS ============
async def get_guild(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_guild_by_name(name):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guilds WHERE name = ?", (name,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_guild(name, owner_id, owner_name):
    from datetime import datetime, timezone
    now = int(datetime.now(timezone.utc).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO guilds (name, owner_id, owner_name, created_at) VALUES (?, ?, ?, ?)",
            (name, owner_id, owner_name, now)
        )
        await db.commit()
        return cur.lastrowid


async def update_guild(guild_id, **kwargs):
    if not kwargs:
        return
    fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [guild_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE guilds SET {fields} WHERE guild_id = ?", values)
        await db.commit()


async def get_all_guilds(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT g.*, (SELECT COUNT(*) FROM users WHERE guild_id = g.guild_id) as members "
                "FROM guilds g ORDER BY g.treasury DESC LIMIT ?",
                (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_guild_members(guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT user_id, character_name, guild_rank, guild_contribution "
                "FROM users WHERE guild_id = ? ORDER BY guild_contribution DESC",
                (guild_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ============ ARTIFACTS ============
async def add_artifact(user_id, slot, rarity, bonus_type, bonus_value, name):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO artifacts (user_id, slot, rarity, bonus_type, bonus_value, name) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, slot, rarity, bonus_type, bonus_value, name)
        )
        await db.commit()
        return cur.lastrowid


async def get_artifact(artifact_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_user_artifacts(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT * FROM artifacts WHERE user_id = ? ORDER BY slot, rarity DESC",
                (user_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def delete_artifact(artifact_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM artifacts WHERE artifact_id = ?", (artifact_id,))
        await db.commit()


async def get_total_bonuses(user_id):
    user = await get_user(user_id)
    if not user:
        return 0, 0
    earn = 0
    drop = 0
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


# ============ WARNS ============
async def add_warn(user_id, amount=1):
    user = await get_user(user_id)
    if not user:
        return 0
    new_warns = (user["warns"] or 0) + amount
    await update_user(user_id, warns=new_warns)
    return new_warns


async def remove_warn(user_id, amount=1):
    user = await get_user(user_id)
    if not user:
        return 0
    new_warns = max(0, (user["warns"] or 0) - amount)
    await update_user(user_id, warns=new_warns)
    return new_warns


# ============ REPUTATION ============
def get_rep_level(reputation):
    if reputation is None:
        reputation = 0
    return min(10, reputation // 500 + 1)


def get_rep_progress(reputation):
    if reputation is None:
        reputation = 0
    level = get_rep_level(reputation)
    if level >= 10:
        return 10, reputation - 4500, 500
    current = reputation % 500
    return level, current, 500


async def add_reputation(user_id, amount=1):
    user = await get_user(user_id)
    if not user:
        return 0
    new_rep = (user["reputation"] or 0) + amount
    await update_user(user_id, reputation=new_rep)
    return new_rep


# ============ RESIN ============
RESIN_MAX = 160
RESIN_REGEN_SECONDS = 480
RESIN_COST_DUNGEON = 40


async def update_resin(user_id):
    user = await get_user(user_id)
    if not user:
        return 0
    from datetime import datetime, timezone
    now = int(datetime.now(timezone.utc).timestamp())
    last = user["last_resin_update"] or now
    current = user["resin"] if user["resin"] is not None else RESIN_MAX

    if current >= RESIN_MAX:
        await update_user(user_id, resin=RESIN_MAX, last_resin_update=now)
        return RESIN_MAX

    elapsed = now - last
    gained = elapsed // RESIN_REGEN_SECONDS
    if gained > 0:
        new_resin = min(RESIN_MAX, current + gained)
        new_last = last + gained * RESIN_REGEN_SECONDS
        await update_user(user_id, resin=new_resin, last_resin_update=new_last)
        return new_resin
    return current


# ============ COOKING ============
INGREDIENTS = {
    "apple": {"name": "🍎 Яблоко", "emoji": "🍎"},
    "mushroom": {"name": "🍄 Гриб", "emoji": "🍄"},
    "fish": {"name": "🐟 Рыба", "emoji": "🐟"},
    "meat": {"name": "🥩 Мясо", "emoji": "🥩"},
    "wheat": {"name": "🌾 Пшеница", "emoji": "🌾"},
    "honey": {"name": "🍯 Мёд", "emoji": "🍯"},
}

RECIPES = {
    "soup": {"name": "🍲 Похлёбка", "need": {"mushroom": 2, "meat": 1}, "buff_value": 10, "duration": 3600},
    "steamed_fish": {"name": "🐟 Рыба на пару", "need": {"fish": 2, "wheat": 1}, "buff_value": 15, "duration": 3600},
    "steak": {"name": "🍖 Стейк", "need": {"meat": 2, "wheat": 1}, "buff_value": 20, "duration": 3600},
    "honey_pie": {"name": "🍰 Медовый пирог", "need": {"wheat": 2, "honey": 1}, "buff_value": 25, "duration": 3600},
    "apple_pie": {"name": "🍎 Яблочный пирог", "need": {"apple": 3, "honey": 1}, "buff_value": 30, "duration": 3600},
}


async def add_ingredient(user_id, ing_key):
    user = await get_user(user_id)
    if not user:
        return
    field = f"ing_{ing_key}"
    current = user.get(field, 0) or 0
    await update_user(user_id, **{field: current + 1})


async def get_ingredients(user_id):
    user = await get_user(user_id)
    if not user:
        return {}
    return {key: (user.get(f"ing_{key}", 0) or 0) for key in INGREDIENTS.keys()}


async def use_ingredients(user_id, need):
    user = await get_user(user_id)
    if not user:
        return False
    for key, amount in need.items():
        if (user.get(f"ing_{key}", 0) or 0) < amount:
            return False
    updates = {}
    for key, amount in need.items():
        field = f"ing_{key}"
        updates[field] = (user.get(field, 0) or 0) - amount
    await update_user(user_id, **updates)
    return True


async def set_food_buff(user_id, name, value, duration):
    from datetime import datetime, timezone
    until = int(datetime.now(timezone.utc).timestamp()) + duration
    await update_user(user_id, food_buff_name=name, food_buff_value=value, food_buff_until=until)


async def get_food_buff(user_id):
    user = await get_user(user_id)
    if not user:
        return "", 0
    from datetime import datetime, timezone
    now = int(datetime.now(timezone.utc).timestamp())
    until = user.get("food_buff_until", 0) or 0
    if until > now:
        return user.get("food_buff_name", "") or "", user.get("food_buff_value", 0) or 0
    if until > 0:
        await update_user(user_id, food_buff_name="", food_buff_value=0, food_buff_until=0)
    return "", 0


# ============ WORLD BOSS ============
async def get_world_boss():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM world_boss WHERE id = 1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def set_world_boss(boss_name, hp, week_start):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE world_boss SET boss_name = ?, current_hp = ?, max_hp = ?, week_start = ? WHERE id = 1",
            (boss_name, hp, hp, week_start)
        )
        await db.commit()


async def damage_world_boss(amount):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT current_hp FROM world_boss WHERE id = 1") as cur:
            row = await cur.fetchone()
            if not row:
                return 0
            new_hp = max(0, row["current_hp"] - amount)
        await db.execute("UPDATE world_boss SET current_hp = ? WHERE id = 1", (new_hp,))
        await db.commit()
        return new_hp


# ============ GUILD BOSS ============
async def get_guild_boss():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM guild_boss WHERE id = 1") as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def set_guild_boss(boss_name, hp, week_start):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE guild_boss SET boss_name = ?, current_hp = ?, max_hp = ?, week_start = ? WHERE id = 1",
            (boss_name, hp, hp, week_start)
        )
        await db.commit()


async def damage_guild_boss(amount):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT current_hp FROM guild_boss WHERE id = 1") as cur:
            row = await cur.fetchone()
            if not row:
                return 0
            new_hp = max(0, row["current_hp"] - amount)
        await db.execute("UPDATE guild_boss SET current_hp = ? WHERE id = 1", (new_hp,))
        await db.commit()
        return new_hp


# ============ PROTECTED USERS ============
async def add_protected_user(user_id, owner_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO protected_users (user_id, owner_id) VALUES (?, ?)",
            (user_id, owner_id)
        )
        await db.commit()


async def remove_protected_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM protected_users WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_protected_owner(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT owner_id FROM protected_users WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# ============ CHAT SETTINGS ============
async def get_list_message_id(chat_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT list_message_id FROM chat_settings WHERE chat_id = ?", (chat_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def set_list_message_id(chat_id, message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO chat_settings (chat_id, list_message_id) VALUES (?, ?)",
            (chat_id, message_id)
        )
        await db.commit()


# ============ GROUP CHANNELS ============
async def set_group_channel(group_id: int, channel_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO group_channels (group_id, channel_id, message_id) VALUES (?, ?, ?)",
            (group_id, channel_id, message_id)
        )
        await db.commit()


async def get_group_channel(group_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT channel_id, message_id FROM group_channels WHERE group_id = ?", (group_id,)
        ) as cur:
            row = await cur.fetchone()
            return row if row else (0, 0)


async def set_group_font(group_id: int, font_style: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE group_channels SET font_style = ? WHERE group_id = ?",
            (font_style, group_id)
        )
        await db.commit()


async def get_group_font(group_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT font_style FROM group_channels WHERE group_id = ?", (group_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else "none"


# ============ CUSTOM NAMES ============
async def set_custom_name(group_id: int, default_name: str, custom_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO custom_names (group_id, default_name, custom_name) VALUES (?, ?, ?)",
            (group_id, default_name, custom_name)
        )
        await db.commit()


async def get_custom_names(group_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
                "SELECT default_name, custom_name FROM custom_names WHERE group_id = ?", (group_id,)
        ) as cur:
            rows = await cur.fetchall()
            return {row[0]: row[1] for row in rows}