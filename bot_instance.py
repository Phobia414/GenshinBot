import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import SendMessage, SendPhoto, SendAnimation
from config import BOT_TOKEN


class AutoDeleteSession(AiohttpSession):
    async def make_request(self, bot: Bot, method, timeout=None):
        result = await super().make_request(bot, method, timeout)

        if isinstance(method, (SendMessage, SendPhoto, SendAnimation)):
            if result and hasattr(result, 'chat'):
                chat_type = result.chat.type

                # 1. Если это ЛС (private) или канал — НИКОГДА не ставим на автоудаление
                if chat_type not in ('group', 'supergroup'):
                    return result

                # Дальше логика только для групп
                is_excluded_msg = False
                text = getattr(method, "text", "") or getattr(method, "caption", "") or ""
                text_upper = text.upper()

                # 2. Исключаем созыв (/call) и сообщения боссов из автоудаления
                if "ПОЗЫВНОЙ" in text_upper or "БОСС" in text_upper:
                    is_excluded_msg = True

                reply_markup = getattr(method, "reply_markup", None)
                if reply_markup and hasattr(reply_markup, "inline_keyboard"):
                    for row in reply_markup.inline_keyboard:
                        for button in row:
                            cb_data = getattr(button, "callback_data", "")
                            if cb_data and ("boss:attack" in cb_data or "gboss_attack" in cb_data):
                                is_excluded_msg = True
                                break
                        if is_excluded_msg:
                            break

                # 3. Ставим таймер на удаление, если это обычное сообщение в группе
                if not is_excluded_msg:
                    asyncio.create_task(self.delete_later(bot, result.chat.id, result.message_id, 300))

        return result

    async def delete_later(self, bot: Bot, chat_id: int, message_id: int, delay: int):
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass


bot = Bot(token=BOT_TOKEN, session=AutoDeleteSession())
dp = Dispatcher()