import asyncio

from aiogram import types
from aiogram.filters import Command

from bot_instance import dp
from config import OWNER_ID
from constants import DIV, PLACEHOLDER_IMAGE
from characters import CHARACTERS


@dp.message(Command("checkimages"))
async def cmd_checkimages(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("🔍 Проверяю все картинки персонажей. Это займёт 15–30 секунд, подожди...")

    try:
        import aiohttp
    except ImportError:
        await message.answer("❌ Установи aiohttp: `pip install aiohttp`")
        return

    sem = asyncio.Semaphore(20)

    async def check_one(session, name, url):
        async with sem:
            try:
                timeout = aiohttp.ClientTimeout(total=8)
                async with session.head(url, timeout=timeout, allow_redirects=True) as resp:
                    ct = resp.headers.get("Content-Type", "")
                    if resp.status != 200:
                        return (name, f"HTTP {resp.status}")
                    if not ct.startswith("image/"):
                        return (name, f"не картинка ({ct[:30]})")
                    return None
            except Exception as e:
                return (name, str(e)[:60])

    no_url = []
    is_placeholder = []
    broken = []

    async with aiohttp.ClientSession() as session:
        tasks = []
        for name, data in CHARACTERS.items():
            url = data.get("image", "") or ""
            if not url:
                no_url.append(name)
                continue
            if url == PLACEHOLDER_IMAGE:
                is_placeholder.append(name)
                continue
            tasks.append((name, check_one(session, name, url)))

        if tasks:
            results = await asyncio.gather(*(t[1] for t in tasks))
            for r in results:
                if r:
                    broken.append(r)

    total = len(CHARACTERS)
    ok_count = total - len(broken) - len(is_placeholder) - len(no_url)

    lines = [
        f"🔍 ПРОВЕРКА КАРТИНОК",
        DIV,
        f"Всего: {total}",
        f"✅ Рабочих: {ok_count}",
    ]

    if broken:
        lines.append("")
        lines.append(f"❌ БИТЫЕ ССЫЛКИ ({len(broken)}):")
        for n, e in broken:
            lines.append(f"• {n} — {e}")
        lines.append("")
        lines.append("ℹ️ У них показывается заглушка.")

    if is_placeholder:
        lines.append("")
        lines.append(f"🖼 СТОИТ ЗАГЛУШКА ({len(is_placeholder)}):")
        for n in is_placeholder:
            lines.append(f"• {n}")

    if no_url:
        lines.append("")
        lines.append(f"⬜ НЕТ ССЫЛКИ ({len(no_url)}):")
        for n in no_url:
            lines.append(f"• {n}")

    if not (broken or is_placeholder or no_url):
        lines.append("")
        lines.append("✅ Все ссылки рабочие.")

    text = "\n".join(lines)
    if len(text) > 4000:
        chunks = []
        cur = []
        size = 0
        for ln in text.split("\n"):
            if size + len(ln) + 1 > 3800:
                chunks.append("\n".join(cur))
                cur = [ln]
                size = len(ln)
            else:
                cur.append(ln)
                size += len(ln) + 1
        if cur:
            chunks.append("\n".join(cur))
        for ch in chunks:
            await message.answer(ch)
        return

    await message.answer(text)