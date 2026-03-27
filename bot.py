import asyncio
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto
)
from pytgcalls import PyTgCall
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall

# 🔑 CONFIG
API_ID = 38687584
API_HASH = "0d494cc2bb431a8bec250a3ebf224a59"
BOT_TOKEN = "8705816076:AAElcimTeKLP1RN1u52whfS9evNUzX8jF1U"

app = Client("single_pro_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call_py = PyTgCalls(app)

queues = {}
paused = {}

# 🎧 Get YouTube / Spotify
def get_audio(query):
    if "spotify" in query:
        query = query.split("/")[-1]

    with yt_dlp.YoutubeDL({"format": "bestaudio", "quiet": True}) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]
        return {
            "url": info["url"],
            "title": info["title"],
            "thumb": info["thumbnail"]
        }

# 📥 Download
def download_song(query):
    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": "song.mp3",
        "quiet": True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch:{query}"])
    return "song.mp3"

# 🎛 Buttons
def buttons(chat_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ Pause", callback_data="pause"),
            InlineKeyboardButton("⏭ Skip", callback_data="skip"),
            InlineKeyboardButton("⏹ Stop", callback_data="stop")
        ],
        [
            InlineKeyboardButton("📥 Download", callback_data="download"),
            InlineKeyboardButton("📜 Queue", callback_data="queue")
        ]
    ])

# ▶️ Play next
async def play_next(chat_id, message=None):
    if queues.get(chat_id):
        data = queues[chat_id].pop(0)
        await call_py.change_stream(chat_id, AudioPiped(data["url"]))

        if message:
            await message.edit_media(
                InputMediaPhoto(
                    media=data["thumb"],
                    caption=f"🎵 {data['title']}"
                ),
                reply_markup=buttons(chat_id)
            )
    else:
        await call_py.leave_group_call(chat_id)

# ▶️ PLAY
@app.on_message(filters.command("play") & filters.group)
async def play(_, message: Message):
    query = " ".join(message.command[1:])
    msg = await message.reply("🔍 Searching...")

    try:
        data = get_audio(query)

        queues.setdefault(message.chat.id, []).append(data)

        try:
            await call_py.get_call(message.chat.id)
            await msg.edit(f"➕ Added: {data['title']}")
        except NoActiveGroupCall:
            await call_py.join_group_call(
                message.chat.id,
                AudioPiped(data["url"])
            )
            queues[message.chat.id].pop(0)

            await msg.delete()
            await message.reply_photo(
                data["thumb"],
                caption=f"🎵 {data['title']}",
                reply_markup=buttons(message.chat.id)
            )

    except Exception as e:
        await msg.edit(str(e))

# 🎛 BUTTONS
@app.on_callback_query()
async def cb(_, query: CallbackQuery):
    chat_id = query.message.chat.id
    data = query.data

    if data == "pause":
        await call_py.pause_stream(chat_id)
        await query.answer("Paused")

    elif data == "skip":
        await play_next(chat_id, query.message)

    elif data == "stop":
        queues[chat_id] = []
        await call_py.leave_group_call(chat_id)
        await query.message.edit("Stopped")

    elif data == "queue":
        q = queues.get(chat_id, [])
        text = "\n".join([s["title"] for s in q]) or "Empty"
        await query.answer(text, show_alert=True)

    elif data == "download":
        await query.answer("Downloading...")
        file = download_song("test")
        await query.message.reply_audio(file)

# 🚀 RUN
async def main():
    await app.start()
    await call_py.start()
    print("🔥 SINGLE BOT PRO RUNNING")
    await idle()

from pyrogram.idle import idle
asyncio.run(main())
