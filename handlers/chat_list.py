from aiogram import types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import aiosqlite
from config import DB_PATH
from telegraph import Telegraph

from bot_instance import bot, dp
from db import (
    set_group_channel, get_group_channel, set_group_font, get_group_font,
    set_custom_name, get_custom_names, get_local_setting, set_local_setting,
    get_setting, set_setting
)
from characters import REGIONS, CHARACTERS, normalize_character_name
from fonts import apply_font
from helpers import is_chat_admin
import state


async def get_telegraph_client():
    """Получаем или создаем клиент Telegraph (с безопасным сохранением токена)"""
    token = await get_setting("telegraph_token")
    tg = Telegraph()

    if token:
        # Если токен есть, создаем клиент с ним
        tg = Telegraph(access_token=token)
    else:
        import random, string
        rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        try:
            # create_account возвращает объект Account, из которого берем токен
            account = tg.create_account(short_name=f'Orion_{rand_str}')
            await set_setting("telegraph_token", account.access_token)
        except Exception as e:
            print(f"❌ Ошибка создания аккаунта Telegraph: {e}")
            raise e
    return tg


async def update_chat_list(group_id: int):
    channel_id, msg_id = await get_group_channel(group_id)
    if not channel_id or not msg_id:
        return False

    font_style = await get_group_font(group_id)
    custom_fonts = await get_custom_names(group_id)

    taken_users = {}
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
                "SELECT character_name, search_rp_partner FROM users WHERE character_name IS NOT NULL AND character_name != '' AND chat_id = ?",
                (group_id,)) as cur:
            for row in await cur.fetchall():
                taken_users[row["character_name"]] = row["search_rp_partner"] or ""

    # Генерируем HTML для Telegraph
    html_content = "<p>Занят - ☒<br>Ищет сорол - ⨂<br>Свободен - пусто</p>"

    for reg_key, reg_name in REGIONS.items():
        display_reg = reg_name.split(" ", 1)[1] if " " in reg_name else reg_name

        chars_in_reg = [name for name, data in CHARACTERS.items() if data["region"] == reg_key]
        custom_chars = [name for name, data in state._custom_chars.items() if data["region"] == reg_key]
        chars_in_reg.extend(custom_chars)

        if not chars_in_reg:
            continue

        char_list = []
        for ch in sorted(chars_in_reg):
            norm_name = normalize_character_name(ch)
            display_name = apply_font(norm_name, font_style) if font_style != "none" else norm_name
            if norm_name in custom_fonts:
                display_name = custom_fonts[norm_name]

            status = ""
            if ch in taken_users:
                status = " - ☒ ⨂" if taken_users[ch] else " - ☒"

            if len(display_name) > 16:
                display_name = display_name[:15] + "…"
            char_list.append(f"{display_name}{status}")

        region_text = []
        for i in range(0, len(char_list), 2):
            left = char_list[i]
            right = char_list[i + 1] if i + 1 < len(char_list) else ""

            if right:
                region_text.append(f"{left:<22} {right}")
            else:
                region_text.append(left)

        html_content += f"<h3>{display_reg}</h3>"
        html_content += f"<pre>{'\n'.join(region_text)}</pre>"

    # Пробуем создать страницу в Telegraph
    telegraph_url = None
    try:
        tg = await get_telegraph_client()
        # В новых версиях библиотеки используется content_html
        page = tg.create_page(
            title='Список ролей',
            content_html=html_content,
            author_name='Орион'
        )
        telegraph_url = page['url']
    except Exception as e:
        print(f"❌ Ошибка Telegraph: {e}")
        telegraph_url = None

    custom_img = await get_local_setting("image_rolelist", group_id)

    # Создаем кнопку, если ссылка есть
    kb = None
    if telegraph_url:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📜 Открыть полный список", url=telegraph_url)]
        ])
        caption = "＿＿＿＿ [ Список ролей ] ＿＿＿＿\n\nНажми на кнопку ниже, чтобы посмотреть всех персонажей и их статус 👇"
    else:
        caption = "＿＿＿＿ [ Список ролей ] ＿＿＿＿\n\n⚠️ Не удалось загрузить полный список (Ошибка Телеграфа)."

    # Обновляем сообщение (картинку + текст + кнопку)
    try:
        if custom_img:
            media = InputMediaPhoto(media=custom_img, caption=caption, parse_mode="HTML")
        else:
            media = InputMediaPhoto(media=FSInputFile("images/list_banner.jpg"), caption=caption, parse_mode="HTML")

        await bot.edit_message_media(chat_id=channel_id, message_id=msg_id, media=media, reply_markup=kb)
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return True  # Игнорируем, если сообщение не изменилось
        print(f"❌ Ошибка при редактировании фото: {e}")
    except Exception as e:
        print(f"❌ Ошибка при редактировании фото: {e}")

    # Если не удалось отредактировать медиа, пробуем обновить только подпись
    try:
        await bot.edit_message_caption(chat_id=channel_id, message_id=msg_id, caption=caption, parse_mode="HTML",
                                       reply_markup=kb)
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return True
        print(f"❌ Ошибка при редактировании подписи: {e}")
    except Exception as e:
        print(f"❌ Ошибка при редактировании подписи: {e}")

    return False


