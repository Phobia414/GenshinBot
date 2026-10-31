from aiogram import types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InputMediaPhoto
import aiosqlite
from config import DB_PATH

from bot_instance import bot, dp
from db import (
    set_group_channel, get_group_channel, set_group_font, get_group_font,
    set_custom_name, get_custom_names, get_local_setting
)
from characters import REGIONS, CHARACTERS, normalize_character_name
from fonts import apply_font
from helpers import is_chat_admin
import state


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

    lines = ["＿＿＿＿ [ Список ролей ] ＿＿＿＿\n"]
    lines.append("Занят - ☒")
    lines.append("Ищет сорол - ⨂")
    lines.append("Свободен - \n")

    for reg_key, reg_name in REGIONS.items():
        display_reg = reg_name.split(" ", 1)[1] if " " in reg_name else reg_name

        chars_in_reg = [name for name, data in CHARACTERS.items() if data["region"] == reg_key]
        custom_chars = [name for name, data in state._custom_chars.items() if data["region"] == reg_key]
        chars_in_reg.extend(custom_chars)

        if not chars_in_reg:
            continue

        block_lines = [f"<b>{display_reg}</b>"]

        for ch in sorted(chars_in_reg):
            norm_name = normalize_character_name(ch)
            display_name = apply_font(norm_name, font_style) if font_style != "none" else norm_name
            if norm_name in custom_fonts:
                display_name = custom_fonts[norm_name]

            if ch in taken_users:
                co_role = taken_users[ch]
                if co_role:
                    block_lines.append(f"{display_name} - ☒ ⨂ <i>(ищет: {co_role})</i>")
                else:
                    block_lines.append(f"{display_name} - ☒")
            else:
                block_lines.append(display_name)

        block_text = "\n".join(block_lines)
        lines.append(f"<blockquote expandable>{block_text}</blockquote>\n")

    text = "\n".join(lines)

    custom_img = await get_local_setting("image_rolelist", group_id)

    try:
        if custom_img:
            media = InputMediaPhoto(media=custom_img, caption=text, parse_mode="HTML")
        else:
            media = InputMediaPhoto(media=FSInputFile("images/list_banner.jpg"), caption=text, parse_mode="HTML")

        await bot.edit_message_media(chat_id=channel_id, message_id=msg_id, media=media)
        return True
    except Exception as e:
        print(f"❌ Ошибка при обновлении списка с фото: {e}")
        try:
            await bot.edit_message_caption(chat_id=channel_id, message_id=msg_id, caption=text, parse_mode="HTML")
            return True
        except Exception as e2:
            print(f"❌ Ошибка при обновлении подписи: {e2}")
            return False


@dp.message(Command("setlist"))
async def cmd_setlist(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    if not await is_chat_admin(message.chat.id, message.from_user.id):
        await message.answer("❌ Только для админов чата.")
        return

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

        custom_img = await get_local_setting("image_rolelist", message.chat.id)
        try:
            if custom_img:
                msg = await bot.send_photo(channel_id, custom_img, caption="🔄 Генерирую список ролей...")
            else:
                photo = FSInputFile("images/list_banner.jpg")
                msg = await bot.send_photo(channel_id, photo, caption="🔄 Генерирую список ролей...")
        except Exception:
            await message.answer(
                "❌ Ошибка: Файл images/list_banner.jpg не найден. Закиньте баннер в папку images или загрузите его через админ-панель.")
            return

        await set_group_channel(message.chat.id, channel_id, msg.message_id)
        await update_chat_list(message.chat.id)

        try:
            await bot.pin_chat_message(chat_id=channel_id, message_id=msg.message_id, disable_notification=True)
        except Exception:
            await message.answer("⚠️ Не удалось закрепить сообщение. Дай боту право 'Закреплять сообщения' в канале.")

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
        await message.answer(
            "🎨 <b>Доступные стили шрифта:</b>\n\n"
            "• <code>/font bold</code> — Жирный\n"
            "• <code>/font italic</code> — Курсив\n"
            "• <code>/font monospace</code> — Моно\n"
            "• <code>/font none</code> — Обычный (сброс)\n\n"
            "<i>Шрифт применится ко всем персонажам сразу.</i>",
            parse_mode="HTML"
        )
        return

    style = parts[1].lower()
    if style not in ("bold", "italic", "monospace", "none"):
        await message.answer("❌ Неизвестный стиль. Используй bold, italic, monospace или none.")
        return

    await set_group_font(message.chat.id, style)
    success = await update_chat_list(message.chat.id)

    if success:
        await message.answer(f"✅ Стиль списка в канале изменен на: <b>{style}</b>", parse_mode="HTML")
    else:
        await message.answer(f"⚠️ Стиль <b>{style}</b> сохранен, но канал не обновлен.", parse_mode="HTML")


@dp.message(Command("setname"))
async def cmd_setname(message: types.Message):
    if message.chat.type not in ("group", "supergroup"): return
    if not await is_chat_admin(message.chat.id, message.from_user.id): return

    text = message.text.replace("/setname", "").strip()
    if "=" not in text:
        await message.answer("⚠️ Формат: <code>/setname ОбычноеИмя = КрасивыйШрифт</code>", parse_mode="HTML")
        return

    parts = text.split("=", 1)
    default_name = parts[0].strip()
    custom_name = parts[1].strip()

    await set_custom_name(message.chat.id, default_name, custom_name)
    await update_chat_list(message.chat.id)
    await message.answer(f"✅ Готово! <b>{default_name}</b> → <b>{custom_name}</b>", parse_mode="HTML")