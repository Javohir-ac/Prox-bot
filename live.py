import asyncio
from pyrogram import Client, filters, idle
from pyrogram.raw import functions
from pytgcalls import GroupCallFactory

# Telegram API ma'lumotlari
api_id = 37341350
api_hash = "a492945f474b6ee7bb2459d6bd1d527e"

# Pyrogram client yaratish
app = Client(
    "my_account",
    api_id=api_id,
    api_hash=api_hash,
    workdir="."
)

# GroupCall yaratish
group_call = None

# Kuzatish uchun kanal
CHANNEL = "uz_profil_on"

# Debug uchun barcha xabarlarni ko'rish
@app.on_message(filters.chat(CHANNEL))
async def all_channel_messages(client, message):
    print(f"📨 Xabar keldi: service={message.service}, video_chat_started={hasattr(message, 'video_chat_started')}")
    
    if message.service:
        if message.video_chat_started:
            print("🎥 Video chat boshlandi!")
            await join_group_call(client, message.chat.id)
        elif message.video_chat_ended:
            print("🛑 Video chat tugadi!")
            if group_call:
                await group_call.stop()

async def join_group_call(client, chat_id):
    global group_call
    
    try:
        # GroupCall yaratish
        group_call = GroupCallFactory(client).get_group_call()
        
        # Group call'ga qo'shilish
        await group_call.start(chat_id)
        print(f"✅ Group call'ga qo'shildik: {chat_id}")
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")

async def main():
    await app.start()
    print("✅ Bot ishga tushdi!")
    print(f"📡 Kanal kuzatilmoqda: {CHANNEL}")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
