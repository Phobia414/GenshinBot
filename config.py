import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "genshin.db")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

PRICE_ROLE_CHANGE = 1000
PRICE_REST = 300
PRICE_CLEAN = 2000

BOARD_COOLDOWN = 86400
ANTISPAM_SECONDS = 3

# ===== АНТИСПАМ =====
CB_COOLDOWN = 0.5
CMD_COOLDOWN = 1.5
PROPOSE_COOLDOWN = 30
BOSS_ATTACK_COOLDOWN = 4

# ===== ОФОРМЛЕНИЕ =====
CREATOR_USERNAME = "@splif1022"

# Проверка, что токен загрузился
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")