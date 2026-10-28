import random
import asyncio
from aiogram import types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot_instance import bot, dp
from callbacks import MenuCB
from db import get_user, update_user, update_primogems, get_gacha_gif, add_gacha_item, get_gacha_inventory
from gacha_data import POOL_3_STAR, POOL_4_STAR, POOL_5_STAR
from helpers import edit_or_send, inject_user
import state

COST_1 = 160
COST_10 = 1600

BANNERS = {
    "event_char": {"name": "Ивентовый баннер", "icon": "🎭", "pity_max": 90, "desc": "50/50 на ивентового 5★"},
    "standard": {"name": "Стандартный баннер", "icon": "💠", "pity_max": 90, "desc": "Только стандартные 5★"},
    "event_weapon": {"name": "Оружейный баннер", "icon": "⚔️", "pity_max": 80, "desc": "75/25 на ивентовое оружие 5★"}
}


def get_pull_result(pity4, pity5, guaranteed, lost_50_50, banner):
    chance_5 = 0.006
    pity_max = BANNERS[banner]["pity_max"]
    if banner == "event_weapon":
        if pity5 >= 62: chance_5 += (pity5 - 61) * 0.07
    else:
        if pity5 >= 73: chance_5 += (pity5 - 72) * 0.06

    if pity5 >= (pity_max - 1) or random.random() < chance_5:
        pity5 = 0
        pity4 += 1
        if banner == "event_char":
            if guaranteed == 1 or lost_50_50 >= 3:
                event_pool = [i for i in POOL_5_STAR if i["is_event"] and i["type"] == "char"]
                item = random.choice(event_pool)
                guaranteed = 0
                lost_50_50 = 0
                is_pink = True
            else:
                if random.random() < 0.5:
                    event_pool = [i for i in POOL_5_STAR if i["is_event"] and i["type"] == "char"]
                    item = random.choice(event_pool)
                    guaranteed = 0
                    lost_50_50 = 0
                    is_pink = False
                else:
                    standard_pool = [i for i in POOL_5_STAR if not i["is_event"]]
                    item = random.choice(standard_pool)
                    guaranteed = 1
                    lost_50_50 += 1
                    is_pink = False
        elif banner == "standard":
            standard_pool = [i for i in POOL_5_STAR if not i["is_event"]]
            item = random.choice(standard_pool)
            is_pink = False
        elif banner == "event_weapon":
            if guaranteed == 1 or lost_50_50 >= 2:
                event_pool = [i for i in POOL_5_STAR if i["is_event"] and i["type"] == "weapon"]
                item = random.choice(event_pool)
                guaranteed = 0
                lost_50_50 = 0
                is_pink = True
            else:
                if random.random() < 0.75:
                    event_pool = [i for i in POOL_5_STAR if i["is_event"] and i["type"] == "weapon"]
                    item = random.choice(event_pool)
                    guaranteed = 0
                    lost_50_50 = 0
                    is_pink = False
                else:
                    standard_pool = [i for i in POOL_5_STAR if not i["is_event"] and i["type"] == "weapon"]
                    item = random.choice(standard_pool)
                    guaranteed = 1
                    lost_50_50 += 1
                    is_pink = False
        return 5, item, pity4, pity5, guaranteed, lost_50_50, is_pink

    if pity4 >= 9 or random.random() < 0.051:
        if banner == "event_weapon":
            pool_4 = [i for i in POOL_4_STAR if i["type"] == "weapon"]
        else:
            pool_4 = POOL_4_STAR
        item = random.choice(pool_4)
        pity4 = 0
        pity5 += 1
        return 4, item, pity4, pity5, guaranteed, lost_50_50, False

    item = random.choice(POOL_3_STAR)
    pity4 += 1
    pity5 += 1
    return 3, item, pity4, pity5, guaranteed, lost_50_50, False


