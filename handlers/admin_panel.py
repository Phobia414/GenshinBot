from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot_instance import bot, dp
from config import OWNER_ID
from constants import DIV
from db import get_local_setting, set_local_setting, save_char_photo, save_custom_char, delete_custom_char, \
    get_known_groups, set_gacha_gif, save_gacha_image
from characters import REGIONS, get_characters_by_region
from gacha_data import POOL_3_STAR, POOL_4_STAR, POOL_5_STAR
import state


class AdminEdit(StatesGroup):
    waiting_for_text = State()
    waiting_for_photo = State()
    waiting_for_char_name = State()
    waiting_for_char_photo = State()
    waiting_for_chat_id = State()
    waiting_for_gif = State()
    waiting_for_gacha_photo = State()
    setting_key = State()


def get_media_file_id(message):
    if message.photo: return message.photo[-1].file_id
    if message.animation: return message.animation.file_id
    if message.video: return message.video.file_id
    if message.document:
        if message.document.mime_type and (message.document.mime_type.startswith(
            "image/") or message.document.mime_type == "video/mp4"): return message.document.file_id
    return None


EDITABLE_TEXTS = {
    "text_start": "👋 Приветствие (/start)", "text_menu": "🌟 Главное меню", "text_profile": "👤 Профиль",
    "text_shop": "🛒 Лавка", "text_relations": "💕 Отношения", "text_adventurers": "🏛 Гильдия искателей",
    "text_duel_help": "⚔️ Помощь по дуэли", "text_dungeons": "⚔️ Подземелья", "text_guild": "🏰 Гильдии",
    "text_tops": "🏆 Топы", "text_reputation": "🎖 Репутация",
}

EDITABLE_PHOTOS = {
    "menu": "🌟 Главное меню", "profile": "👤 Профиль", "shop": "🛒 Лавка Тейвата",
    "relations": "💕 Отношения", "adventurers": "🏛 Гильдия искателей", "dungeons": "⚔️ Подземелья",
    "guild": "🏰 Гильдии", "reputation": "🎖 Репутация", "tops": "🏆 Топы (общее)",
    "tops_balance": "💰 Топ по балансу", "tops_messages": "💬 Топ по сообщениям",
    "tops_rep": "⭐ Топ по репутации", "tops_guilds": "🏰 Топ по гильдиям", "fun": "⚔ Дуэль (Развлечения)",
    "rolelist": "📜 Баннер списка ролей (в канале)"
}


async def render_admin_menu(message, state):
    data = await state.get_data()
    target_chat_id = data.get("target_chat_id", 0)
    context_text = "🌐 ВСЕ ЧАТЫ (Глобально)" if target_chat_id == 0 else f"💬 Чат ID: {target_chat_id}"

    b = InlineKeyboardBuilder()
    b.button(text=f"⊱ Контекст: {context_text} ⊰", callback_data="admin_change_context")
    b.button(text="⊱ 📝 Изменить тексты ⊰", callback_data="admin_edit_texts")
    b.button(text="⊱ 🖼 Изменить картинки ⊰", callback_data="admin_edit_photos")
    b.button(text="⊱ 🎭 Персонажи ⊰", callback_data="admin_edit_chars")
    b.button(text="⊱ 🎬 Гифки Гачи ⊰", callback_data="admin_edit_gifs")
    b.button(text="⊱ 🎨 Картинки Гачи ⊰", callback_data="admin_edit_gacha_imgs")
    b.adjust(1)

    text = f"╓───────────────────────╖\n   ⚙️ АДМИН-ПАНЕЛЬ\n╙───────────────────────╜\n\n🌐 Контекст: <b>{context_text}</b>\n\n╞═══════════════════════╡\n\nВыбери категорию:"
    await message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")


@dp.message(Command("admin"))
async def cmd_admin(message, state):
    if message.from_user.id != OWNER_ID: return
    if message.chat.type != "private": return await message.answer("❌ Только в ЛС.")
    await state.clear()
    await state.update_data(target_chat_id=0)

    b = InlineKeyboardBuilder()
    b.button(text="⊱ Контекст: 🌐 ВСЕ ЧАТЫ (Глобально) ⊰", callback_data="admin_change_context")
    b.button(text="⊱ 📝 Изменить тексты ⊰", callback_data="admin_edit_texts")
    b.button(text="⊱ 🖼 Изменить картинки ⊰", callback_data="admin_edit_photos")
    b.button(text="⊱ 🎭 Персонажи ⊰", callback_data="admin_edit_chars")
    b.button(text="⊱ 🎬 Гифки Гачи ⊰", callback_data="admin_edit_gifs")
    b.button(text="⊱ 🎨 Картинки Гачи ⊰", callback_data="admin_edit_gacha_imgs")
    b.adjust(1)

    text = f"╓───────────────────────╖\n   ⚙️ АДМИН-ПАНЕЛЬ\n╙───────────────────────╜\n\n🌐 Контекст: <b>ВСЕ ЧАТЫ (Глобально)</b>\n\n╞═══════════════════════╡\n\nВыбери категорию:"
    await message.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data == "admin_change_context")
