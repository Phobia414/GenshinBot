import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "data/genshin.db")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

QUIZ_CHAT_ID = int(os.getenv("QUIZ_CHAT_ID", OWNER_ID))

PRICE_ROLE_CHANGE = 25000
PRICE_REST = 8000
PRICE_CLEAN = 40000
PRICE_ELIXIR = 6000

BOARD_COOLDOWN = 86400
ANTISPAM_SECONDS = 3

# ===== АНТИСПАМ =====
CB_COOLDOWN = 0.5
CMD_COOLDOWN = 1.5
PROPOSE_COOLDOWN = 30
BOSS_ATTACK_COOLDOWN = 4

# ===== ОФОРМЛЕНИЕ =====
CREATOR_USERNAME = "@splif1022"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")