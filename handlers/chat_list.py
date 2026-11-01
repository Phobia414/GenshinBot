from aiogram import types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InputMediaPhoto
from aiogram.exceptions import TelegramBadRequest
import aiosqlite
from config import DB_PATH

from bot_instance import bot, dp
from db import (
    set_group_channel, get_group_channel, set_group_font, get_group_font,
    set_custom_name, get_custom_names, get_local_setting, set_local_setting
)
from characters import REGIONS, CHARACTERS, normalize_character_name
from fonts import apply_font
from helpers import is_chat_admin
import state


async def update_chat_list(group_id: int):
    channel_id, msg_id = await get_group_channel(group_id)
    if not channel_id or not msg_id:
        return False

    text_msg_id = await get_local_setting("list_text_msg", group_id)
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

    # === ГЕНЕРАЦИЯ ТЕКСТА ПО ТЗ ===
    lines = ["▰▰▰ 〔 Список персонажей 〕 ▰▰▰\n"]

    for reg_key, reg_name in REGIONS.items():
        display_reg = reg_name.split(" ", 1)[1] if " " in reg_name else reg_name

        chars_in_reg = [name for name, data in CHARACTERS.items() if data["region"] == reg_key]
        custom_chars = [name for name, data in state._custom_chars.items() if data["region"] == reg_key]
        chars_in_reg.extend(custom_chars)

        if not chars_in_reg:
            continue

        occupied = []
        searching = []
        free = []

        for ch in sorted(chars_in_reg):
            norm_name = normalize_character_name(ch)
            display_name = apply_font(norm_name, font_style) if font_style != "none" else norm_name
            if norm_name in custom_fonts:
                display_name = custom_fonts[norm_name]

            if ch in taken_users:
                partner = taken_users[ch]
                if partner:
                    searching.append(f"{partner} (Для {display_name})")
                else:
                    occupied.append(display_name)
            else:
                free.append(display_name)

        region_lines = []
        region_lines.append("▱▱▱▱▱▱▱▱▱▱▱")
        region_lines.append(display_reg)
        region_lines.append("▱▱▱▱▱▱▱▱▱▱▱")

        if occupied:
            region_lines.append(f"Занятые: {', '.join(occupied)}")
            region_lines.append("")

        if searching:
            region_lines.append(f"Нужны в соролы: {', '.join(searching)}")
            region_lines.append("")

        if free:
            region_lines.append(f"Свободные: {', '.join(free)}")
            region_lines.append("")

        lines.append("\n".join(region_lines).strip())

    inner_text = "\n\n".join(lines)
    full_text = f"<b><code>{inner_text}</code></b>"

    # === РЕЖИМ 1: Текст короткий (помещается в подпись к фото) ===
    if len(full_text) <= 1024:
        if text_msg_id:
            try:
                await bot.delete_message(chat_id=channel_id, message_id=int(text_msg_id))
            except Exception:
                pass
            await set_local_setting("list_text_msg", "", group_id)

        try:
            await bot.edit_message_caption(
                chat_id=channel_id,
                message_id=msg_id,
                caption=full_text,
                parse_mode="HTML"
            )
            return True
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return True
            try:
                custom_img = await get_local_setting("image_rolelist", group_id)
                media = InputMediaPhoto(media=custom_img or FSInputFile("images/list_banner.jpg"), caption=full_text,
                                        parse_mode="HTML")
                await bot.edit_message_media(chat_id=channel_id, message_id=msg_id, media=media)
                return True
            except Exception as e2:
                print(f"❌ Ошибка при редактировании: {e2}")
                return False

    # === РЕЖИМ 2: Текст длинный (Редактируем фото и текст отдельно) ===
    else:
        # ВОТ ТУТ МЫ УБРАЛИ ЗАГОЛОВОК С ВЕНЗЕЛЯМИ, ОСТАВИЛИ ТОЛЬКО СТРЕЛОЧКУ
        caption = ""

        if text_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=channel_id,
                    message_id=int(text_msg_id),
                    text=full_text,
                    parse_mode="HTML"
                )
                try:
                    await bot.edit_message_caption(
                        chat_id=channel_id,
                        message_id=msg_id,
                        caption=caption,
                        parse_mode="HTML"
                    )
                except TelegramBadRequest:
                    pass
                return True
            except Exception as e:
                print(f"⚠️ Не удалось отредактировать старые сообщения, создаем новые: {e}")

        try:
            await bot.delete_message(chat_id=channel_id, message_id=msg_id)
        except Exception:
            pass

        custom_img = await get_local_setting("image_rolelist", group_id)
        try:
            if custom_img:
                photo_msg = await bot.send_photo(channel_id, custom_img, caption=caption, parse_mode="HTML")
            else:
                photo_msg = await bot.send_photo(channel_id, FSInputFile("images/list_banner.jpg"), caption=caption,
                                                 parse_mode="HTML")
        except Exception as e:
            print(f"❌ Ошибка отправки фото: {e}")
            return False

        try:
            text_msg = await bot.send_message(channel_id, full_text, parse_mode="HTML",
                                              reply_to_message_id=photo_msg.message_id)
        except Exception as e:
            print(f"❌ Ошибка отправки текста: {e}")
            return False

        await set_group_channel(group_id, channel_id, photo_msg.message_id)
        await set_local_setting("list_text_msg", text_msg.message_id, group_id)

        try:
            await bot.pin_chat_message(channel_id, photo_msg.message_id, disable_notification=True)
        except Exception:
            pass
        return True


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
                    msg = await bot.send_photo(channel_id, custom_img, caption="🔄 Генерирую список...")
                else:
                    photo = FSInputFile("images/list_banner.jpg")
                    msg = await bot.send_photo(channel_id, photo, caption="🔄 Генерирую список...")
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