async def cb_change_context(query, state):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    b.button(text="⊱ 🌐 Применять для ВСЕХ ⊰", callback_data="admin_set_context_0")
    for chat_id in await get_known_groups():
        try:
            chat = await bot.get_chat(chat_id)
            b.button(text=f"⊱ 💬 {chat.title} ⊰", callback_data=f"admin_set_context_{chat_id}")
        except:
            pass
    b.button(text="⊱ ✍️ Ввести ID вручную ⊰", callback_data="admin_manual_chat")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_back")
    b.adjust(1)
    await query.message.edit_text("🌐 **ВЫБОР КОНТЕКСТА**\n\nВыбери чат:", reply_markup=b.as_markup(),
                                  parse_mode="Markdown")


@dp.callback_query(F.data.startswith("admin_set_context_"))
async def cb_set_context(query, state):
    if query.from_user.id != OWNER_ID: return
    chat_id = int(query.data.replace("admin_set_context_", ""))
    await state.update_data(target_chat_id=chat_id)
    await render_admin_menu(query.message, state)


@dp.callback_query(F.data == "admin_manual_chat")
async def cb_manual_chat(query, state):
    if query.from_user.id != OWNER_ID: return
    await state.set_state(AdminEdit.waiting_for_chat_id)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="admin_back")
    await query.message.edit_text("✍️ Отправь ID чата (например `-100123456789`):", reply_markup=b.as_markup())


