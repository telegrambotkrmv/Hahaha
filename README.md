# Telegram Video Downloader Bot

Foydalanuvchilar Instagram/TikTok/YouTube linkini yuboradi, bot avtomatik downloader botga yuboradi va videoni qaytaradi.

## Arxitektura

```
User → Sizning Bot → Userbot → Downloader Bot → Video → User
```

## Railway ga deploy qilish

1. Railway.app da yangi loyiha yarating
2. GitHub repo ni ulang
3. Environment variables qo'shing:
   - `BOT_TOKEN`
   - `API_ID`
   - `API_HASH`
   - `PHONE_NUMBER`
   - `ADMIN_PASSWORD`
4. Deploy tugmasini bosing

## Admin buyruqlari

- `/admin` — admin panelini ko'rish
- `/login <parol>` — admin tizimiga kirish
- `/addbot @username` — downloader bot qo'shish
- `/removebot @username` — botni o'chirish
- `/listbots` — botlar ro'yxati
- `/connectuserbot` — userbotni ulash
- `/userbotcode aa12345` — kodni kiritish (oldiga aa qo'shing)
- `/disconnectuserbot` — userbotni uzish

## Tavsiya etilgan downloader botlar

- @SaveVideo_bot
- @DownloadVideoBot
- @getmediabot
