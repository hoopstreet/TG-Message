import asyncio, os, sys, threading
from fastapi import FastAPI
import uvicorn
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime, timedelta

# Initialize FastAPI for Northflank Health Check
app = FastAPI()
@app.get("/")
def health(): return {"status": "online"}

def start_web():
    uvicorn.run(app, host="0.0.0.0", port=8080)

# Load Variables from Northflank Environment
API_ID = int(os.getenv('API_ID', 29748251))
API_HASH = os.getenv('API_HASH', 'ce97166a7552c061a3da822233c32873')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8664911522:AAHA9qT6L7dv-OlrfNv5lAOiDsg29SujCx8')
OWNER_ID = int(os.getenv('OWNER_ID', 8296776401))

# Try to import local database logic
sys.path.append('.')
try:
    import database
except ImportError:
    database = None

bot = TelegramClient('bot_commander', API_ID, API_HASH)

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):
    if event.sender_id != OWNER_ID: return
    pht = (datetime.utcnow() + timedelta(hours=8)).strftime('%I:%M %p')
    await event.respond(f"✅ **Node Online (Northflank)**\n🕒 PHT: {pht}")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    if event.sender_id != OWNER_ID: return
    await event.respond("🔄 **QR Login Initiated...**\nLink desktop on your iPhone.")
    
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 11")
    await client.connect()
    
    try:
        qr = await client.qr_login()
        await event.respond(f"🔗 **Link:**\n`{qr.url}`")
        user = await qr.wait()
        session = client.session.save()
        
        if database:
            database.save_account(user.id, session)
            await event.respond(f"✅ Saved {user.first_name} to Supabase!")
        else:
            await event.respond(f"✅ Logged in as {user.first_name} (Database script missing!)")
            
    except Exception as e:
        await event.respond(f"❌ Error: {e}")
    finally:
        await client.disconnect()

async def run_bot():
    await bot.start(bot_token=BOT_TOKEN)
    print("🚀 Bot is listening...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    # Start web server in background
    threading.Thread(target=start_web, daemon=True).start()
    # Run Telegram Bot
    asyncio.run(run_bot())
