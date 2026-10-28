# bosses.py
# Мировые боссы. Ротация — каждую субботу в 12:00.
# Урон 3000-10000 за удар.

WORLD_BOSSES = {
    "Двалин": {
        "hp": 100_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/NDhxwug.jpeg",
    },
    "Аждаха": {
        "hp": 200_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/3N1c7kA.png",
    },
    "Бейшт": {
        "hp": 200_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/QyrNbss.jpeg",
    },
    "Манифестация грома": {
        "hp": 150_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/Sci3M3l.jpeg",
    },
    "Легат големов": {
        "hp": 250_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/hY38c3E.jpeg",
    },
    "Золотой волчий вожак": {
        "hp": 250_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/ZjdOa6S.jpeg",
    },
    "Магу кэнки": {
        "hp": 300_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/dpOLerY.jpeg",
    },
    "Морской конёк тысячелетней жемчужины": {
        "hp": 300_000, "reward_min": 100, "reward_max": 300,
        "image": "https://i.imgur.com/gLUrJyf.jpeg",
    },
    "Гидротульпа": {
        "hp": 400_000, "reward_min": 200, "reward_max": 400,
        "image": "https://i.imgur.com/cBrhxr8.jpeg",
    },
    "Суаньи-отшельник": {
        "hp": 500_000, "reward_min": 400, "reward_max": 600,
        "image": "https://i.imgur.com/HKpwTJ1.jpeg",
    },
}

BOSS_ROTATION_DAY = 5       # 5 = суббота (пн=0)
BOSS_ROTATION_HOUR = 12     # 12:00
BOSS_DAMAGE_MIN = 3000      # Увеличенный минимальный урон
BOSS_DAMAGE_MAX = 10000     # Увеличенный максимальный урон