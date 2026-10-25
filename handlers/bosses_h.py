import random

from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot_instance import dp
from callbacks import MenuCB, BossCB, GuildCB
from config import OWNER_ID, BOSS_ATTACK_COOLDOWN
from constants import DIV, REP_PER_WORLD_BOSS_KILL, REP_PER_GUILD_BOSS_KILL
from bosses import WORLD_BOSSES, BOSS_DAMAGE_MIN, BOSS_DAMAGE_MAX
from db import (
    get_user, update_user, get_world_boss, damage_world_boss,
    get_guild_boss, damage_guild_boss, get_guild, update_guild,
)
from helpers import hp_bar, esc, edit_or_send, _gain_rep, _now_ts
from state import _boss_cooldown


@dp.callback_query(MenuCB.filter(F.action == "world_boss"))
async def cb_world_boss(query: types.CallbackQuery, callback_data: MenuCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    wb = await get_world_boss()
    if not wb or not wb["boss_name"]:
        await query.answer("🐉 Босс пока не появился. Ждём субботу 12:00!", show_alert=True)
        return
    boss = WORLD_BOSSES.get(wb["boss_name"], {})

    # ПАТЧ 3: если босс уже повержен — показываем экран «повержен», без кнопки атаки
    if wb["current_hp"] <= 0:
        bar = hp_bar(0, wb["max_hp"])
        text = (f"🐉 МИРОВОЙ БОСС\n{DIV}\n\n"
                f"👹 {wb['boss_name']}\n\n"
                f"❤️ HP 0 / {wb['max_hp']:,}\n{bar}\n\n"
                f"{DIV}\n\n"
                f"💀 Босс повержен!\n\n"
                f"⏰ Следующий — в субботу в 12:00")
        b = InlineKeyboardBuilder()
        b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=query.from_user.id))
        b.adjust(1)
        img = boss.get("image") or ""
        await edit_or_send(query, text, b.as_markup(), image_url=img)
        return

    bar = hp_bar(wb["current_hp"], wb["max_hp"])
    text = (f"🐉 МИРОВОЙ БОСС\n{DIV}\n\n"
            f"👹 {wb['boss_name']}\n\n"
            f"❤️ HP {wb['current_hp']:,} / {wb['max_hp']:,}\n{bar}\n\n"
            f"{DIV}\n\n"
            f"⚔️ Урон: {BOSS_DAMAGE_MIN} – {BOSS_DAMAGE_MAX}\n"
            f"💰 Награда: {boss.get('reward_min', 100)} – {boss.get('reward_max', 300)}\n"
            f"🎖️ За добивание: +{REP_PER_WORLD_BOSS_KILL}\n\n"
            f"{DIV}\n\n"
            f"⏰ Ротация — каждую\nсубботу в 12:00")
    b = InlineKeyboardBuilder()
    b.button(text="⚔ Атаковать", callback_data=BossCB(action="attack", owner_id=query.from_user.id))
    b.button(text="‹ Назад", callback_data=MenuCB(action="adventurers", owner_id=query.from_user.id))
    b.adjust(1)
    img = boss.get("image") or ""
    await edit_or_send(query, text, b.as_markup(), image_url=img)


