import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import SendMessage, SendPhoto, SendAnimation
from config import BOT_TOKEN


class AutoDeleteSession(AiohttpSession):
    async def make_request(self, bot: Bot, method, timeout=None):
        result = await super().make_request(bot, method, timeout)

        # Если это текстовое сообщение, фото или гифка БЕЗ кнопок (нет reply_markup)
        if isinstance(method, (SendMessage, SendPhoto, SendAnimation)):
            reply_markup = getattr(method, "reply_markup", None)
            if not reply_markup and result and hasattr(result, 'chat'):
                # Запускаем фоновую задачу на удаление через 30 секунд
                asyncio.create_task(self.delete_later(bot, result.chat.id, result.message_id, 30))

        return result

    async def delete_later(self, bot: Bot, chat_id: int, message_id: int, delay: int):
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass  # Если сообщение уже удалено или нет прав — игнорируем


bot = Bot(token=BOT_TOKEN, session=AutoDeleteSession())
dp = Dispatcher()