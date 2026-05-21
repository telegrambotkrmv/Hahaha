import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
WAITING_BOT_USERNAME = set()
WAITING_USERBOT_CODE = set()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Bot qo'shish", callback_data="add_bot"),
            InlineKeyboardButton(text="🗑 Bot o'chirish", callback_data="remove_bot"),
        ],
        [
            InlineKeyboardButton(text="📋 Botlar ro'yxati", callback_data="list_bots"),
        ],
        [
            InlineKeyboardButton(text="🔗 Userbot ulash", callback_data="connect_userbot"),
            InlineKeyboardButton(text="🔌 Userbot uzish", callback_data="disconnect_userbot"),
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_status"),
        ],
    ])


async def admin_panel_text() -> str:
    bots = db.get_downloader_bots()
    userbot_status = db.get_userbot_status()
    active_bot = db.get_active_bot()

    if bots:
        bots_text = ""
        for b in bots:
            mark = "🟢" if b.get("active", False) else "🔴"
            bots_text += f"{mark} @{b['username']}\n"
    else:
        bots_text = "Hech qanday bot qo'shilmagan\n"

    ub_status = "✅ Ulangan" if userbot_status else "❌ Ulanmagan"
    active_text = f"@{active_bot['username']}" if active_bot else "Yo'q"

    return (
        "🔧 *Admin Panel*\n\n"
        f"*Userbot:* {ub_status}\n"
        f"*Faol bot:* {active_text}\n\n"
        f"*Downloader botlar:*\n{bots_text}\n"
        "*Buyruqlar:*\n"
        "/addbot @username — bot qo'shish\n"
        "/removebot @username — botni o'chirish\n"
        "/listbots — botlar ro'yxati\n"
        "/connectuserbot — userbotni ulash\n"
        "/disconnectuserbot — userbotni uzish\n"
        "/userbotcode aa12345 — kodni kiritish\n\n"
        "Yoki quyidagi tugmalardan foydalaning:"
    )


# ───────────────────── START ─────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Salom! Men relay botman.\n\n"
        "Menga xabar yoki link yuboring — men uni ulangan botga yuborib, "
        "natijani sizga qaytaraman.\n\n"
        "Admin kirish: /login parol"
    )


# ───────────────────── AUTH ─────────────────────

@dp.message(Command("login"))
async def cmd_login(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /login parol")
        return
    if parts[1].strip() == ADMIN_PASSWORD:
        ADMIN_IDS.add(message.from_user.id)
        text = await admin_panel_text()
        await message.answer(
            "✅ Xush kelibsiz, admin!\n\n" + text,
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )
    else:
        await message.answer("❌ Noto'g'ri parol!")


# ───────────────────── ADMIN PANEL ─────────────────────

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Avval tizimga kiring: /login parol")
        return
    text = await admin_panel_text()
    await message.answer(text, parse_mode="Markdown", reply_markup=admin_keyboard())


# ───────────────────── BOT MANAGEMENT COMMANDS ─────────────────────

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
    panel = await admin_panel_text()
    await message.answer(panel, parse_mode="Markdown", reply_markup=admin_keyboard())


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
    panel = await admin_panel_text()
    await message.answer(panel, parse_mode="Markdown", reply_markup=admin_keyboard())


@dp.message(Command("listbots"))
async def cmd_listbots(message: Message):
    if not is_admin(message.from_user.id):
        return
    bots = db.get_downloader_bots()
    if not bots:
        await message.answer("Hech qanday bot yo'q.")
        return
    text = "📋 *Downloader botlar:*\n\n"
    for b in bots:
        mark = "🟢" if b.get("active", False) else "🔴"
        text += f"{mark} @{b['username']}\n"
    await message.answer(text, parse_mode="Markdown")


# ───────────────────── USERBOT COMMANDS ─────────────────────

@dp.message(Command("connectuserbot"))
async def cmd_connectuserbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("⏳ Userbot ulanmoqda...")
    result = await userbot_manager.start_auth()
    if result == "already_connected":
        await message.answer("✅ Userbot allaqachon ulangan!")
    elif result == "code_sent":
        WAITING_USERBOT_CODE.add(message.from_user.id)
        await message.answer(
            "📱 Telegramdan kod keldi!\n\n"
            "Kodni /userbotcode orqali kiriting:\n"
            "Misol: kod *12345* bo'lsa:\n"
            "/userbotcode aa12345\n\n"
            "(Oldiga aa qo'shing)",
            parse_mode="Markdown"
        )
    else:
        await message.answer(f"❌ Xatolik: {result}")


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
    WAITING_USERBOT_CODE.discard(message.from_user.id)
    result = await userbot_manager.submit_code(code)
    if result == "success":
        db.set_userbot_status(True)
        await message.answer("✅ Userbot muvaffaqiyatli ulandi!")
        panel = await admin_panel_text()
        await message.answer(panel, parse_mode="Markdown", reply_markup=admin_keyboard())
    else:
        await message.answer(f"❌ Xatolik: {result}")


@dp.message(Command("disconnectuserbot"))
async def cmd_disconnectuserbot(message: Message):
    if not is_admin(message.from_user.id):
        return
    await userbot_manager.disconnect()
    db.set_userbot_status(False)
    await message.answer("✅ Userbot uzildi.")
    panel = await admin_panel_text()
    await message.answer(panel, parse_mode="Markdown", reply_markup=admin_keyboard())


# ───────────────────── INLINE KEYBOARD CALLBACKS ─────────────────────

@dp.callback_query(F.data == "add_bot")
async def cb_add_bot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    WAITING_BOT_USERNAME.add(callback.from_user.id)
    await callback.message.answer(
        "Bot username kiriting:\n"
        "(masalan: SaveVideo_bot yoki @SaveVideo_bot)"
    )
    await callback.answer()


@dp.callback_query(F.data == "remove_bot")
async def cb_remove_bot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    bots = db.get_downloader_bots()
    if not bots:
        await callback.answer("O'chirish uchun bot yo'q!", show_alert=True)
        return
    buttons = []
    for b in bots:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 @{b['username']}",
                callback_data=f"del_{b['username']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="refresh_status")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer("Qaysi botni o'chirmoqchisiz?", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("del_"))
async def cb_delete_bot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    username = callback.data[4:]
    db.remove_downloader_bot(username)
    await callback.answer(f"@{username} o'chirildi!", show_alert=True)
    text = await admin_panel_text()
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())


