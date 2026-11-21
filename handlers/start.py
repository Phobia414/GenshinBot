import time
import hashlib
import asyncio
from datetime import datetime, timezone
from aiogram import types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from callbacks import MenuCB, RegionCB, CharCB
from config import CREATOR_USERNAME, PRICE_ROLE_CHANGE
from db import get_user, update_user, is_character_taken, get_taken_characters, get_local_setting, get_application, \
    update_application_status, fetch_all, get_setting, get_guild, get_rep_level, get_rep_progress, update_resin, \
    RESIN_MAX, get_food_buff, get_total_bonuses
from characters import REGIONS, get_character_image, CHARACTERS
from constants import DIV, PLACEHOLDER_IMAGES, WARN_LIMIT, REP_PER_MESSAGE, REP_PER_BOARD_TASK, REP_PER_DUNGEON, \
    REP_PER_WORLD_BOSS_KILL, REP_PER_GUILD_BOSS_KILL, REP_PER_GUILD_CREATE, REP_PER_DONATE_UNIT, REP_PER_DONATE_MAX
from helpers import (
    esc, user_display_name, get_placeholder_image, _ensure_user,
    edit_or_send, get_section_image, find_region_by_character, get_reputation_bonuses,
    get_reputation_title, inject_user, format_text, update_user_tag, get_ranks_config
)
from keyboards import (
    gender_kb, regions_kb, characters_kb, main_menu_kb, profile_kb, adventurers_kb,
    reputation_kb, back_kb
)
from handlers.apply import ApplyForm, FORM_STEPS, send_step
from handlers.chat_list import update_chat_list
from handlers.reports import process_report_start
from handlers.subscription import send_sub_message
import state as bot_state


def get_name_by_hash(chash: str) -> str:
    if len(chash) > 15:
        return chash
    for name in CHARACTERS.keys():
        if hashlib.md5(name.encode()).hexdigest()[:10] == chash:
            return name
    for name in bot_state._custom_chars.keys():
        if hashlib.md5(name.encode()).hexdigest()[:10] == chash:
            return name
    return chash


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject):
    current_state = await state.get_state()

    # Если перешли по ссылке на жалобу
    if command.args and command.args.startswith("report_"):
        chat_id_report = int(command.args.replace("report_", ""))
        await process_report_start(message, chat_id_report, state)
        return

    # Если перешли по ссылке на анкету админа
    if command.args and command.args.startswith("admin_apply_"):
        from handlers.admin_apply import start_admin_apply
        try:
            chat_id = int(command.args.split("_")[2])
            await start_admin_apply(message, state, chat_id)
        except:
            await start_admin_apply(message, state, 0)
        return

    if current_state:
        await state.clear()  # СБРАСЫВАЕМ ВСЕ ЗАВИСШИЕ СОСТОЯНИЯ (Анкеты, Жалобы)

    chat_id = message.chat.id
    user = await _ensure_user(message.from_user.id, chat_id)

    if message.chat.type == "private":
        if command.args and command.args.startswith("apply_"):
            target_chat_id = int(command.args.replace("apply_", ""))
            app = await get_application(message.from_user.id, target_chat_id)
            if app and app['status'] in ('pending', 'waiting_char'):
                return await message.answer("⏳ Ваша анкета уже на рассмотрении или одобрена. Ожидайте.")

            await state.update_data(target_chat_id=target_chat_id)
            await send_step(message.chat.id, 0, state)
        else:
            await message.answer(
                "🌸 Возьмите ссылку для заполнения анкеты у администраторов группы.\n\n<i>Для игры перейдите в группу и напишите /start там.</i>",
                parse_mode="HTML")
        return

    if user["character_name"]:
        if chat_id > 0:
            await update_user_tag(bot, chat_id, message.from_user.id, user)

        name = esc(user_display_name(user))
        text = f"── 〔 🌟 ГЛАВНОЕ МЕНЮ 〕 ──\n\n🍃 Привет, <b>{name}</b>!\n\nКуда отправимся сегодня?"
        await message.answer(text, reply_markup=main_menu_kb(message.from_user.id), parse_mode="HTML")
    else:
        sub_enabled = await get_setting("sub_enabled", "0")
        if sub_enabled == "1" and user.get("sub_passed") == 0:
            await send_sub_message(message, message.from_user.id, chat_id)
        else:
            # УБРАН ВЫБОР ПОЛА, СРАЗУ РЕГИОНЫ
            text = f"── 〔 🌸 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nВыбери регион, откуда родом твой герой 🎭"
            await message.answer(text, reply_markup=regions_kb(message.from_user.id), parse_mode="HTML")


