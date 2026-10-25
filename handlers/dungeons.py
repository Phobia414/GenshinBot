import random
from datetime import datetime, timezone

from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp
from callbacks import MenuCB, DungeonCB, ArtCB, ArtifactCB
from constants import (
    DIV, DUNGEONS, DUNGEON_IMAGES, SELL_PRICE, REP_PER_DUNGEON,
)
from db import (
    get_user, update_user, get_total_bonuses, get_food_buff,
    update_resin, RESIN_MAX, RESIN_REGEN_SECONDS, RESIN_COST_DUNGEON,
    add_artifact, get_artifact, get_user_artifacts, delete_artifact,
)
from helpers import (
    esc, user_display_name, roll_artifact, edit_or_send,
    get_reputation_bonuses, format_resin_time, _gain_rep,
)
from keyboards import (
    dungeons_kb, artifacts_menu_kb, inventory_kb, artifact_view_kb,
)


@dp.callback_query(MenuCB.filter(F.action == "dungeons"))
async def cb_dungeons(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    # БАГ ФИКС: сначала update_resin, потом get_user — чтобы last_resin_update был свежим
    resin = await update_resin(query.from_user.id)
    user = await get_user(query.from_user.id)
    if resin >= RESIN_MAX:
        tt = "💧 Смола полная!"
    else:
        now = int(datetime.now(timezone.utc).timestamp())
        last = user["last_resin_update"] or now
        tt = f"⏱️ След. смола: {format_resin_time(RESIN_REGEN_SECONDS - (now - last) % RESIN_REGEN_SECONDS)}"
    text = (f"⚔️ ПОДЗЕМЕЛЬЯ\n{DIV}\n\n"
            f"💧 Смола: {resin} / {RESIN_MAX}\n{tt}\n\n"
            f"{DIV}\n\n"
            f"💰 Баланс: {user['balance']}\n"
            f"💧 Вход: {RESIN_COST_DUNGEON} смолы\n"
            f"🎖️ За заход: +{REP_PER_DUNGEON} репутации\n"
            f"🎁 Награды: монеты + артефакты\n\n"
            f"{DIV}\n\n"
            f"Куда отправимся?")
    await edit_or_send(query, text, dungeons_kb(query.from_user.id))


@dp.callback_query(DungeonCB.filter())
async def cb_dungeon_enter(query: types.CallbackQuery, callback_data: DungeonCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    resin = await update_resin(query.from_user.id)
    if resin < RESIN_COST_DUNGEON:
        await query.answer(f"❌ Нужно {RESIN_COST_DUNGEON} смолы, у тебя {resin}", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if callback_data.dungeon not in DUNGEONS:
        await query.answer("❌ Не найдено", show_alert=True)
        return
    d = DUNGEONS[callback_data.dungeon]
    set_name = d.get("artifact_set", "")
    new_resin = resin - RESIN_COST_DUNGEON
    now = int(datetime.now(timezone.utc).timestamp())
    last = user["last_resin_update"] or now
    if resin >= RESIN_MAX:
        last = now
    await update_user(query.from_user.id, resin=new_resin, last_resin_update=last)
    earn_b, drop_b = await get_total_bonuses(query.from_user.id)
    rep_earn, rep_drop, _ = get_reputation_bonuses(user["reputation"])
    _, food_value = await get_food_buff(query.from_user.id)
    total_earn = earn_b + rep_earn + food_value
    total_drop = drop_b + rep_drop
    reward = random.randint(d["reward_min"], d["reward_max"])
    if total_earn:
        reward = int(reward * (100 + total_earn) / 100)
    artifacts_text = ""
    for _ in range(2):
        slot, rarity, btype, bvalue, name = roll_artifact(total_drop, set_name)
        art_id = await add_artifact(query.from_user.id, slot, rarity, btype, bvalue, name)
        stars = "⭐" * rarity
        user = await get_user(query.from_user.id)
        field = f"equip_{slot}"
        cur = user.get(field, 0) or 0
        if not cur:
            await update_user(query.from_user.id, **{field: art_id})
        else:
            ca = await get_artifact(cur)
            if ca and rarity > ca["rarity"]:
                await update_user(query.from_user.id, **{field: art_id})
        artifacts_text += f"\n{stars} {name}"
    await update_user(query.from_user.id, balance=user["balance"] + reward)
    await _gain_rep(query.from_user.id, query.message.chat.id, REP_PER_DUNGEON, query.from_user.first_name)
    b = InlineKeyboardBuilder()
    b.button(text="⚔ Ещё заход ›", callback_data=MenuCB(action="dungeons", owner_id=query.from_user.id))
    b.button(text="🎒 Инвентарь ›", callback_data=ArtCB(action="inventory", owner_id=query.from_user.id))
    b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=query.from_user.id))
    b.adjust(1)
    name = esc(user_display_name(user))
    fl = f"\n🍳 Бафф еды: +{food_value}%" if food_value else ""
    text = (f"⚔️ {d['name'].upper()}\n{DIV}\n\n"
            f"✨ Отличная работа, {name}!\n\n"
            f"💰 Монет: {reward}\n"
            f"💧 Смола: {new_resin} / {RESIN_MAX}\n"
            f"🎖️ Репутация: +{REP_PER_DUNGEON}{fl}\n\n"
            f"{DIV}\n\n"
            f"🎁 ДОБЫЧА\n({set_name}){artifacts_text}")
    img = DUNGEON_IMAGES.get(callback_data.dungeon) or ""
    await edit_or_send(query, text, b.as_markup(), image_url=img)


@dp.callback_query(MenuCB.filter(F.action == "artifacts"))
async def cb_artifacts(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    arts = await get_user_artifacts(query.from_user.id)
    earn_b, drop_b = await get_total_bonuses(query.from_user.id)
    rep_earn, rep_drop, _ = get_reputation_bonuses(user["reputation"])
    _, fv = await get_food_buff(query.from_user.id)
    total_earn = earn_b + rep_earn + fv
    total_drop = drop_b + rep_drop
    text = (f"🎒 АРТЕФАКТЫ\n{DIV}\n\n"
            f"💰 Баланс: {user['balance']}\n"
            f"🎒 В инвентаре: {len(arts)} шт.\n\n"
            f"{DIV}\n\n"
            f"📊 БОНУСЫ\n\n"
            f"⚡ К заработку: +{total_earn}%\n"
            f"💎 К дропу 5★: +{total_drop}%\n\n"
            f"{DIV}\n\n"
            f"Артефакты падают из подземелий.")
    await edit_or_send(query, text, artifacts_menu_kb(query.from_user.id, bool(arts)))


@dp.callback_query(ArtCB.filter(F.action == "inventory"))
async def cb_artifacts_inv(query: types.CallbackQuery, callback_data: ArtCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    arts = await get_user_artifacts(query.from_user.id)
    if not arts:
        await query.answer("❌ Инвентарь пуст.", show_alert=True)
        return
    text = f"🎒 ИНВЕНТАРЬ ({len(arts)} шт.)\n{DIV}"
    await edit_or_send(query, text, inventory_kb(query.from_user.id, arts))


@dp.callback_query(ArtifactCB.filter(F.action == "view"))
async def cb_art_view(query: types.CallbackQuery, callback_data: ArtifactCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    art = await get_artifact(callback_data.art_id)
    if not art or art["user_id"] != query.from_user.id:
        await query.answer("❌ Не найден", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    eq = user.get(f"equip_{art['slot']}", 0) == art["artifact_id"]
    bn = "заработку" if art["bonus_type"] == "earn" else "дропу 5★"
    stars = "⭐" * art["rarity"]
    eq_line = "\n✅ Экипирован" if eq else ""
    text = (f"🎒 {art['name']}\n{DIV}\n\n{stars}\n\n"
            f"💎 Бонус: +{art['bonus_value']}% к {bn}\n"
            f"💰 Цена: {SELL_PRICE[art['rarity']]} монет{eq_line}")
    await edit_or_send(query, text, artifact_view_kb(query.from_user.id, art["artifact_id"], eq))


@dp.callback_query(ArtifactCB.filter(F.action == "equip"))
async def cb_art_equip(query: types.CallbackQuery, callback_data: ArtifactCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    art = await get_artifact(callback_data.art_id)
    if not art or art["user_id"] != query.from_user.id:
        await query.answer("❌ Не найден", show_alert=True)
        return
    await update_user(query.from_user.id, **{f"equip_{art['slot']}": art["artifact_id"]})
    await query.answer("✅ Экипировано!", show_alert=True)
    await cb_art_view(query, ArtifactCB(action="view", art_id=art["artifact_id"], owner_id=query.from_user.id))


@dp.callback_query(ArtifactCB.filter(F.action == "unequip"))
async def cb_art_unequip(query: types.CallbackQuery, callback_data: ArtifactCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    art = await get_artifact(callback_data.art_id)
    if not art or art["user_id"] != query.from_user.id:
        await query.answer("❌ Не найден", show_alert=True)
        return
    await update_user(query.from_user.id, **{f"equip_{art['slot']}": 0})
    await query.answer("✅ Снято", show_alert=True)
    await cb_art_view(query, ArtifactCB(action="view", art_id=art["artifact_id"], owner_id=query.from_user.id))


@dp.callback_query(ArtifactCB.filter(F.action == "sell"))
async def cb_art_sell(query: types.CallbackQuery, callback_data: ArtifactCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    art = await get_artifact(callback_data.art_id)
    if not art or art["user_id"] != query.from_user.id:
        await query.answer("❌ Не найден", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    field = f"equip_{art['slot']}"
    was_equipped = user.get(field, 0) == art["artifact_id"]
    price = SELL_PRICE[art["rarity"]]
    await update_user(query.from_user.id, balance=user["balance"] + price)
    await delete_artifact(art["artifact_id"])
    await query.answer(f"💰 Продано за {price}", show_alert=True)

    if was_equipped:
        arts_left = await get_user_artifacts(query.from_user.id)
        same_slot = [a for a in arts_left if a["slot"] == art["slot"]]
        if same_slot:
            best = max(same_slot, key=lambda a: a["rarity"])
            await update_user(query.from_user.id, **{field: best["artifact_id"]})
        else:
            await update_user(query.from_user.id, **{field: 0})

    arts = await get_user_artifacts(query.from_user.id)
    if arts:
        text = f"🎒 ИНВЕНТАРЬ ({len(arts)} шт.)\n{DIV}"
        await edit_or_send(query, text, inventory_kb(query.from_user.id, arts))
    else:
        b = InlineKeyboardBuilder()
        b.button(text="‹ К артефактам", callback_data=MenuCB(action="artifacts", owner_id=query.from_user.id))
        text = f"🎒 ИНВЕНТАРЬ\n{DIV}\n\nПусто."
        await edit_or_send(query, text, b.as_markup())