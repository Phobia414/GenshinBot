import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import SendMessage, SendPhoto, SendAnimation
from config import BOT_TOKEN

class AutoDeleteSession(AiohttpSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delete_queue = asyncio.Queue()
        self.worker_started = False

    async def _delete_worker(self, bot):
        while True:
            try:
                chat_id, message_id, delay = await self.delete_queue.get()
                await asyncio.sleep(delay)
                try:
                    await bot.delete_message(chat_id, message_id)
                except Exception:
                    pass
                self.delete_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"AutoDelete error: {e}")

    async def make_request(self, bot: Bot, method, timeout=None):
        result = await super().make_request(bot, method, timeout)

        if not self.worker_started:
            asyncio.create_task(self._delete_worker(bot))
            self.worker_started = True

        if isinstance(method, (SendMessage, SendPhoto, SendAnimation)):
            if result and hasattr(result, 'chat'):
                chat_type = result.chat.type

                if chat_type not in ('group', 'supergroup'):
                    return result

                is_excluded_msg = False
                text = getattr(method, "text", "") or getattr(method, "caption", "") or ""
                text_upper = text.upper()

                exclude_phrases = [
                    "ПОЗЫВНОЙ", "БОСС", "ОБЯЗАТЕЛЬНАЯ ПОДПИСКА", "У НАС НОВЕНЬКИЙ", "АНКЕТА ОПУБЛИКОВАНА"
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
                    # Кладем в очередь, а не создаем отдельную задачу
                    await self.delete_queue.put((result.chat.id, result.message_id, 3600))

        return result


bot = Bot(token=BOT_TOKEN, session=AutoDeleteSession())
dp = Dispatcher()