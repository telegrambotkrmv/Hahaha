import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from database import Database
from userbot import UserbotManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()
userbot_manager = UserbotManager(db)

ADMIN_IDS = set()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Salom! Men video yuklovchi botman.\n\n"
        "Instagram, TikTok, YouTube linkini yuboring — videoni qaytaraman.\n\n"
        "Admin: /admin"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if is_admin(message.from_user.id):
        await show_admin_panel(message)
    else:
        await message.answer("Admin parolini kiriting:\n/login <parol>")

@dp.message(Command("login"))
async def cmd_login(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /login <parol>")
        return
    password = parts[1].strip()
    if password == ADMIN_PASSWORD:
        ADMIN_IDS.add(message.from_user.id)
        await message.answer("Admin paneliga xush kelibsiz!")
        await show_admin_panel(message)
    else:
        await message.answer("Noto'g'ri parol!")

async def show_admin_panel(message: Message):
    bots = db.get_downloader_bots()
    userbot_status = db.get_userbot_status()

    bots_text = ""
    if bots:
        for b in bots:
            status = "✅" if b["active"] else "❌"
            bots_text += f"{status} @{b['username']}\n"
    else:
        bots_text = "Hech qanday bot qo'shilmagan\n"

    ub_text = f"{'✅ Ulangan' if userbot_status else '❌ Ulanmagan'}"

    text = (
        "🔧 *Admin Panel*\n\n"
        f"*Downloader botlar:*\n{bots_text}\n"
        f"*Userbot:* {ub_text}\n\n"
        "Buyruqlar:\n"
        "/addbot @username — bot qo'shish\n"
        "/removebot @username — botni o'chirish\n"
        "/listbots — botlar ro'yxati\n"
        "/connectuserbot — userbotni ulash\n"
        "/disconnectuserbot — userbotni uzish\n"
        "/userbotcode <aa12345> — kodni kiritish"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("addbot"))
async def cmd_addbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /addbot @botusername")
        return
    username = parts[1].strip().lstrip("@")
    db.add_downloader_bot(username)
    await message.answer(f"✅ @{username} qo'shildi!")

@dp.message(Command("removebot"))
async def cmd_removebot(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /removebot @botusername")
        return
    username = parts[1].strip().lstrip("@")
    db.remove_downloader_bot(username)
    await message.answer(f"✅ @{username} o'chirildi!")

@dp.message(Command("listbots"))
async def cmd_listbots(message: Message):
    if not is_admin(message.from_user.id):
        return
    bots = db.get_downloader_bots()
    if not bots:
        await message.answer("Hech qanday bot yo'q.")
        return
    text = "📋 *Downloader botlar:*\n"
    for b in bots:
        status = "✅" if b["active"] else "❌"
        text += f"{status} @{b['username']}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("connectuserbot"))
async def cmd_connectuserbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Userbotni ulash boshlandi...\n"
        "Telegram sizga kod yuboradi.\n"
        "Kodni quyidagi formatda yuboring:\n"
        "/userbotcode aa12345\n\n"
        "(Oldiga aa qo'shing, masalan: 12345 → aa12345)"
    )
    result = await userbot_manager.start_auth()
    if result == "already_connected":
        await message.answer("✅ Userbot allaqachon ulangan!")
    elif result == "code_sent":
        await message.answer("📱 Kod yuborildi! /userbotcode aa12345 formatida kiriting.")
    else:
        await message.answer(f"Xatolik: {result}")

@dp.message(Command("userbotcode"))
async def cmd_userbotcode(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /userbotcode aa12345")
        return
    raw_code = parts[1].strip()
    code = raw_code.lstrip("a").strip()
    result = await userbot_manager.submit_code(code)
    if result == "success":
        db.set_userbot_status(True)
        await message.answer("✅ Userbot muvaffaqiyatli ulandi!")
    else:
        await message.answer(f"Xatolik: {result}")

@dp.message(Command("disconnectuserbot"))
async def cmd_disconnectuserbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    await userbot_manager.disconnect()
    db.set_userbot_status(False)
    await message.answer("✅ Userbot uzildi.")

@dp.message(F.text)
async def handle_link(message: Message):
    text = message.text.strip()
    if not any(domain in text for domain in ["instagram.com", "tiktok.com", "youtube.com", "youtu.be", "t.me"]):
        await message.answer("Link yuboring (Instagram, TikTok, YouTube)")
        return

    active_bot = db.get_active_bot()
    if not active_bot:
        await message.answer("❌ Hozir downloader bot ulanmagan. Admin bilan bog'laning.")
        return

    if not db.get_userbot_status():
        await message.answer("❌ Userbot ulanmagan. Admin bilan bog'laning.")
        return

    wait_msg = await message.answer("⏳ Video yuklanmoqda...")

    try:
        result = await userbot_manager.forward_link(
            bot_username=active_bot["username"],
            link=text,
            user_id=message.from_user.id
        )
        if result["success"]:
            if result.get("video"):
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=result["video"],
                    caption="✅ Mana videongiz!"
                )
            elif result.get("file"):
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=result["file"],
                    caption="✅ Mana faylingiz!"
                )
            elif result.get("text"):
                await message.answer(f"Bot javobi: {result['text']}")
            else:
                await message.answer("✅ Javobi topilmadi, lekin so'rov yuborildi.")
        else:
            await message.answer(f"❌ Xatolik: {result.get('error', 'Noma\\'lum xato')}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
    finally:
        await wait_msg.delete()

async def main():
    logger.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