async def render_gacha_menu(message_or_query, user_id, chat_id, is_edit=True):
    user = await get_user(user_id, chat_id)
    if not user: return
    banner_key = user.get("gacha_banner", "event_char")
    b_info = BANNERS.get(banner_key, BANNERS["event_char"])
    p4, p5, g5 = user.get("gacha_pity_4", 0), user.get("gacha_pity_5", 0), user.get("gacha_guaranteed_5", 0)

    b = InlineKeyboardBuilder()
    b.button(text="⊱ 🔮 Молитва x1 (160 💎) ⊰", callback_data="gacha_1")
    b.button(text="⊱ 🌟 Молитва x10 (1600 💎) ⊰", callback_data="gacha_10")
    b.button(text="⊱ 🔄 Сменить баннер ⊰", callback_data="gacha_change_banner")
    b.button(text="⊱ 📜 Информация ⊰", callback_data="gacha_info")
    b.button(text="⊱ 🎒 Инвентарь ⊰", callback_data="gacha_inv")
    b.button(text="⊱ ‹ Назад в меню ⊰", callback_data=MenuCB(action="menu", owner_id=user_id))
    b.adjust(1)

    text = (
        f"╭──────────────────────────╮\n"
        f"   🔮 МОЛИТВЫ\n"
        f"╰──────────────────────────╯\n\n"
        f"🎰 Баннер: <b>{b_info['name']}</b>\n\n"
        f"╭ 💎 Примогемы: <b>{user.get('primogems', 0)}</b>\n"
        f"┆\n"
        f"├ 🔮 До гаранта 5★: <b>{b_info['pity_max'] - p5}</b>\n"
        f"┆\n"
        f"├ 🟡 До гаранта 4★: <b>{10 - p4}</b>\n"
        f"┆\n"
        f"╰ 🎯 Гарант: <b>{'Да' if g5 else 'Нет (50/50)'}</b>"
    )
    if is_edit:
        await edit_or_send(message_or_query, text, b.as_markup(), image_url=None)
    else:
        await message_or_query.answer(text, reply_markup=b.as_markup(), parse_mode="HTML")


@dp.message(Command("gacha"))
async def cmd_gacha(message):
    await render_gacha_menu(message, message.from_user.id, message.chat.id, is_edit=False)


@dp.callback_query(MenuCB.filter(F.action == "gacha"))
@inject_user
async def cb_gacha_menu(query, callback_data, user, chat_id):
    if query.from_user.id != callback_data.owner_id: return
    await render_gacha_menu(query, query.from_user.id, chat_id, is_edit=True)


@dp.callback_query(F.data == "gacha_change_banner")
async def cb_gacha_change_banner(query):
    b = InlineKeyboardBuilder()
    for key, val in BANNERS.items(): b.button(text=f"⊱ {val['icon']} {val['name']} ⊰",
                                              callback_data=f"gacha_set_banner_{key}")
    b.button(text="⊱ ‹ Назад ⊰", callback_data="gacha_back")
    b.adjust(1)
    text = f"╭──────────────────────────╮\n   🔄 ВЫБОР БАННЕРА\n╰──────────────────────────╯\n\n🎭 Ивентовый — 50/50.\n💠 Стандартный — только стандартные.\n⚔️ Оружейный — 75/25.\n\nВыбери баннер:"
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(F.data.startswith("gacha_set_banner_"))
@inject_user
async def cb_set_banner(query, user, chat_id):
    key = query.data.replace("gacha_set_banner_", "")
    await update_user(query.from_user.id, chat_id, gacha_banner=key)
    await query.answer(f"✅ Выбран: {BANNERS[key]['name']}", show_alert=False)
    await render_gacha_menu(query, query.from_user.id, chat_id, is_edit=True)


@dp.callback_query(F.data == "gacha_info")
@inject_user
async def cb_gacha_info(query, user, chat_id):
    b_info = BANNERS[user.get("gacha_banner", "event_char")]
    text = f"╭──────────────────────────╮\n   📜 ИНФОРМАЦИЯ\n╰──────────────────────────╯\n\nТекущий: {b_info['icon']} <b>{b_info['name']}</b>\n📝 {b_info['desc']}\n\n🔴 <b>5★</b>: 0.6% (Гарант {b_info['pity_max']})\n🟡 <b>4★</b>: 5.1% (Гарант 10)\n\n💖 Розовая анимация — выигрыш 50/50 или гарант!"
    b = InlineKeyboardBuilder().button(text="⊱ ‹ Назад ⊰", callback_data="gacha_back")
    await edit_or_send(query, text, b.as_markup())