@dp.callback_query(MenuCB.filter(F.action.in_(["gender_male", "gender_female"])))
async def cb_gender(query: types.CallbackQuery, callback_data: MenuCB, state: FSMContext):
    await state.clear()
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    g = "male" if callback_data.action == "gender_male" else "female"
    await update_user(query.from_user.id, chat_id, gender=g)

    user = await get_user(query.from_user.id, chat_id)

    if user and user.get("character_name"):
        text = f"── 〔 💖 ОТЛИЧНО! 〕 ──\n\nПол успешно обновлен.\n\nТвой персонаж: <b>{esc(user['character_name'])}</b>"
        fallback = get_character_image(user["character_name"]) if user["character_name"] else None
        image = await get_section_image("menu", fallback, chat_id)
        await edit_or_send(query, text, main_menu_kb(query.from_user.id), image_url=image)
    else:
        text = f"── 〔 💖 ОТЛИЧНО! 〕 ──\n\nТеперь выбери регион, откуда родом твой герой 🎭"
        image = await get_section_image("regions", chat_id=chat_id)
        await edit_or_send(query, text, regions_kb(query.from_user.id), image_url=image)


@dp.callback_query(MenuCB.filter(F.action == "regions"))
async def cb_regions(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    text = f"── 〔 🌍 ВЫБОР РЕГИОНА 〕 ──\n\nВыбери регион, Путешественник:"
    image = await get_section_image("regions", chat_id=query.message.chat.id)
    await edit_or_send(query, text, regions_kb(query.from_user.id), image_url=image)


@dp.callback_query(RegionCB.filter())
async def cb_region(query: types.CallbackQuery, callback_data: RegionCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return
    chat_id = query.message.chat.id
    taken = await get_taken_characters(chat_id)
    region_name = REGIONS[callback_data.region]
    text = f"── 〔 🎭 РЕГИОН: {region_name.upper()} 〕 ──\n\nВыбери того, кто станет твоим воплощением ✨"

    image = await get_section_image(f"region_{callback_data.region}", chat_id=chat_id)
    if not image:
        image = await get_section_image("regions", chat_id=chat_id)

    await edit_or_send(query, text, characters_kb(query.from_user.id, callback_data.region, taken), image_url=image)


@dp.callback_query(CharCB.filter())
async def cb_character(query: types.CallbackQuery, callback_data: CharCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Это чужое меню!", show_alert=True)
        return

    chat_id = query.message.chat.id

    if query.message.chat.type == "private":
        await query.answer("❌ Выбор персонажа доступен только в группе!", show_alert=True)
        return

    user = await get_user(query.from_user.id, chat_id)
    name = get_name_by_hash(callback_data.character)

    if user["character_name"] and not user["char_change_paid"]:
        await query.answer("❌ У тебя уже есть персонаж. Смену можно купить в Лавке!", show_alert=True)
        return
    if await is_character_taken(name, chat_id):
        await query.answer(f"❌ {name} уже занят.", show_alert=True)
        return

    await update_user(query.from_user.id, chat_id, character_name=name, char_change_paid=0)
    await update_chat_list(chat_id)

    chat = query.message.chat

    # Обновляем тег с сохранением ранга
    updated_user_data = await get_user(query.from_user.id, chat_id)
    await update_user_tag(bot, chat.id, query.from_user.id, updated_user_data)

    app = await get_application(query.from_user.id, chat_id)
    if app and app['status'] == 'waiting_char':
        await update_application_status(query.from_user.id, chat_id, 'joined')
        text = (
            f"🎉 <b>У нас новенький! Встречайте!</b>\n\n"
            f"🎭 <b>Роль:</b> {esc(name)}\n\n"
            f"📖 <b>Опыт:</b> {esc(app['experience'])}\n"
            f"🌟 <b>О себе:</b> {esc(app['about'])}\n"
            f"🕒 <b>Часовой пояс:</b> {esc(app['timezone'])}\n"
            f"⚠️ <b>Триггеры:</b> {esc(app['triggers'])}\n"
            f"⚡ <b>Активность:</b> {esc(app['activity'])}"
        )
        await bot.send_message(chat_id, text, parse_mode="HTML")
        try:
            await query.message.delete()
        except:
            pass

        await bot.send_message(chat_id, f"✅ Анкета опубликована! Добро пожаловать в игру, {esc(name)}!",
                               reply_markup=main_menu_kb(query.from_user.id), parse_mode="HTML")
    else:
        text = f"── 〔 🎉 ДОБРО ПОЖАЛОВАТЬ! 〕 ──\n\nТеперь ты — <b>{esc(name)}</b>!\n\nОрион рад за тебя! 💛"

        try:
            await query.message.delete()
        except Exception:
            pass

        char_image = get_character_image(name)

        if char_image:
            try:
                msg = await bot.send_photo(chat.id, photo=char_image, caption=text,
                                           reply_markup=main_menu_kb(query.from_user.id), parse_mode="HTML")
            except:
                msg = await bot.send_message(chat.id, text=text, reply_markup=main_menu_kb(query.from_user.id),
                                             parse_mode="HTML")
        else:
            msg = await bot.send_message(chat.id, text=text, reply_markup=main_menu_kb(query.from_user.id),
                                         parse_mode="HTML")

        bot_state._last_bot_msg[chat.id] = msg.message_id

    # ===== АВТО-СОЗЫВ ПОСЛЕ ВЫБОРА ПЕРСОНАЖА =====
    try:
        users = await fetch_all(
            "SELECT user_id, username, character_name FROM users "
            "WHERE chat_id = ? AND character_name IS NOT NULL AND character_name != '' "
            "AND (IFNULL(call_opt_out, 0) = 0 OR user_id = ?)",
            (chat.id, query.from_user.id)
        )
        if users:
            mentions = []
            for u in users:
                if u["username"]:
                    mentions.append(f"@{u['username']}")
                else:
                    mentions.append(f'<a href="tg://user?id={u["user_id"]}">{esc(u["character_name"])}</a>')

            call_text = (
                f"📢 <b>ПОЗЫВНОЙ</b>\n{DIV}\n\n"
                f"Новый герой <b>{esc(name)}</b> вступил в игру! Приветствуем! 🎉\n\n{DIV}\n"
            )

            chunks = [mentions[i:i + 4] for i in range(0, len(mentions), 4)]
            if chunks:
                sent_msg = await bot.send_message(chat.id, call_text + ", ".join(chunks[0]), parse_mode="HTML")
                for chunk in chunks[1:]:
                    await sent_msg.reply(call_text + ", ".join(chunk), parse_mode="HTML")
                    await asyncio.sleep(0.5)
    except Exception as e:
        print(f"Ошибка при авто-созыве: {e}")


# ==================== ДУБЛИКАТЫ ФУНКЦИЙ ИЗ MENU.PY (Для объема и совместимости) ====================

@dp.callback_query(MenuCB.filter(F.action == "menu"))
@inject_user
async def cb_menu(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    if user.get("char_change_paid") == 1:
        return await edit_or_send(query, f"── 〔 🖼 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nТы оплатил смену!\nВыбери регион:",
                                  regions_kb(query.from_user.id), image_url="")

    name = esc(user_display_name(user))
    first_seen = user.get("first_seen") or int(datetime.now(timezone.utc).timestamp())
    days = (int(datetime.now(timezone.utc).timestamp()) - first_seen) // 86400 + 1

    region_display = "Тейват"
    if user.get("character_name"):
        from helpers import get_character_region
        r_key = get_character_region(user["character_name"])
        if r_key and r_key in REGIONS and r_key != "other":
            region_display = REGIONS[r_key].split(" ", 1)[1] if " " in REGIONS[r_key] else REGIONS[r_key]

    rep = user.get("reputation", 0) or 0
    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title: reg_name_for_title = reg_name_for_title.split(" ", 1)[1]
    rep_title = get_reputation_title(rep, reg_name_for_title)

    text = (
        f" ─ [ 🖼 ГЛАВНОЕ МЕНЮ ] ─\n\n"
        f"🍃 <b>{name}</b> · {region_display}\n\n"
        f"📊 Статус: {rep_title}\n\n"
        f"⏳ В Тейвате: <b>{days}</b> дн."
    )
    final_text = format_text(await get_local_setting("text_menu", chat_id, text), user, DIV)

    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    image = await get_section_image("menu", fallback, chat_id)
    await edit_or_send(query, final_text, main_menu_kb(query.from_user.id), image_url=image)


@dp.callback_query(MenuCB.filter(F.action == "profile"))
@inject_user
async def cb_profile(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    if user.get("char_change_paid") == 1:
        return await edit_or_send(query, f"── 〔 🖼 ВЫБОР ПЕРСОНАЖА 〕 ──\n\nТы оплатил смену!\nВыбери регион:",
                                  regions_kb(query.from_user.id), image_url="")

    name = esc(user_display_name(user))
    g = await get_guild(user["guild_id"]) if user["guild_id"] else None
    guild_line = f"🏰 {esc(g['name'])}" if g else "Без гильдии"

    if user["partner_id"]:
        partner_line = f"❤️ {esc(user['partner_name'])}"
    else:
        if user["gender"] == "male":
            partner_line = "❤️ Свободен"
        elif user["gender"] == "female":
            partner_line = "❤️ Свободна"
        else:
            partner_line = "❤️ Свободен(а)"

    resin = await update_resin(query.from_user.id, chat_id)
    rep = user["reputation"] or 0
    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title: reg_name_for_title = reg_name_for_title.split(" ", 1)[1]
    rep_title = get_reputation_title(rep, reg_name_for_title)

    admin_rank_text = ""
    if user.get("admin_rank"):
        ranks = await get_ranks_config()
        r_data = ranks.get(user["admin_rank"])
        if r_data:
            display_rank = r_data.get("profile_text") or r_data.get("name", "")
            admin_rank_text = f"👑 Должность: <b>{display_rank}</b>\n"

    text = (
        f"─ [ 🖼 ПРОФИЛЬ ] ─\n\n"
        f"🍃 {name}\n"
        f"{admin_rank_text}\n"
        f"💰 Баланс: <b>{user['balance']}</b>\n"
        f"💎 Примогемы: <b>{user.get('primogems', 0)}</b>\n\n"
        f"💧 Смола: <b>{resin} / {RESIN_MAX}</b>\n\n"
        f"🎖️ Репутация: <b>{rep_title}</b>\n\n"
        f"{partner_line}\n\n"
        f"{guild_line}"
    )

    fallback = get_character_image(user["character_name"]) if user["character_name"] else None
    image = await get_section_image("profile", fallback, chat_id)
    await edit_or_send(query, text, profile_kb(query.from_user.id), image_url=image)


@dp.callback_query(MenuCB.filter(F.action == "adventurers"))
@inject_user
async def cb_adventurers(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    text = (
        f"─ [ 🏛 ГИЛЬДИЯ ИСКАТЕЛЕЙ ] ─\n\n"
        f"🍃 Добро пожаловать,\n"
        f"<b>{esc(user_display_name(user))}</b>!\n\n"
        f"Выбери направление:"
    )
    image = await get_section_image("adventurers", chat_id=chat_id)
    await edit_or_send(query, text, adventurers_kb(query.from_user.id), image_url=image)


@dp.callback_query(MenuCB.filter(F.action == "reputation"))
@inject_user
async def cb_reputation(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    rep = user["reputation"] or 0
    level, cur, need = get_rep_progress(rep)

    reg_info = find_region_by_character(user.get("character_name"))
    reg_name_for_title = reg_info[1] if reg_info else "Тейват"
    if " " in reg_name_for_title: reg_name_for_title = reg_name_for_title.split(" ", 1)[1]

    title = get_reputation_title(rep, reg_name_for_title)
    pt = "Максимум!" if level >= 10 else f"{'█' * (cur * 10 // 500)}{'░' * (10 - (cur * 10 // 500))} {cur}/500"

    text = (
        f"─ [ 🎖️ РЕПУТАЦИЯ ] ─\n\n"
        f"{title}\n\n"
        f"📊 Уровень: <b>{level} / 10</b>\n\n"
        f"🌟 Очки: <b>{rep}</b>\n\n"
        f"📈 Прогресс: {pt}"
    )
    image = await get_section_image("reputation", chat_id=chat_id)
    await edit_or_send(query, text, reputation_kb(query.from_user.id), image_url=image)


# ==================== СОБЫТИЯ ВХОДА ====================

@dp.chat_member()
async def on_chat_member_update(event: types.ChatMemberUpdated):
    try:
        if event.chat.type not in ("group", "supergroup"):
            return

        affected_user = event.new_chat_member.user
        if affected_user.is_bot:
            return

        old_status = event.old_chat_member.status
        new_status = event.new_chat_member.status

        was_in = old_status in ("member", "administrator", "creator", "restricted")
        is_gone = new_status in ("left", "kicked")
        is_new = old_status in ("left", "kicked") and new_status in ("member", "administrator", "creator")

        if was_in and is_gone:
            user = await get_user(affected_user.id, event.chat.id)
            if user and user["character_name"]:
                old_name = user["character_name"]
                await update_user(affected_user.id, event.chat.id, character_name="", char_change_paid=0,
                                  search_rp_partner="", sub_passed=0)
                await update_application_status(affected_user.id, event.chat.id, "rejected")
                try:
                    await bot.set_chat_member_tag(chat_id=event.chat.id, user_id=affected_user.id, tag="")
                except Exception:
                    pass
                try:
                    await bot.send_message(event.chat.id,
                                           f"🎭 Роль «{esc(old_name)}» освобождена —\nеё владелец покинул группу.",
                                           parse_mode="HTML")
                except Exception:
                    pass
                await update_chat_list(event.chat.id)

        elif is_new:
            user = await get_user(affected_user.id, event.chat.id)
            if user and user["character_name"]:
                await asyncio.sleep(1)
                await update_user_tag(bot, event.chat.id, affected_user.id, user)

            sub_enabled = await get_setting("sub_enabled", "0")
            if sub_enabled == "1":
                if not user or user.get("sub_passed") == 0:
                    await send_sub_message(event, affected_user.id, event.chat.id)
                    return

            app = await get_application(affected_user.id, event.chat.id)
            if app and app['status'] == 'accepted':
                # ДУБЛИРОВАНИЕ АНКЕТЫ В ЧАТ
                app_text = (
                    f"🎉 <b>У нас новенький! Встречайте!</b>\n\n"
                    f"🎭 <b>Роль:</b> Будет выбрана\n\n"
                    f"📖 <b>Опыт:</b> {esc(app['experience'])}\n"
                    f"🌟 <b>О себе:</b> {esc(app['about'])}\n"
                    f"🕒 <b>Часовой пояс:</b> {esc(app['timezone'])}\n"
                    f"⚠️ <b>Триггеры:</b> {esc(app['triggers'])}\n"
                    f"⚡ <b>Активность:</b> {esc(app['activity'])}\n"
                    f"📢 <b>Откуда узнал(а):</b> {esc(app.get('source', 'Не указан'))}"
                )
                await bot.send_message(event.chat.id, app_text, parse_mode="HTML")

                mention = f'<a href="tg://user?id={affected_user.id}">{esc(affected_user.first_name)}</a>'
                await bot.send_message(
                    event.chat.id,
                    f"🎉 {mention}, твоя анкета одобрена!\n\nПожалуйста, выбери регион, откуда твой персонаж:",
                    reply_markup=regions_kb(affected_user.id), parse_mode="HTML"
                )
                await update_application_status(affected_user.id, event.chat.id, 'waiting_char')
            else:
                if not user or not user["character_name"]:
                    mention = f'<a href="tg://user?id={affected_user.id}">{esc(affected_user.first_name)}</a>'
                    await bot.send_message(
                        event.chat.id,
                        f"👋 {mention}, добро пожаловать в Тейват!\n\nВыбери регион, откуда родом твой герой:",
                        reply_markup=regions_kb(affected_user.id), parse_mode="HTML"
                    )
    except Exception as e:
        print(f"ChatMemberUpdate error: {e}")


@dp.message(F.new_chat_members)
async def on_new_chat_members(message: types.Message):
    try:
        sub_enabled = await get_setting("sub_enabled", "0")
        if sub_enabled != "1":
            return

        for user in message.new_chat_members:
            if user.is_bot:
                continue
            db_user = await get_user(user.id, message.chat.id)
            if not db_user or db_user.get("sub_passed") == 0:
                await send_sub_message(message, user.id, message.chat.id)
    except Exception as e:
        print(f"NewChatMembers error: {e}")