@dp.message(AdminEdit.waiting_for_chat_id)
async def process_manual_chat(message, state):
    if message.from_user.id != OWNER_ID: return
    try:
        chat_id = int(message.text.strip())
        await state.update_data(target_chat_id=chat_id)
        await state.set_state(None)
        b = InlineKeyboardBuilder()
        b.button(text="‹ В админ-панель", callback_data="admin_back")
        await message.answer(f"✅ Контекст: `{chat_id}`.", reply_markup=b.as_markup(), parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Неверный формат.")


@dp.callback_query(F.data == "admin_back")
async def cb_admin_back(query, state):
    if query.from_user.id != OWNER_ID: return
    await state.set_state(None)
    await render_admin_menu(query.message, state)


# ==================== ГИФКИ ГАЧИ ====================
@dp.callback_query(F.data == "admin_edit_gifs")
async def cb_edit_gifs(query):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    b.button(text="⊱ 🔵 Синяя (3★) ⊰", callback_data="admin_gif_blue")
    b.button(text="⊱ 🟣 Фиолетовая (4★) ⊰", callback_data="admin_gif_purple")
    b.button(text="⊱ 🟡 Золотая (5★) ⊰", callback_data="admin_gif_gold")
    b.button(text="⊱ 💖 Розовая (Захват) ⊰", callback_data="admin_gif_pink")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_back")
    b.adjust(1)
    await query.message.edit_text("🎬 Выбери гифку (можно отправить как видео или файл):", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_gif_"))
async def cb_set_gif(query, state):
    if query.from_user.id != OWNER_ID: return
    rarity = query.data.replace("admin_gif_", "")
    await state.update_data(gif_rarity=rarity)
    await state.set_state(AdminEdit.waiting_for_gif)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="admin_back")
    await query.message.edit_text(f"Отправь GIF/видео/файл для **{rarity}**:", reply_markup=b.as_markup())


@dp.message(AdminEdit.waiting_for_gif, F.animation | F.video | F.document)
async def process_gif(message, state):
    if message.from_user.id != OWNER_ID: return
    rarity = (await state.get_data()).get("gif_rarity")
    file_id = get_media_file_id(message)
    if not file_id: return await message.answer("❌ Отправь GIF/видео/файл.")
    await set_gacha_gif(rarity, file_id)
    await state.set_state(None)
    b = InlineKeyboardBuilder()
    b.button(text="‹ В админ-панель", callback_data="admin_back")
    await message.answer("✅ Гифка сохранена!", reply_markup=b.as_markup())


# ==================== КАРТИНКИ ГАЧИ ====================
@dp.callback_query(F.data == "admin_edit_gacha_imgs")
async def cb_edit_gacha_imgs(query):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    b.button(text="⊱ ⚔️ 3★ Оружие ⊰", callback_data="admin_gimg_cat_3weap_page_0")
    b.button(text="⊱ 👤 4★ Персонажи ⊰", callback_data="admin_gimg_cat_4char_page_0")
    b.button(text="⊱ ⚔️ 4★ Оружие ⊰", callback_data="admin_gimg_cat_4weap_page_0")
    b.button(text="⊱ 👤 5★ Персонажи ⊰", callback_data="admin_gimg_cat_5char_page_0")
    b.button(text="⊱ ⚔️ 5★ Оружие ⊰", callback_data="admin_gimg_cat_5weap_page_0")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_back")
    b.adjust(2, 2, 1, 1)
    await query.message.edit_text("🎨 Выбери категорию:", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_gimg_cat_"))
async def cb_gimg_cat(query, state):
    if query.from_user.id != OWNER_ID: return
    parts = query.data.replace("admin_gimg_cat_", "").split("_page_")
    cat = parts[0]
    page = int(parts[1]) if len(parts) > 1 else 0
    await state.update_data(gimg_cat=cat)

    pool = []
    if cat == "3weap":
        pool = POOL_3_STAR
    elif cat == "4char":
        pool = [i for i in POOL_4_STAR if i["type"] == "char"]
    elif cat == "4weap":
        pool = [i for i in POOL_4_STAR if i["type"] == "weapon"]
    elif cat == "5char":
        pool = [i for i in POOL_5_STAR if i["type"] == "char"]
    elif cat == "5weap":
        pool = [i for i in POOL_5_STAR if i["type"] == "weapon"]

    start, end = page * 10, page * 10 + 10
    b = InlineKeyboardBuilder()
    for idx, item in enumerate(pool[start:end]):
        b.button(text=f"⊱ {item['name']} ⊰", callback_data=f"admin_gimg_set_{start + idx}_{cat}")

    navs = []
    if page > 0: navs.append(("⬅️", f"admin_gimg_cat_{cat}_page_{page - 1}"))
    if end < len(pool): navs.append(("➡️", f"admin_gimg_cat_{cat}_page_{page + 1}"))
    if navs:
        for txt, cb in navs: b.button(text=txt, callback_data=cb)
        b.adjust(2, 2, 2, 2, 2, len(navs), 1)
    else:
        b.button(text="‹ К категориям", callback_data="admin_edit_gacha_imgs")
        b.adjust(2, 2, 2, 2, 2, 1)
    await query.message.edit_text(f"🎨 <b>{cat.upper()}</b>\nСтр. {page + 1}. Выбери предмет:",
                                  reply_markup=b.as_markup(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("admin_gimg_set_"))
async def cb_gimg_set(query, state):
    if query.from_user.id != OWNER_ID: return
    parts = query.data.replace("admin_gimg_set_", "").split("_")
    idx = int(parts[0])
    cat = "_".join(parts[1:])

    pool = []
    if cat == "3weap":
        pool = POOL_3_STAR
    elif cat == "4char":
        pool = [i for i in POOL_4_STAR if i["type"] == "char"]
    elif cat == "4weap":
        pool = [i for i in POOL_4_STAR if i["type"] == "weapon"]
    elif cat == "5char":
        pool = [i for i in POOL_5_STAR if i["type"] == "char"]
    elif cat == "5weap":
        pool = [i for i in POOL_5_STAR if i["type"] == "weapon"]

    item_name = pool[idx]["name"]
    await state.update_data(gacha_img_name=item_name, gimg_cat=cat)
    await state.set_state(AdminEdit.waiting_for_gacha_photo)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data=f"admin_gimg_cat_{cat}_page_{idx // 10}")
    await query.message.edit_text(f"📸 Отправь фото для: **{item_name}**:", reply_markup=b.as_markup(),
                                  parse_mode="Markdown")


@dp.message(AdminEdit.waiting_for_gacha_photo, F.photo | F.document)
async def process_gacha_photo(message, state):
    if message.from_user.id != OWNER_ID: return
    data = await state.get_data()
    file_id = get_media_file_id(message)
    if not file_id: return await message.answer("❌ Отправь фото.")
    await save_gacha_image(data["gacha_img_name"], file_id)
    await state.set_state(None)
    b = InlineKeyboardBuilder()
    b.button(text="🎨 Ещё", callback_data=f"admin_gimg_cat_{data['gimg_cat']}_page_0")
    b.button(text="‹ В админ-панель", callback_data="admin_back")
    b.adjust(1)
    await message.answer("✅ Фото обновлено!", reply_markup=b.as_markup())


# ==================== ПЕРСОНАЖИ ====================
@dp.callback_query(F.data == "admin_edit_chars")
async def cb_edit_chars(query, state):
    if query.from_user.id != OWNER_ID: return
    await state.set_state(None)
    b = InlineKeyboardBuilder()
    b.button(text="⊱ 📸 Сменить фото ⊰", callback_data="admin_char_change_photo")
    b.button(text="⊱ ➕ Добавить персонажа ⊰", callback_data="admin_char_add")
    b.button(text="⊱ 🗑 Удалить персонажа ⊰", callback_data="admin_char_delete")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_back")
    b.adjust(1)
    await query.message.edit_text("🎭 **Управление персонажами**", reply_markup=b.as_markup())


@dp.callback_query(F.data == "admin_char_change_photo")
async def cb_char_change_photo(query):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    for k, v in REGIONS.items(): b.button(text=f"⊱ {v} ⊰", callback_data=f"admin_cchar_reg_{k}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_edit_chars")
    b.adjust(2, 2, 2, 1, 1)
    await query.message.edit_text("📸 Выбери регион:", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_cchar_reg_"))
async def cb_char_pick_region(query):
    if query.from_user.id != OWNER_ID: return
    region = query.data.replace("admin_cchar_reg_", "")
    chars = get_characters_by_region(region)
    if not chars: return await query.answer("Нет персонажей.", show_alert=True)
    b = InlineKeyboardBuilder()
    for ch in chars: b.button(text=f"⊱ {ch} ⊰", callback_data=f"admin_cchar_pick_{ch}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_char_change_photo")
    b.adjust(2, 2, 2, 2, 2)
    await query.message.edit_text("📸 Выбери персонажа:", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_cchar_pick_"))
async def cb_char_pick_name(query, state):
    if query.from_user.id != OWNER_ID: return
    char_name = query.data.replace("admin_cchar_pick_", "")
    await state.update_data(char_name=char_name)
    await state.set_state(AdminEdit.waiting_for_char_photo)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="admin_edit_chars")
    await query.message.edit_text(f"📸 Фото для **{char_name}**:", reply_markup=b.as_markup())


@dp.callback_query(F.data == "admin_char_add")
async def cb_char_add(query):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    for k, v in REGIONS.items(): b.button(text=f"⊱ {v} ⊰", callback_data=f"admin_addchar_reg_{k}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_edit_chars")
    b.adjust(2, 2, 2, 1, 1)
    await query.message.edit_text("➕ Выбери регион:", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_addchar_reg_"))
async def cb_addchar_region(query, state):
    if query.from_user.id != OWNER_ID: return
    await state.update_data(region=query.data.replace("admin_addchar_reg_", ""))
    await state.set_state(AdminEdit.waiting_for_char_name)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="admin_edit_chars")
    await query.message.edit_text("✏️ Напиши имя нового персонажа:", reply_markup=b.as_markup())


@dp.message(AdminEdit.waiting_for_char_name)
async def process_char_name(message, state):
    if message.from_user.id != OWNER_ID: return
    await state.update_data(char_name=message.text.strip())
    await state.set_state(AdminEdit.waiting_for_char_photo)
    await message.answer(f"📸 Отправь фото для **{message.text.strip()}**:")


@dp.callback_query(F.data == "admin_char_delete")
async def cb_char_delete(query):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    for k, v in REGIONS.items(): b.button(text=f"⊱ {v} ⊰", callback_data=f"admin_delchar_reg_{k}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_edit_chars")
    b.adjust(2, 2, 2, 1, 1)
    await query.message.edit_text("🗑 Выбери регион:", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_delchar_reg_"))
async def cb_delchar_region(query):
    if query.from_user.id != OWNER_ID: return
    region = query.data.replace("admin_delchar_reg_", "")
    chars = [name for name in state._custom_chars.keys() if state._custom_chars[name]["region"] == region]
    if not chars: return await query.answer("Нет кастомных персонажей.", show_alert=True)
    b = InlineKeyboardBuilder()
    for ch in chars: b.button(text=f"⊱ {ch} ⊰", callback_data=f"admin_delchar_pick_{ch}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_char_delete")
    b.adjust(2, 2, 2)
    await query.message.edit_text("🗑 Выбери персонажа:", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_delchar_pick_"))
async def cb_delchar_confirm(query):
    if query.from_user.id != OWNER_ID: return
    char_name = query.data.replace("admin_delchar_pick_", "")
    await delete_custom_char(char_name)
    b = InlineKeyboardBuilder()
    b.button(text="⊱ ‹ К персонажам ⊰", callback_data="admin_edit_chars")
    await query.message.edit_text(f"✅ **{char_name}** удалён!", reply_markup=b.as_markup())


@dp.message(AdminEdit.waiting_for_char_photo, F.photo | F.document)
async def process_char_photo(message, state):
    if message.from_user.id != OWNER_ID: return
    data = await state.get_data()
    file_id = get_media_file_id(message)
    if not file_id: return await message.answer("❌ Отправь фото.")
    if data.get("region"):
        await save_custom_char(data["char_name"], data["region"], file_id)
        msg = f"✅ Добавлен **{data['char_name']}**!"
    else:
        await save_char_photo(data["char_name"], file_id)
        msg = f"✅ Фото для **{data['char_name']}** обновлено!"
    await state.set_state(None)
    b = InlineKeyboardBuilder()
    b.button(text="🎭 Ещё", callback_data="admin_edit_chars")
    b.button(text="‹ В админ-панель", callback_data="admin_back")
    b.adjust(1)
    await message.answer(msg, reply_markup=b.as_markup())


# ==================== ТЕКСТЫ ====================
@dp.callback_query(F.data == "admin_edit_texts")
async def cb_edit_texts(query):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    for key, name in EDITABLE_TEXTS.items(): b.button(text=f"⊱ {name} ⊰", callback_data=f"admin_set_{key}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_back")
    b.adjust(2, 2, 2, 2, 2, 1)
    await query.message.edit_text("📝 **Выбери текст:**", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_set_"))
async def cb_set_text(query, state):
    if query.from_user.id != OWNER_ID: return
    key = query.data.replace("admin_set_", "")
    await state.update_data(setting_key=key)
    await state.set_state(AdminEdit.waiting_for_text)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="admin_edit_texts")
    await query.message.edit_text(
        f"📝 Отправь новый текст для: **{EDITABLE_TEXTS.get(key, key)}**\n\nПеременные: `{name}`, `{div}`",
        reply_markup=b.as_markup(), parse_mode="Markdown")


@dp.message(AdminEdit.waiting_for_text, F.text)
async def process_new_text(message, state):
    if message.from_user.id != OWNER_ID: return
    data = await state.get_data()
    await set_local_setting(data["setting_key"], message.html_text, data.get("target_chat_id", 0))
    await state.set_state(None)
    b = InlineKeyboardBuilder()
    b.button(text="⊱ ‹ В меню текстов ⊰", callback_data="admin_edit_texts")
    await message.answer("✅ Текст сохранён!", reply_markup=b.as_markup())


# ==================== КАРТИНКИ РАЗДЕЛОВ ====================
@dp.callback_query(F.data == "admin_edit_photos")
async def cb_edit_photos(query):
    if query.from_user.id != OWNER_ID: return
    b = InlineKeyboardBuilder()
    for key, name in EDITABLE_PHOTOS.items(): b.button(text=f"⊱ {name} ⊰", callback_data=f"admin_photo_{key}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="admin_back")
    b.adjust(2, 2, 2, 2, 2, 2, 2, 1)
    await query.message.edit_text("🖼 **Выбери раздел:**", reply_markup=b.as_markup())


@dp.callback_query(F.data.startswith("admin_photo_"))
async def cb_set_photo(query, state):
    if query.from_user.id != OWNER_ID: return
    key = query.data.replace("admin_photo_", "")
    await state.update_data(setting_key=f"image_{key}")
    await state.set_state(AdminEdit.waiting_for_photo)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="admin_edit_photos")
    await query.message.edit_text(f"🖼 Отправь фото для: **{EDITABLE_PHOTOS.get(key, key)}**",
                                  reply_markup=b.as_markup(), parse_mode="Markdown")


@dp.message(AdminEdit.waiting_for_photo, F.photo | F.document)
async def process_new_photo(message, state):
    if message.from_user.id != OWNER_ID: return
    data = await state.get_data()
    file_id = get_media_file_id(message)
    if not file_id: return await message.answer("❌ Отправь фото.")
    await set_local_setting(data["setting_key"], file_id, data.get("target_chat_id", 0))
    await state.set_state(None)
    b = InlineKeyboardBuilder()
    b.button(text="🖼 Ещё", callback_data="admin_edit_photos")
    b.button(text="‹ В админ-панель", callback_data="admin_back")
    b.adjust(1)
    await message.answer("✅ Картинка обновлена!", reply_markup=b.as_markup())