@dp.callback_query(F.data == "gacha_inv")
@inject_user
async def cb_gacha_inv(query, user, chat_id):
    items = await get_gacha_inventory(query.from_user.id, chat_id)
    if not items: return await query.answer("Инвентарь пуст!", show_alert=True)
    lines = [f"╭──────────────────────────╮\n   🎒 ИНВЕНТАРЬ\n╰──────────────────────────╯\n"]
    for it in items[:20]: lines.append(f"{'⭐' * it['rarity']} {it['item_name']}")
    b = InlineKeyboardBuilder().button(text="⊱ ‹ Назад ⊰", callback_data="gacha_back")
    await edit_or_send(query, "\n".join(lines), b.as_markup())


@dp.callback_query(F.data == "gacha_back")
@inject_user
async def cb_gacha_back(query, user, chat_id):
    await render_gacha_menu(query, query.from_user.id, chat_id, is_edit=True)


@dp.callback_query(F.data.in_(["gacha_1", "gacha_10"]))
@inject_user
async def cb_do_pull(query, user, chat_id):
    pulls = 1 if query.data == "gacha_1" else 10
    cost = COST_1 if pulls == 1 else COST_10
    if user.get("primogems", 0) < cost: return await query.answer(f"❌ Нужно {cost} 💎", show_alert=True)
    await query.answer("Крутим...")
    await update_primogems(query.from_user.id, chat_id, -cost)

    banner = user.get("gacha_banner", "event_char")
    p4, p5, g5, l50 = user.get("gacha_pity_4", 0), user.get("gacha_pity_5", 0), user.get("gacha_guaranteed_5", 0), user.get("gacha_lost_50_50", 0)
    results, max_rarity, is_pink, best_item = [], 3, False, None

    for _ in range(pulls):
        rarity, item, p4, p5, g5, l50, pink = get_pull_result(p4, p5, g5, l50, banner)
        results.append((rarity, item))
        img = state._gacha_images.get(item["name"], item["image"])
        await add_gacha_item(query.from_user.id, chat_id, item["name"], item["type"], rarity, img)
        if rarity > max_rarity:
            max_rarity, is_pink, best_item = rarity, pink, item
        elif rarity == 5 and pink:
            is_pink, best_item = True, item
        elif best_item is None:
            best_item = item

    await update_user(query.from_user.id, chat_id, gacha_pity_4=p4, gacha_pity_5=p5, gacha_guaranteed_5=g5, gacha_lost_50_50=l50)
    gif_type = "blue" if max_rarity == 3 else ("purple" if max_rarity == 4 else ("pink" if is_pink else "gold"))

    try:
        await query.message.delete()
    except:
        pass

    gif_id = await get_gacha_gif(gif_type)
    if gif_id:
        try:
            gif_msg = await bot.send_animation(chat_id, gif_id)
            await asyncio.sleep(3)
            await gif_msg.delete()
        except:
            pass

    lines = [f"{'⭐' * rar} {it['name']}" for rar, it in results]
    text = f"🌟 <b>РЕЗУЛЬТАТЫ (x{pulls})</b>\n\n" + "\n".join(lines) + f"\n\n💎 Остаток: {user.get('primogems', 0) - cost}\n🔮 До гаранта: {BANNERS[banner]['pity_max'] - p5}"

    kb = InlineKeyboardBuilder().button(text="⊱ 🔮 К молитвам ⊰", callback_data="gacha_back")
    kb.adjust(1)

    if best_item:
        best_img = state._gacha_images.get(best_item["name"], best_item["image"])
        caption = text + f"\n\n✨ Лучшее: {'⭐' * max_rarity} <b>{best_item['name']}</b>"
        try:
            await bot.send_photo(chat_id=chat_id, photo=best_img, caption=caption, reply_markup=kb.as_markup(), parse_mode="HTML")
        except:
            await bot.send_message(chat_id, text, reply_markup=kb.as_markup(), parse_mode="HTML")
    else:
        await bot.send_message(chat_id, text, reply_markup=kb.as_markup(), parse_mode="HTML")