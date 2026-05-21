import asyncio
import logging
import os
from telethon import TelegramClient, events

logger = logging.getLogger(__name__)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
PHONE_NUMBER = os.environ["PHONE_NUMBER"]
SESSION_FILE = "userbot_session"


class UserbotManager:
    def __init__(self, db):
        self.db = db
        self.client: TelegramClient = None
        self._pending_code_future = None
        self._response_futures = {}
        self._lock = asyncio.Lock()
        self._handler_registered = False

    def _make_client(self):
        return TelegramClient(SESSION_FILE, API_ID, API_HASH)

    async def start_auth(self):
        async with self._lock:
            if self.client and self.client.is_connected():
                if await self.client.is_user_authorized():
                    if not self._handler_registered:
                        self._setup_handler()
                    return "already_connected"

            self.client = self._make_client()
            await self.client.connect()

            if await self.client.is_user_authorized():
                self._setup_handler()
                return "already_connected"

            loop = asyncio.get_event_loop()
            self._pending_code_future = loop.create_future()
            await self.client.send_code_request(PHONE_NUMBER)
            return "code_sent"

    async def submit_code(self, code: str):
        try:
            if self._pending_code_future is None:
                return "Avval /connectuserbot (tugmadan) bosing"

            self._pending_code_future.set_result(code)
            self._pending_code_future = None

            await self.client.sign_in(PHONE_NUMBER, code)
            self._setup_handler()
            return "success"
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return str(e)

    def _setup_handler(self):
        if self._handler_registered:
            return
        self._handler_registered = True

        @self.client.on(events.NewMessage())
        async def on_new_message(event):
            try:
                sender = await event.get_sender()
                if sender is None:
                    return
                sender_username = (getattr(sender, "username", "") or "").lower()
                chat_id = event.chat_id
                key = f"{sender_username}_{chat_id}"
                if key in self._response_futures:
                    fut = self._response_futures[key]
                    if not fut.done():
                        fut.set_result(event.message)
            except Exception as e:
                logger.error(f"Handler error: {e}")

    async def forward_message(self, bot_username: str, text: str):
        try:
            if not self.client or not self.client.is_connected():
                return {"success": False, "error": "Userbot ulanmagan"}

            bot_entity = await self.client.get_entity(bot_username)
            chat_id = bot_entity.id
            key = f"{bot_username.lower()}_{chat_id}"

            loop = asyncio.get_event_loop()
            future = loop.create_future()
            self._response_futures[key] = future

            await self.client.send_message(bot_entity, text)

            try:
                response = await asyncio.wait_for(future, timeout=60)
            except asyncio.TimeoutError:
                self._response_futures.pop(key, None)
                return {"success": False, "error": "Bot 60 soniyada javob bermadi"}

            self._response_futures.pop(key, None)

            if response.video:
                video_bytes = await self.client.download_media(response.video, bytes)
                return {"success": True, "video": video_bytes}
            elif response.document:
                file_bytes = await self.client.download_media(response.document, bytes)
                return {"success": True, "file": file_bytes}
            elif response.photo:
                photo_bytes = await self.client.download_media(response.photo, bytes)
                return {"success": True, "photo": photo_bytes}
            elif response.text:
                return {"success": True, "text": response.text}
            else:
                return {"success": False, "error": "Bot hech narsa yubbormadi"}

        except Exception as e:
            logger.error(f"forward_message error: {e}")
            return {"success": False, "error": str(e)}

    async def disconnect(self):
        if self.client:
            try:
                await self.client.disconnect()
            except Exception:
                pass
            self.client = None
            self._handler_registered = False
