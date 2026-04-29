import asyncio, os, database, re, sys
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import *
from datetime import datetime, timedelta

# Add the MCP folder to path
sys.path.append('/root/mcp-merge')

API_ID = 29748251
API_HASH = 'ce97166a7552c061a3da822233c32873'
BOT_TOKEN = '8664911522:AAHA9qT6L7dv-OlrfNv5lAOiDsg29SujCx8'
OWNER_ID = 5861858910

DEVICE, SYS_VERSION, APP_VERSION = "iPhone 11", "17.4", "10.10.1"

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def get_pht():
    return datetime.utcnow() + timedelta(hours=8)

@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if event.sender_id != OWNER_ID: return
    all_accs = database.get_accounts()
    active_count = sum(1 for a in all_accs if a.get('status') != 'banned')
    await event.respond(f"📱 **MCP QR-Node Active**\nAccs: {active_count}\n🕒 PHT: {get_pht().strftime('%I:%M %p')}")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc_init(event):
    if event.sender_id != OWNER_ID: return
    await event.respond("🔄 **Generating QR Login...**\nOpen iPhone 11 > Settings > Devices > Link Desktop.")
    
    client = TelegramClient(StringSession(), API_ID, API_HASH, device_model=DEVICE)
    await client.connect()
    
    try:
        qr_login = await client.qr_login()
        # Sending the raw token link
        await event.respond(f"🔗 **Action Required:**\nClick this link on your phone to authorize:\n\n`{qr_login.url}`\n\nWaiting for you to authorize...")
        
        user = await qr_login.wait()
        session_str = client.session.save()
        me = await client.get_me()
        
        # Identify the account by phone or username
        acc_id = me.phone if me.phone else (me.username if me.username else "Unknown")
        database.save_account(acc_id, session_str)
        
        await event.respond(f"✅ **Success!** Logged in as {me.first_name}.")
    except Exception as e:
        await event.respond(f"❌ QR Login Failed: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    print("Bot is starting...")
    bot.run_until_disconnected()
