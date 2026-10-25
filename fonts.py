# fonts.py
# Генератор Юникод-шрифтов для Telegram и правильный перевод на английский

RU_TO_EN = {
    # Мондштадт
    "Альбедо": "Albedo", "Барбара": "Barbara", "Беннет": "Bennett",
    "Венти": "Venti", "Джинн": "Jean", "Дилюк": "Diluc", "Диона": "Diona",
    "Кли": "Klee", "Кэйа": "Kaeya", "Лиза": "Lisa", "Мика": "Mika",
    "Мона": "Mona", "Ноэлль": "Noelle", "Розария": "Rosaria", "Рэйзор": "Razor",
    "Сахароза": "Sucrose", "Фишль": "Fischl", "Эмбер": "Amber", "Эола": "Eula",
    "Далия": "Dahlia", "Лоэн": "Lohen", "Дурин": "Durin", "Николь": "Nicole",
    "Варка": "Barka", "Алиса": "Alice", "Прюн": "Prun",
    # Ли Юэ
    "Бай Чжу": "Baizhu", "Бэй Доу": "Beidou", "Гань Юй": "Ganyu",
    "Е Лань": "Yelan", "Кэ Цин": "Keqing", "Нин Гуан": "Ningguang",
    "Син Цю": "Xingqiu", "Синь Янь": "Xinyan", "Сян Лин": "Xiangling",
    "Сяо": "Xiao", "Ху Тао": "Hu Tao", "Цици": "Qiqi",
    "Чжун Ли": "Zhongli", "Чунь Юнь": "Chongyun", "Шэнь Хэ": "Shenhe",
    "Юнь Цзинь": "Yun Jin", "Янь Фэй": "Yanfei", "Яо Яо": "Yaoyao",
    "Га Мин": "Gaming", "Лань Янь": "Lanyan", "Сянь Юнь": "Xianyun",
    # Инадзума
    "Аяка Камисато": "Kamisato Ayaka", "Аято Камисато": "Kamisato Ayato",
    "Горо": "Gorou", "Ёимия": "Yoimiya", "Итто": "Arataki Itto",
    "Кадзуха": "Kaedehara Kazuha", "Кирара": "Kirara", "Кокоми": "Sangonomiya Kokomi",
    "Райдэн Эи": "Raiden Shogun", "Сара": "Kujou Sara", "Саю": "Sayu",
    "Синобу": "Kuki Shinobu", "Тома": "Thoma", "Хэйдзо": "Shikanoin Heizou",
    "Яэ Мико": "Yae Miko", "Тиори": "Chiori", "Мидзуки": "Mizuki",
    # Сумеру
    "Аль-Хайтам": "Alhaitham", "Дори": "Dori", "Дэхья": "Dehya",
    "Кавех": "Kaveh", "Кандакия": "Candace", "Коллеи": "Collei",
    "Лайла": "Layla", "Нахида": "Nahida", "Нилу": "Nilou",
    "Сайно": "Cyno", "Сетос": "Sethos", "Странник": "Wanderer",
    "Тигнари": "Tighnari", "Фарузан": "Faruzan",
    # Фонтейн
    "Клоринда": "Clorinde", "Лини": "Lyney", "Линнет": "Lynette",
    "Навия": "Navia", "Нёвиллет": "Neuvillette", "Ризли": "Wriothesley",
    "Сиджвин": "Sigewinne", "Фремине": "Freminet", "Фурина": "Furina",
    "Шарлотта": "Charlotte", "Шеврёз": "Chevreuse", "Эмилия": "Emilie",
    "Эскофье": "Escoffier",
    # Натлан
    "Вареса": "Varesa", "Иансан": "Iansan", "Ифа": "Ifa",
    "Качина": "Kachina", "Кинич": "Kinich", "Мавуика": "Mavuika",
    "Муалани": "Mualani", "Оророн": "Ororon", "Ситлали": "Citlali",
    "Часка": "Chasca", "Шилонен": "Xilonen",
    # Нод-Край
    "Айно": "Aino", "Иллуга": "Illuga", "Коломбина": "Columbina",
    "Лаума": "Lauma", "Нефер": "Nefer", "Флинс": "Flins",
    "Ягода": "Yagoda", "Инеффа": "Ineffa", "Линнея": "Linnea",
    # Снежная
    "Алёша": "Alyosha", "Арлекино": "Arlecchino", "Одетта": "Odette",
    "Сандроне": "Sandrone", "Тарталья": "Tartaglia", "Пульчинелла": "Pulcinella",
    "Панталоне": "Pantalone", "Дотторе": "Dottore", "Капитано": "Capitano",
    "Пьеро": "Pierro", "Синьора": "Signora", "Царица": "Tsaritsa",
    "Весна": "Vesna", "Водяница": "Vodyanitsa", "Цзы Бай": "Zibai",
    "Валерий": "Valeriy", "Митя": "Mitya",
    # Другие
    "Дайнслейф": "Dainsleif", "Итэр": "Aether", "Люмин": "Lumine",
    "Паймон": "Paimon", "Скирк": "Skirk", "Элой": "Aloy"
}

BOLD_OFFSET = 0x1D400 - ord('A')
ITALIC_OFFSET = 0x1D434 - ord('A')
MONO_OFFSET = 0x1D670 - ord('A')

def to_bold(text: str) -> str:
    res = []
    for char in text:
        if 'A' <= char <= 'Z':
            res.append(chr(ord(char) + BOLD_OFFSET))
        elif 'a' <= char <= 'z':
            res.append(chr(ord(char) + BOLD_OFFSET + 26))
        else:
            res.append(char)
    return "".join(res)

def to_italic(text: str) -> str:
    res = []
    for char in text:
        if 'A' <= char <= 'Z':
            res.append(chr(ord(char) + ITALIC_OFFSET))
        elif 'a' <= char <= 'z':
            res.append(chr(ord(char) + ITALIC_OFFSET + 26))
        else:
            res.append(char)
    return "".join(res)

def to_monospace(text: str) -> str:
    res = []
    for char in text:
        if 'A' <= char <= 'Z':
            res.append(chr(ord(char) + MONO_OFFSET))
        elif 'a' <= char <= 'z':
            res.append(chr(ord(char) + MONO_OFFSET + 26))
        else:
            res.append(char)
    return "".join(res)

def apply_font(text: str, style: str) -> str:
    if style == "none":
        return text
    eng_name = RU_TO_EN.get(text, text)
    if style == "bold":
        return to_bold(eng_name)
    elif style == "italic":
        return to_italic(eng_name)
    elif style == "monospace":
        return to_monospace(eng_name)
    return eng_name

def apply_custom_font(text: str, custom_map: dict) -> str:
    """
    Применяет кастомный алфавит к тексту.
    """
    if not custom_map:
        return text

    # Проверяем, есть ли в карте русские буквы
    has_cyrillic = any('А' <= k <= 'я' or k in ('Ё', 'ё') for k in custom_map.keys())

    if has_cyrillic:
        # Если в карте есть русские буквы, применяем напрямую к оригиналу
        return "".join(custom_map.get(c, c) for c in text)

    # Иначе это чисто английский алфавит. Переводим имя на английский и заменяем.
    eng = RU_TO_EN.get(text, text)
    return "".join(custom_map.get(c, c) for c in eng)