@dp.callback_query(F.data == "list_bots")
async def cb_list_bots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    bots = db.get_downloader_bots()
    if not bots:
        await callback.answer("Hech qanday bot yo'q!", show_alert=True)
        return
    text = "📋 *Downloader botlar:*\n\n"
    for b in bots:
        mark = "🟢" if b.get("active", False) else "🔴"
        text += f"{mark} @{b['username']}\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "connect_userbot")
async def cb_connect_userbot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer("⏳ Userbot ulanmoqda...")
    result = await userbot_manager.start_auth()
    if result == "already_connected":
        await callback.message.answer("✅ Userbot allaqachon ulangan!")
    elif result == "code_sent":
        WAITING_USERBOT_CODE.add(callback.from_user.id)
        await callback.message.answer(
            "📱 Telegramdan kod keldi!\n\n"
            "Kodni /userbotcode orqali kiriting:\n"
            "Misol: kod *12345* bo'lsa:\n"
            "/userbotcode aa12345\n\n"
            "(Oldiga aa qo'shing)",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(f"❌ Xatolik: {result}")


@dp.callback_query(F.data == "disconnect_userbot")
async def cb_disconnect_userbot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    await userbot_manager.disconnect()
    db.set_userbot_status(False)
    await callback.answer("✅ Userbot uzildi!", show_alert=True)
    text = await admin_panel_text()
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())


@dp.callback_query(F.data == "refresh_status")
async def cb_refresh(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    text = await admin_panel_text()
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())
    await callback.answer("Yangilandi!")


# ───────────────────── MESSAGE RELAY ─────────────────────

@dp.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in WAITING_BOT_USERNAME:
        WAITING_BOT_USERNAME.discard(user_id)
        username = text.lstrip("@").strip()
        db.add_downloader_bot(username)
        await message.answer(f"✅ @{username} qo'shildi!")
        panel = await admin_panel_text()
        await message.answer(panel, parse_mode="Markdown", reply_markup=admin_keyboard())
        return

    if user_id in WAITING_USERBOT_CODE:
        WAITING_USERBOT_CODE.discard(user_id)
        code = text.lstrip("a").strip()
        result = await userbot_manager.submit_code(code)
        if result == "success":
            db.set_userbot_status(True)
            await message.answer("✅ Userbot muvaffaqiyatli ulandi!")
            panel = await admin_panel_text()
            await message.answer(panel, parse_mode="Markdown", reply_markup=admin_keyboard())
        else:
            await message.answer(f"❌ Xatolik: {result}")
        return

    active_bot = db.get_active_bot()
    if not active_bot:
        await message.answer(
            "❌ Hozir hech qanday downloader bot ulanmagan.\n"
            "Admin bilan bog'laning."
        )
        return

    if not db.get_userbot_status():
        await message.answer(
            "❌ Userbot ulanmagan.\n"
            "Admin bilan bog'laning."
        )
        return

    wait_msg = await message.answer("⏳ Yuklanmoqda...")

    try:
        result = await userbot_manager.forward_message(
            bot_username=active_bot["username"],
            text=text
        )

        if result["success"]:
            if result.get("video"):
                await bot.send_video(
                    chat_id=message.chat.id,
                    video=result["video"],
                    caption="✅ Tayyor!"
                )
            elif result.get("file"):
                await bot.send_document(
                    chat_id=message.chat.id,
                    document=result["file"],
                    caption="✅ Tayyor!"
                )
            elif result.get("photo"):
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=result["photo"],
                    caption="✅ Tayyor!"
                )
            elif result.get("text"):
                await message.answer(result["text"])
            else:
                await message.answer("✅ Yuborildi, lekin javob kelmadi.")
        else:
            error = result.get("error", "Noma'lum xato")
            await message.answer(f"❌ {error}")
    except Exception as e:
        logger.error(f"handle_message error: {e}")
        await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
    finally:
        try:
            await wait_msg.delete()
        except Exception:
            pass


async def main():
    logger.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
