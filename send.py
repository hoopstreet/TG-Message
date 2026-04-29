import asyncio, random, os, database, re
from telethon import TelegramClient, events, functions, types, utils
from telethon.sessions import StringSession
from telethon.errors import *
from datetime import datetime, timedelta

# Your Official App Credentials
API_ID = 29748251
API_HASH = 'ce97166a7552c061a3da822233c32873'
BOT_TOKEN = os.getenv('BOT_TOKEN', '8664911522:AAHA9qT6L7dv-OlrfNv5lAOiDsg29SujCx8')
OWNER_ID = int(os.getenv('OWNER_ID', 5861858910))

# Adoption of iPhone 11 Identity for PH Locale
DEVICE = "iPhone 11"
SYS_VERSION = "17.4"
APP_VERSION = "10.10.1"
LANG = "en-PH"

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}

def get_pht():
    return datetime.utcnow() + timedelta(hours=8)

@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if event.sender_id != OWNER_ID: return
    all_accs = database.get_accounts()
    active_count = sum(1 for a in all_accs if a.get('status') != 'banned')
    await event.respond(f"📱 **PH Node Active**\nDevice: {DEVICE}\nActive Accs: {active_count}\n🕒 PHT: {get_pht().strftime('%I:%M %p')}")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc_init(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'phone'}
    await event.respond("📱 **iPhone 11 Identity Locked.**\nEnter Phone Number (+63...):")

@bot.on(events.NewMessage())
async def flow(event):
    if event.text.startswith('/') or event.sender_id not in user_state: return
    state = user_state[event.sender_id]
    
    if state['step'] == 'phone':
        phone = event.text.strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH, 
            device_model=DEVICE, system_version=SYS_VERSION, app_version=APP_VERSION, 
            lang_code="en", system_lang_code=LANG)
        await client.connect()
        try:
            # Send code request
            sc = await client.send_code_request(phone)
            user_state[event.sender_id].update({'step': 'otp', 'phone': phone, 'client': client, 'hash': sc.phone_code_hash})
            await event.respond("📩 **OTP Sent.** Check your iPhone 11 Telegram app:")
        except Exception as e:
            await event.respond(f"❌ Connection Fail: {e}"); await client.disconnect()

    elif state['step'] == 'otp':
        try:
            # Adopted: Adding a tiny 1-second sleep to prevent 'code previously shared' race condition
            await asyncio.sleep(1.5)
            await state['client'].sign_in(state['phone'], event.text.strip(), phone_code_hash=state['hash'])
            ss = state['client'].session.save()
            database.save_account(state['phone'], ss)
            await event.respond("✅ **SUCCESS!** Account linked from PH."); await state['client'].disconnect()
            del user_state[event.sender_id]
        except SessionPasswordNeededError:
            await event.respond("🔐 **2FA Active.** Enter Cloud Password:")
            user_state[event.sender_id]['step'] = 'password'
        except Exception as e:
            await event.respond(f"❌ Error: {e}"); await state['client'].disconnect(); del user_state[event.sender_id]

    elif state['step'] == 'password':
        try:
            await state['client'].sign_in(password=event.text.strip())
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ **SUCCESS!** 2FA Linked."); await state['client'].disconnect()
            del user_state[event.sender_id]
        except Exception as e: await event.respond(f"❌ 2FA Error: {e}")

if __name__ == '__main__':
    bot.run_until_disconnected()
