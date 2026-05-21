import asyncio
import logging
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession

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

    def _make_client(self):
        return TelegramClient(SESSION_FILE, API_ID, API_HASH)

    async def start_auth(self):
        async with self._lock:
            if self.client and self.client.is_connected():
                if await self.client.is_user_authorized():
                    return "already_connected"

            self.client = self._make_client()
            await self.client.connect()

            if await self.client.is_user_authorized():
                await self._setup_handler()
                return "already_connected"

            self._pending_code_future = asyncio.get_event_loop().create_future()
            await self.client.send_code_request(PHONE_NUMBER)
            return "code_sent"

    async def submit_code(self, code: str):
        try:
            if self._pending_code_future is None:
                return "Avval /connectuserbot buyrug'ini bering"

            self._pending_code_future.set_result(code)
            self._pending_code_future = None

            await self.client.sign_in(PHONE_NUMBER, code)
            await self._setup_handler()
            return "success"
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return str(e)

    async def _setup_handler(self):
        @self.client.on(events.NewMessage())
        async def on_message(event):
            sender = await event.get_sender()
            if sender is None:
                return
            sender_username = getattr(sender, 'username', '') or ''
            chat_id = event.chat_id

            key = f"{sender_username}_{chat_id}"
            if key in self._response_futures and not self._response_futures[key].done():
                self._response_futures[key].set_result(event.message)

    async def forward_link(self, bot_username: str, link: str, user_id: int):
        try:
            if not self.client or not self.client.is_connected():
                return {"success": False, "error": "Userbot ulanmagan"}

            bot_entity = await self.client.get_entity(bot_username)
            chat_id = bot_entity.id

            key = f"{bot_username}_{chat_id}"
            future = asyncio.get_event_loop().create_future()
            self._response_futures[key] = future

            await self.client.send_message(bot_entity, link)

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
            elif response.text:
                return {"success": True, "text": response.text}
            else:
                return {"success": False, "error": "Bot hech narsa yubbormadi"}

        except Exception as e:
            logger.error(f"forward_link error: {e}")
            return {"success": False, "error": str(e)}

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.client = None
