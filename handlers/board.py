from datetime import datetime, timezone

from aiogram import types, F

from bot_instance import dp
from callbacks import MenuCB, TaskCB
from config import BOARD_COOLDOWN
from constants import DIV, TASKS, REP_PER_BOARD_TASK
from db import get_user, update_user
from helpers import esc, user_display_name, generate_tasks, edit_or_send
from keyboards import board_kb


@dp.callback_query(MenuCB.filter(F.action == "board"))
async def cb_board(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    now = int(datetime.now(timezone.utc).timestamp())
    if now - user["last_board"] >= BOARD_COOLDOWN:
        tasks = generate_tasks()
        await update_user(query.from_user.id, last_board=now,
                          board_msgs=0, board_sts=0, board_reps=0,
                          board_tasks=";".join(tasks), board_claimed="",
                          board_notified="", board_accepted="", board_active="")
        user = await get_user(query.from_user.id)
    else:
        tasks = user["board_tasks"].split(";") if user["board_tasks"] else generate_tasks()
        if not user["board_tasks"]:
            await update_user(query.from_user.id, board_tasks=";".join(tasks))
    accepted = user["board_accepted"].split(";") if user["board_accepted"] else []
    claimed = user["board_claimed"].split(";") if user["board_claimed"] else []
    name = esc(user_display_name(user))
    text = (f"📋 ДОСКА ЗАНЯТОСТИ\n{DIV}\n\nПривет, {name}!\n\n"
            f"Нажми «📌 Принять» на задании,\nпотом выполняй его.\n"
            f"Монеты и репутация зачислятся\nавтоматически ✨\n\n"
            f"{DIV}\n\n🎖️ Награда за задание: +{REP_PER_BOARD_TASK} репутации")
    await edit_or_send(query, text, board_kb(query.from_user.id, user, tasks, accepted, claimed))


@dp.callback_query(TaskCB.filter())
async def cb_task(query: types.CallbackQuery, callback_data: TaskCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    t_id = callback_data.task_id
    if t_id not in TASKS:
        await query.answer("❌ Задание не найдено", show_alert=True)
        return
    claimed = user["board_claimed"].split(";") if user["board_claimed"] else []
    accepted = user["board_accepted"].split(";") if user["board_accepted"] else []
    if t_id in claimed:
        await query.answer("✅ Награда уже получена!", show_alert=True)
        return
    if t_id in accepted:
        t = TASKS[t_id]
        from helpers import get_progress
        progress = get_progress(user, t["cat"])
        await query.answer(f"⏳ Прогресс: {progress}/{t['need']}", show_alert=True)
        return
    accepted.append(t_id)
    await update_user(query.from_user.id, board_accepted=";".join(accepted))
    await query.answer("✅ Задание принято!", show_alert=True)
    user = await get_user(query.from_user.id)
    tasks = user["board_tasks"].split(";") if user["board_tasks"] else []
    text = f"📋 ДОСКА ЗАНЯТОСТИ\n{DIV}\n\nЗадание принято!"
    await edit_or_send(query, text, board_kb(query.from_user.id, user, tasks, accepted, claimed))