@dp.message(Command("setlist"))
async def cmd_setlist(message: types.Message):
    if message.chat.type not in ("group", "supergroup"): return
    if not await is_chat_admin(message.chat.id, message.from_user.id): return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Инструкция: /setlist @username_канала")
        return

    channel_username = parts[1].strip()
    try:
        channel = await bot.get_chat(channel_username)
        channel_id = channel.id

        member = await bot.get_chat_member(channel_id, bot.id)
        if member.status not in ("administrator", "creator"):
            await message.answer("❌ Бот не админ в канале.")
            return

        existing_channel, existing_msg_id = await get_group_channel(message.chat.id)

        if existing_channel == channel_id and existing_msg_id:
            await update_chat_list(message.chat.id)
            await message.answer(f"✅ Список в канале <b>{channel.title}</b> обновлен!", parse_mode="HTML")
        else:
            custom_img = await get_local_setting("image_rolelist", message.chat.id)
            try:
                if custom_img:
                    msg = await bot.send_photo(channel_id, custom_img, caption="🔄 Генерирую список ролей...")
                else:
                    photo = FSInputFile("images/list_banner.jpg")
                    msg = await bot.send_photo(channel_id, photo, caption="🔄 Генерирую список ролей...")
            except Exception:
                await message.answer("❌ Ошибка: Файл images/list_banner.jpg не найден.")
                return

            await set_group_channel(message.chat.id, channel_id, msg.message_id)
            await update_chat_list(message.chat.id)

            try:
                await bot.pin_chat_message(chat_id=channel_id, message_id=msg.message_id, disable_notification=True)
            except Exception:
                pass

            await message.answer(f"✅ Список создан в канале <b>{channel.title}</b>!", parse_mode="HTML")

        await message.delete()
    except Exception as e:
        await message.answer(f"❌ Ошибка: <code>{e}</code>", parse_mode="HTML")


@dp.message(Command("font"))
async def cmd_font(message: types.Message):
    if message.chat.type not in ("group", "supergroup"): return
    if not await is_chat_admin(message.chat.id, message.from_user.id): return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("🎨 Доступные стили: bold, italic, monospace, none\nПример: <code>/font bold</code>",
                             parse_mode="HTML")
        return

    style = parts[1].lower()
    if style not in ("bold", "italic", "monospace", "none"):
        await message.answer("❌ Неизвестный стиль.")
        return

    await set_group_font(message.chat.id, style)
    success = await update_chat_list(message.chat.id)
    if success:
        await message.answer(f"✅ Стиль изменен на: <b>{style}</b>", parse_mode="HTML")
    else:
        await message.answer(f"⚠️ Стиль сохранен, но канал не обновлен.", parse_mode="HTML")


@dp.message(Command("setname"))
async def cmd_setname(message: types.Message):
    if message.chat.type not in ("group", "supergroup"): return
    if not await is_chat_admin(message.chat.id, message.from_user.id): return

    text = message.text.replace("/setname", "").strip()
    if "=" not in text:
        await message.answer("⚠️ Формат: <code>/setname Имя = Шрифт</code>", parse_mode="HTML")
        return

    parts = text.split("=", 1)
    await set_custom_name(message.chat.id, parts[0].strip(), parts[1].strip())
    await update_chat_list(message.chat.id)
    await message.answer(f"✅ Имя заменено!", parse_mode="HTML")