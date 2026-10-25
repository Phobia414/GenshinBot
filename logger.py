import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "bot.log"
LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level=logging.INFO):
    """Настройка логирования: консоль + файл с ротацией (10 МБ × 5 файлов)."""
    LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level)

    # Убираем все старые хендлеры (для повторных вызовов)
    for h in root.handlers[:]:
        root.removeHandler(h)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 1. Консоль
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(level)
    root.addHandler(console)

    # 2. Файл с ротацией
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,   # 10 MB
        backupCount=5,               # всего до 50 MB
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    # Понижаем уровень шума от сторонних библиотек
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)

    return root


def get_logger(name):
    return logging.getLogger(name)