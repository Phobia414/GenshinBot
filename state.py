# Глобальное состояние (кулдауны и кеш)
_inter_cooldown: dict = {}
_cb_cooldown: dict = {}
_cmd_cooldown: dict = {}
_propose_cooldown: dict = {}
_duel_cooldown: dict = {}
_boss_cooldown: dict = {}
_call_cooldown: dict = {}
_username_cache: dict = {}
import asyncio

# Викторина и группы
_active_quiz: dict = {}
_known_groups: set = set()
_active_quizzes: dict = {}

# ===== КАСТОМНЫЕ ПЕРСОНАЖИ И ФОТО =====
_char_photos: dict = {}   # {"Дурин": "file_id или url"}
_custom_chars: dict = {}  # {"Новый Герой": {"region": "mondstadt", "image": "file_id или url"}}
_gacha_images: dict = {}
_board_locks: dict = {}
# Хранилище ID последних сообщений бота для авто-удаления
_last_bot_msg: dict = {}
def get_board_lock(user_id: int) -> asyncio.Lock:
    if user_id not in _board_locks:
        _board_locks[user_id] = asyncio.Lock()
    return _board_locks[user_id]

# ===== FSM состояния для настройки шрифта =====
from aiogram.fsm.state import State, StatesGroup

class FontEdit(StatesGroup):
    waiting_alphabet = State()