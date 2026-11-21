import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import SendMessage, SendPhoto, SendAnimation
from aiogram.exceptions import TelegramNetworkError
from config import BOT_TOKEN

class AutoDeleteSession(AiohttpSession):
    async def make_request(self, bot: Bot, method, timeout=None):
        retries = 3
        for attempt in range(retries):
            try:
                result = await super().make_request(bot, method, timeout)
                break
            except TelegramNetworkError as e:
                if attempt == retries - 1:
                    raise e
                await asyncio.sleep(2)
            except Exception as e:
                raise e

        if isinstance(method, (SendMessage, SendPhoto, SendAnimation)):
            if result and hasattr(result, 'chat'):
                chat_type = result.chat.type
                if chat_type not in ('group', 'supergroup'):
                    return result

                is_excluded_msg = False
                text = getattr(method, "text", "") or getattr(method, "caption", "") or ""
                text_upper = text.upper()

                exclude_phrases = [
                    "ПОЗЫВНОЙ", "БОСС", "ОБЯЗАТЕЛЬНАЯ ПОДПИСКА",
                    "У НАС НОВЕНЬКИЙ", "АНКЕТА ОПУБЛИКОВАНА", "АНКЕТА ВСТУПИЛА"
                ]

                if any(phrase in text_upper for phrase in exclude_phrases):
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

                if not is_excluded_msg:
                    # ИЗМЕНЕНО: Автоудаление теперь 3600 секунд (1 час)
                    asyncio.create_task(self.delete_later(bot, result.chat.id, result.message_id, 3600))
        return result

    async def delete_later(self, bot: Bot, chat_id: int, message_id: int, delay: int):
        await asyncio.sleep(delay)
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass

bot = Bot(token=BOT_TOKEN, session=AutoDeleteSession())
dp = Dispatcher()