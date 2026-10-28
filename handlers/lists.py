from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp
from callbacks import MenuCB, ListsCB, CmdCatCB
from config import OWNER_ID
from constants import DIV, PLAYER_COMMANDS
from helpers import esc, edit_or_send, get_characters_status, is_chat_admin
from keyboards import lists_kb, commands_cats_kb


@dp.callback_query(MenuCB.filter(F.action == "lists"))
async def cb_lists(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    text = f"📖 СПИСКИ\n{DIV}\n\n• 📜 Команды\n• 🎭 Персонажи"
    await edit_or_send(query, text, lists_kb(query.from_user.id))


@dp.callback_query(ListsCB.filter(F.action == "commands"))
async def cb_lists_cmds(query: types.CallbackQuery, callback_data: ListsCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    chat_id = query.message.chat.id if query.message else 0
    is_admin = False

    if chat_id != 0:
        is_admin = await is_chat_admin(chat_id, query.from_user.id)
    if query.from_user.id == OWNER_ID:
        is_admin = True

    text = f"📜 СПИСОК КОМАНД\n{DIV}\n\nВыбери категорию:"
    await edit_or_send(query, text, commands_cats_kb(query.from_user.id, is_admin))


@dp.callback_query(CmdCatCB.filter())
async def cb_cmd_cat(query: types.CallbackQuery, callback_data: CmdCatCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    chat_id = query.message.chat.id if query.message else 0

    if callback_data.cat == "admin_owner" and query.from_user.id != OWNER_ID:
        await query.answer("❌ Только для владельца бота.", show_alert=True)
        return

    if callback_data.cat == "admin_chat":
        if query.from_user.id != OWNER_ID:
            if chat_id == 0 or not await is_chat_admin(chat_id, query.from_user.id):
                await query.answer("❌ Только для админов этого чата.", show_alert=True)
                return

    data = PLAYER_COMMANDS.get(callback_data.cat)
    if not data:
        await query.answer("❌ Не найдено", show_alert=True)
        return

    lines = [f"{data['title']}\n{DIV}\n"]
    for cmd, desc in data["commands"]:
        lines.append(f"• {cmd}\n  {desc}")
    lines.append(f"\n{DIV}\n\n💡 «ответом» — Reply на сообщение.")

    b = InlineKeyboardBuilder()
    b.button(text="‹ К категориям", callback_data=ListsCB(action="commands", owner_id=query.from_user.id))
    b.button(text="📖 В меню ›", callback_data=MenuCB(action="menu", owner_id=query.from_user.id))
    b.adjust(1)
    text = "\n".join(lines)
    await edit_or_send(query, text, b.as_markup(), image_url="")


@dp.callback_query(ListsCB.filter(F.action == "characters"))
async def cb_lists_chars(query: types.CallbackQuery, callback_data: ListsCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return

    chat_id = query.message.chat.id if query.message else 0
    occ, free = await get_characters_status(chat_id)

    occ_by_reg = {}
    for rn, ch, _ in occ:
        occ_by_reg.setdefault(rn, []).append(ch)
    free_by_reg = {}
    for rn, ch in free:
        free_by_reg.setdefault(rn, []).append(ch)

    lines = [f"🎭 СПИСОК ПЕРСОНАЖЕЙ\n{DIV}\n"]

    lines.append(f"🔴 Занятые ({len(occ)}):")
    if occ_by_reg:
        for rn, chs in occ_by_reg.items():
            lines.append(f"{rn}:")
            for ch in chs:
                lines.append(f"  • {ch}")
    else:
        lines.append("(никого)")

    lines.append(f"\n🟢 Свободные ({len(free)}):")
    if free_by_reg:
        for rn, chs in free_by_reg.items():
            lines.append(f"{rn}:")
            for ch in chs:
                lines.append(f"  • {ch}")
    else:
        lines.append("(все заняты!)")

    b = InlineKeyboardBuilder()
    b.button(text="‹ К спискам", callback_data=MenuCB(action="lists", owner_id=query.from_user.id))

    text = "\n".join(lines)

    # Уменьшен лимит до 3500 символов для защиты от ошибки "Message is too long"
    if len(text) > 3500:
        lines_short = [f"🎭 СПИСОК ПЕРСОНАЖЕЙ\n{DIV}\n"]
        lines_short.append(f"🔴 Занятые ({len(occ)}):")
        if occ_by_reg:
            for rn, chs in occ_by_reg.items():
                lines_short.append(f"{rn}: {', '.join(chs)}")
        else:
            lines_short.append("(никого)")
        lines_short.append(f"\n🟢 Свободные — по регионам:")
        for rn, chs in free_by_reg.items():
            lines_short.append(f"{rn}: {len(chs)} чел.")
        text = "\n".join(lines_short)

    await edit_or_send(query, text, b.as_markup(), image_url="")