@dp.callback_query(BossCB.filter(F.action == "attack"))
async def cb_boss_attack(query: types.CallbackQuery, callback_data: BossCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    wb = await get_world_boss()
    if not wb or wb["current_hp"] <= 0:
        await query.answer("🐉 Босс уже повержен!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user or not user["character_name"]:
        await query.answer("❌ Сначала выбери персонажа!", show_alert=True)
        return
    if query.from_user.id != OWNER_ID:
        chat_id = 0
        try:
            chat_id = query.message.chat.id if query.message else 0
        except Exception:
            pass
        key = ("world", query.from_user.id, chat_id)
        now_ts = _now_ts()
        last = _boss_cooldown.get(key, 0)
        if now_ts - last < BOSS_ATTACK_COOLDOWN:
            await query.answer(f"⏳ Атака раз в {BOSS_ATTACK_COOLDOWN} сек.", show_alert=False)
            return
        _boss_cooldown[key] = now_ts
    dmg = random.randint(BOSS_DAMAGE_MIN, BOSS_DAMAGE_MAX)
    new_hp = await damage_world_boss(dmg)
    if new_hp == 0:
        boss = WORLD_BOSSES.get(wb["boss_name"], {})
        reward = random.randint(boss.get("reward_min", 100), boss.get("reward_max", 300))
        await update_user(query.from_user.id, balance=user["balance"] + reward)
        await _gain_rep(query.from_user.id, query.message.chat.id, REP_PER_WORLD_BOSS_KILL, query.from_user.first_name)
        await query.answer(
            f"⚔️ {dmg} урона! Босс повержен! +{reward} монет, +{REP_PER_WORLD_BOSS_KILL} репутации",
            show_alert=True)
    else:
        await query.answer(f"⚔️ Ты нанёс {dmg} урона!", show_alert=False)
    await cb_world_boss(query, MenuCB(action="world_boss", owner_id=query.from_user.id))


@dp.callback_query(GuildCB.filter(F.action == "boss"))
async def cb_guild_boss(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["guild_id"]:
        await query.answer("❌ Ты не в гильдии.", show_alert=True)
        return
    gb = await get_guild_boss()
    if not gb or not gb["boss_name"]:
        await query.answer("🐉 Босс пока не появился.", show_alert=True)
        return
    boss = WORLD_BOSSES.get(gb["boss_name"], {})

    # ПАТЧ 3: если босс уже повержен — показываем экран «повержен»
    if gb["current_hp"] <= 0:
        bar = hp_bar(0, gb["max_hp"])
        text = (f"🐉 БОСС ГИЛЬДИИ\n{DIV}\n\n"
                f"👹 {gb['boss_name']}\n\n"
                f"❤️ HP 0 / {gb['max_hp']:,}\n{bar}\n\n"
                f"{DIV}\n\n"
                f"💀 Босс повержен!\n\n"
                f"⏰ Следующий — в субботу в 12:00")
        b = InlineKeyboardBuilder()
        b.button(text="‹ Назад", callback_data=MenuCB(action="guild", owner_id=query.from_user.id))
        b.adjust(1)
        img = boss.get("image") or ""
        await edit_or_send(query, text, b.as_markup(), image_url=img)
        return

    bar = hp_bar(gb["current_hp"], gb["max_hp"])
    text = (f"🐉 БОСС ГИЛЬДИИ\n{DIV}\n\n"
            f"👹 {gb['boss_name']}\n\n"
            f"❤️ HP {gb['current_hp']:,} / {gb['max_hp']:,}\n{bar}\n\n"
            f"{DIV}\n\n"
            f"⚔️ Награда в казну:\n{boss.get('reward_min', 100)} – {boss.get('reward_max', 300)} монет\n"
            f"🎖️ За добивание: +{REP_PER_GUILD_BOSS_KILL}\n\n"
            f"Только члены гильдии!")
    b = InlineKeyboardBuilder()
    b.button(text="⚔ Атаковать", callback_data=GuildCB(action="gboss_attack", owner_id=query.from_user.id))
    b.button(text="‹ Назад", callback_data=MenuCB(action="guild", owner_id=query.from_user.id))
    b.adjust(1)
    img = boss.get("image") or ""
    await edit_or_send(query, text, b.as_markup(), image_url=img)


@dp.callback_query(GuildCB.filter(F.action == "gboss_attack"))
async def cb_guild_boss_attack(query: types.CallbackQuery, callback_data: GuildCB):
    if query.from_user.id != callback_data.owner_id:
        await query.answer("⚠️ Чужое меню!", show_alert=True)
        return
    user = await get_user(query.from_user.id)
    if not user["guild_id"]:
        await query.answer("❌ Ты не в гильдии.", show_alert=True)
        return
    gb = await get_guild_boss()
    if not gb or gb["current_hp"] <= 0:
        await query.answer("🐉 Уже повержен!", show_alert=True)
        return
    if query.from_user.id != OWNER_ID:
        chat_id = 0
        try:
            chat_id = query.message.chat.id if query.message else 0
        except Exception:
            pass
        key = ("guild", query.from_user.id, chat_id)
        now_ts = _now_ts()
        last = _boss_cooldown.get(key, 0)
        if now_ts - last < BOSS_ATTACK_COOLDOWN:
            await query.answer(f"⏳ Атака раз в {BOSS_ATTACK_COOLDOWN} сек.", show_alert=False)
            return
        _boss_cooldown[key] = now_ts
    dmg = random.randint(BOSS_DAMAGE_MIN, BOSS_DAMAGE_MAX)
    new_hp = await damage_guild_boss(dmg)
    if new_hp == 0:
        boss = WORLD_BOSSES.get(gb["boss_name"], {})
        reward = random.randint(boss.get("reward_min", 100), boss.get("reward_max", 300))
        g = await get_guild(user["guild_id"])
        if g:
            await update_guild(g["guild_id"], treasury=g["treasury"] + reward)
        await _gain_rep(query.from_user.id, query.message.chat.id, REP_PER_GUILD_BOSS_KILL, query.from_user.first_name)
        await query.answer(
            f"🎉 Босс повержен! +{reward} в казну, +{REP_PER_GUILD_BOSS_KILL} репутации",
            show_alert=True)
    else:
        await query.answer(f"⚔️ {dmg} урона!", show_alert=False)
    # ПАТЧ 2a: не мутируем callback_data — создаём новый
    await cb_guild_boss(query, GuildCB(action="boss", owner_id=query.from_user.id))