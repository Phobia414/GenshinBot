import random
from datetime import datetime, timezone

from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import bot, dp
from callbacks import MenuCB, FunCB, CasinoCB, QuizCB, DuelCB, CookCB
from config import OWNER_ID, PROPOSE_COOLDOWN
from constants import (
    DIV, QUIZ_QUESTIONS, QUIZ_COOLDOWN, QUIZ_REWARD,
)
from db import (
    get_user, update_user, get_ingredients, use_ingredients,
    set_food_buff, get_food_buff, RECIPES, INGREDIENTS,
)
from helpers import (
    esc, edit_or_send, _ensure_user, extract_target, resolve_user_id, _now_ts,
)
from keyboards import (
    fun_menu_kb, casino_kb, cook_kb, back_kb,
)
from state import _duel_cooldown


@dp.callback_query(MenuCB.filter(F.action == "fun"))
async def cb_fun(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    from helpers import user_display_name
    name = esc(user_display_name(user))
    text = f"🎲 РАЗВЛЕЧЕНИЯ\n{DIV}\n\n{name}, чем займёмся?\n\n{DIV}\n\n🎰 Казино\n🧠 Викторина\n⚔ Дуэль\n🍳 Кулинария"
    await edit_or_send(query, text, fun_menu_kb(query.from_user.id))


@dp.callback_query(FunCB.filter(F.action == "casino"))
async def cb_casino(query: types.CallbackQuery, callback_data: FunCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    text = f"🎰 КАЗИНО\n{DIV}\n\n💰 Баланс: {user['balance']}\n\n{DIV}\n\n🎡 Рулетка — 50% x2\n🎰 Слоты — 25% x3\n🎲 Кости — 45% x2"
    await edit_or_send(query, text, casino_kb(query.from_user.id))


@dp.callback_query(CasinoCB.filter())
async def cb_casino_bet(query: types.CallbackQuery, callback_data: CasinoCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if user["balance"] < callback_data.bet:
        await query.answer(f"❌ Нужно {callback_data.bet}", show_alert=True)
        return
    # БАГ ФИКС: было 0.55 — это давало игроку +10% EV. Стало 0.45 — минус 10% игроку.
    if callback_data.game == "roulette":
        win, mult = random.random() < 0.50, 2   # EV = 1.00
    elif callback_data.game == "slots":
        win, mult = random.random() < 0.25, 3   # EV = 0.75
    else:  # dice
        win, mult = random.random() < 0.45, 2   # EV = 0.90
    if win:
        profit = callback_data.bet * (mult - 1)
        nb = user["balance"] + profit
        res_line = f"🎉 Победа! +{profit} (x{mult})"
    else:
        nb = user["balance"] - callback_data.bet
        res_line = f"💔 Проигрыш. -{callback_data.bet}"
    await update_user(query.from_user.id, balance=nb)
    b = InlineKeyboardBuilder()
    b.button(text="🎰 Ещё ›", callback_data=FunCB(action="casino", owner_id=query.from_user.id))
    b.button(text="‹ Назад", callback_data=MenuCB(action="fun", owner_id=query.from_user.id))
    b.adjust(1)
    text = f"🎰 РЕЗУЛЬТАТ\n{DIV}\n\n{res_line}\n\n💰 Баланс: {nb}"
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(FunCB.filter(F.action == "quiz"))
async def cb_quiz_start(query: types.CallbackQuery, callback_data: FunCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    now = int(datetime.now(timezone.utc).timestamp())
    if now - user["last_quiz"] < QUIZ_COOLDOWN:
        await query.answer(f"⏳ Подожди {QUIZ_COOLDOWN - (now - user['last_quiz'])} сек", show_alert=True)
        return
    q = random.choice(QUIZ_QUESTIONS)
    b = InlineKeyboardBuilder()
    for i, opt in enumerate(q["options"]):
        b.button(text=opt, callback_data=QuizCB(answer=i, correct=q["correct"], owner_id=query.from_user.id))
    b.adjust(1)
    text = f"🧠 ВИКТОРИНА\n{DIV}\n\n{q['q']}\n\n{DIV}\n\n🎁 Награда: {QUIZ_REWARD} монет"
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(QuizCB.filter())
async def cb_quiz_answer(query: types.CallbackQuery, callback_data: QuizCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    await update_user(query.from_user.id, last_quiz=int(datetime.now(timezone.utc).timestamp()))
    if callback_data.answer == callback_data.correct:
        await update_user(query.from_user.id, balance=user["balance"] + QUIZ_REWARD)
        res, nb = f"🌟 Верно! +{QUIZ_REWARD}", user["balance"] + QUIZ_REWARD
    else:
        res, nb = "🤔 Неправильно.", user["balance"]
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="fun", owner_id=query.from_user.id))
    text = f"🧠 РЕЗУЛЬТАТ\n{DIV}\n\n{res}\n\n💰 Баланс: {nb}"
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(FunCB.filter(F.action == "duel_help"))
async def cb_duel_help(query: types.CallbackQuery, callback_data: FunCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.button(text="‹ Назад", callback_data=MenuCB(action="fun", owner_id=query.from_user.id))
    text = f"⚔️ ДУЭЛЬ\n{DIV}\n\nОтветь на сообщение игрока\nи напиши:\n\n/duel Сумма\n\nили укажи его @username"
    await edit_or_send(query, text, b.as_markup())


@dp.message(Command("duel"))
async def cmd_duel(message: types.Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Дуэль работает только в группе.")
        return
    target_ref, display = extract_target(message)
    if target_ref is None:
        await message.answer("⚔️ Ответь на сообщение игрока и напиши /duel Сумма\n(или /duel @user Сумма)")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[-1].isdigit():
        await message.answer("Используй: /duel Сумма (ответом) или /duel @user Сумма")
        return
    bet = int(parts[-1])
    if bet <= 0:
        await message.answer("❌ Сумма > 0")
        return
    if isinstance(target_ref, str):
        target_id = await resolve_user_id(target_ref)
        if not target_id:
            await message.answer(f"❌ Не нашёл @{target_ref}. Пусть игрок напишет в чат с ботом.")
            return
        display = target_ref
    else:
        target_id = target_ref
    if target_id == message.from_user.id:
        await message.answer("❌ Себя нельзя.")
        return
    me = await _ensure_user(message.from_user.id)
    other = await _ensure_user(target_id)
    try:
        tg_target = await bot.get_chat(target_id)
        if getattr(tg_target, "is_bot", False):
            await message.answer("❌ Бота нельзя.")
            return
    except Exception:
        pass
    if not me["character_name"]:
        await message.answer("❌ Сначала выбери персонажа: /start")
        return
    if not other["character_name"]:
        await message.answer(f"❌ {esc(display)} ещё не выбрал персонажа.")
        return
    if me["balance"] < bet:
        await message.answer("❌ У тебя мало монет")
        return
    if other["balance"] < bet:
        await message.answer(f"❌ У {esc(display)} мало монет")
        return
    if message.from_user.id != OWNER_ID:
        key = ("duel", message.from_user.id, target_id, message.chat.id)
        now_ts = _now_ts()
        last = _duel_cooldown.get(key, 0)
        if now_ts - last < PROPOSE_COOLDOWN:
            left = int(PROPOSE_COOLDOWN - (now_ts - last))
            await message.answer(f"⏳ Ты уже вызывал(а) этого игрока. Подожди {left} сек.")
            return
        _duel_cooldown[key] = now_ts
    b = InlineKeyboardBuilder()
    b.button(text="✅ Принять", callback_data=DuelCB(action="accept",
                                                     challenger_id=message.from_user.id,
                                                     target_id=target_id, bet=bet))
    b.button(text="❌ Отклонить", callback_data=DuelCB(action="decline",
                                                       challenger_id=message.from_user.id,
                                                       target_id=target_id, bet=bet))
    b.adjust(2)
    mention = f'<a href="tg://user?id={target_id}">{esc(display)}</a>'
    ch = f'<a href="tg://user?id={message.from_user.id}">{esc(message.from_user.first_name)}</a>'
    await message.answer(
        f"⚔️ ВЫЗОВ НА ДУЭЛЬ\n{DIV}\n\n{mention}, {ch}\nвызывает тебя на дуэль!\n\n💰 Ставка: {bet}",
        reply_markup=b.as_markup(), parse_mode="HTML")


@dp.callback_query(DuelCB.filter())
async def cb_duel(query: types.CallbackQuery, callback_data: DuelCB):
    if query.from_user.id != callback_data.target_id:
        await query.answer("❌ Не для тебя!", show_alert=True)
        return
    if callback_data.action == "decline":
        text = f"🕊️ ОТКЛОНЕНО\n{DIV}\n\nМирное решение!"
        await edit_or_send(query, text, back_kb(query.from_user.id))
        return
    ch = await get_user(callback_data.challenger_id)
    tg = await get_user(callback_data.target_id)
    if ch["balance"] < callback_data.bet or tg["balance"] < callback_data.bet:
        await query.answer("❌ Мало монет.", show_alert=True)
        return
    r1, r2 = random.randint(1, 100), random.randint(1, 100)
    while r1 == r2:
        r2 = random.randint(1, 100)
    if r1 > r2:
        await update_user(callback_data.challenger_id, balance=ch["balance"] + callback_data.bet)
        await update_user(callback_data.target_id, balance=tg["balance"] - callback_data.bet)
    else:
        await update_user(callback_data.target_id, balance=tg["balance"] + callback_data.bet)
        await update_user(callback_data.challenger_id, balance=ch["balance"] - callback_data.bet)
    text = f"⚔️ ДУЭЛЬ ЗАВЕРШЕНА\n{DIV}\n\n🎲 {r1} vs {r2}\n\n🏆 Победитель забирает {callback_data.bet}!"
    await edit_or_send(query, text, back_kb(query.from_user.id))


@dp.callback_query(MenuCB.filter(F.action == "cook"))
async def cb_cook(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    ing = await get_ingredients(query.from_user.id)
    fn, fv = await get_food_buff(query.from_user.id)
    lines = []
    for k, d in INGREDIENTS.items():
        lines.append(f"{d['emoji']} {d['name'][2:]}: {ing.get(k, 0)}")
    bt = f"\n\n{DIV}\n\n🍳 Бафф: {fn} (+{fv}%)" if fn else ""
    text = (f"🍳 КУЛИНАРИЯ\n{DIV}\n\n📦 ИНГРЕДИЕНТЫ\n\n"
            + "\n".join(lines) + f"{bt}\n\n{DIV}\n\n🍽️ Выбери блюдо:\n(бафф на 1 час)")
    await edit_or_send(query, text, cook_kb(query.from_user.id, ing))


@dp.callback_query(CookCB.filter())
async def cb_cook_recipe(query: types.CallbackQuery, callback_data: CookCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    if callback_data.recipe not in RECIPES:
        await query.answer("❌ Не найдено", show_alert=True)
        return
    r = RECIPES[callback_data.recipe]
    ing = await get_ingredients(query.from_user.id)
    missing = [f"{INGREDIENTS[k]['emoji']}: нужно {v}, есть {ing.get(k, 0)}"
               for k, v in r["need"].items() if ing.get(k, 0) < v]
    if missing:
        await query.answer("❌ Не хватает:\n" + "\n".join(missing), show_alert=True)
        return
    await use_ingredients(query.from_user.id, r["need"])
    await set_food_buff(query.from_user.id, r["name"], r["buff_value"], r["duration"])
    ing = await get_ingredients(query.from_user.id)
    text = f"😋 ГОТОВО!\n{DIV}\n\n{r['name']}\n\n🍳 Бафф +{r['buff_value']}%\n⏰ Длительность: 1 час"
    await edit_or_send(query, text, cook_kb(query.from_user.id, ing))