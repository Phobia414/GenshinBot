import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import SendMessage, SendPhoto, SendAnimation
from config import BOT_TOKEN


class AutoDeleteSession(AiohttpSession):
    async def make_request(self, bot: Bot, method, timeout=None):
        result = await super().make_request(bot, method, timeout)

        # Если это текстовое сообщение, фото или гифка
        if isinstance(method, (SendMessage, SendPhoto, SendAnimation)):
            if result and hasattr(result, 'chat'):
                # Игнорируем каналы, чтобы не удалять список ролей
                if result.chat.type != 'channel':

                    is_boss_msg = False

                    # 1. Проверяем текст или подпись на наличие слова "БОСС"
                    text = getattr(method, "text", "") or getattr(method, "caption", "") or ""
                    if "БОСС" in text.upper():
                        is_boss_msg = True

                    # 2. Проверяем кнопки (если есть кнопка атаки босса - не удаляем)
                    reply_markup = getattr(method, "reply_markup", None)
                    if reply_markup and hasattr(reply_markup, "inline_keyboard"):
                        for row in reply_markup.inline_keyboard:
                            for button in row:
                                cb_data = getattr(button, "callback_data", "")
                                # Проверяем колбэки мирового и гильдейского босса
                                if cb_data and ("boss:attack" in cb_data or "gboss_attack" in cb_data):
                                    is_boss_msg = True
                                    break
                            if is_boss_msg:
                                break

                    # Если это НЕ сообщение с боссом — удаляем через 5 минут (300 секунд)
                    if not is_boss_msg:
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