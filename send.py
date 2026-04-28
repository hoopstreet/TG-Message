import asyncio, random, os, database
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import *
from datetime import datetime, timedelta

# Configuration
API_ID = int(os.getenv('API_ID', 39849897))
API_HASH = os.getenv('API_HASH', '21eb2d7f293519cc5eb575c9639e1423')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8664911522:AAHA9qT6L7dv-OlrfNv5lAOiDsg29SujCx8')
OWNER_ID = int(os.getenv('OWNER_ID', 5861858910))
DAILY_LIMIT = 20 

# Localized Device Info for PH (Cebu/Tacloban)
DEVICE = "iPhone 15 Pro"
SYS_VERSION = "iOS 17.4.1"
APP_VERSION = "10.9.1"

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}

def get_pht():
    return datetime.utcnow() + timedelta(hours=8)

def get_random_greeting():
    return random.choice(["Hi", "Hello", "Good day", "Hey", "Mabuhay", "Greetings"])
@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if event.sender_id != OWNER_ID: return
    q = database.supabase.table('queue').select('*', count='exact').execute()
    sent = database.supabase.table('queue').select('*', count='exact').eq('status', 'sent').execute()
    all_accs = database.get_accounts()
    
    active_count = 0
    banned_count = 0
    
    # Quick check for account health
    for acc in all_accs:
        if acc.get('status') == 'banned':
            banned_count += 1
        else:
            active_count += 1

    sched = database.get_setting('schedule_time')
    is_active = "🟢 ACTIVE" if sched != "stopped" else "🔴 INACTIVE"
    
    await event.respond(
        f"🛡️ Schedule: {is_active}\n"
        f"🕒 PHT: {get_pht().strftime('%I:%M %p')}\n"
        f"📱 Active Accounts: {active_count}\n"
        f"🚫 Banned Accounts: {banned_count}\n"
        f"✅ Total List: {q.count}\n"
        f"📤 Total Sent: {sent.count}\n"
        f"⏳ Remaining: {q.count - sent.count}\n"
        f"📅 Sched: {sched}"
    )
@bot.on(events.NewMessage())
async def flow(event):
    if event.text.startswith('/') or event.sender_id not in user_state: return
    state = user_state[event.sender_id]
    
    if state['step'] == 'phone':
        phone = event.text.strip()
        # Spoofing device to look like a PH Mobile user
        client = TelegramClient(
            StringSession(), API_ID, API_HASH,
            device_model=DEVICE, system_version=SYS_VERSION, app_version=APP_VERSION
        )
        await client.connect()
        try:
            sc = await client.send_code_request(phone)
            user_state[event.sender_id].update({'step': 'otp', 'phone': phone, 'client': client, 'hash': sc.phone_code_hash})
            await event.respond(f"📩 OTP sent to {phone}. Enter code quickly:")
        except Exception as e:
            await event.respond(f"❌ OTP Fail: {e}")
            await client.disconnect()

    elif state['step'] == 'otp':
        try:
            await state['client'].sign_in(state['phone'], event.text.strip(), phone_code_hash=state['hash'])
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Account linked successfully from PH device profile!")
            await state['client'].disconnect()
            del user_state[event.sender_id]
        except SessionPasswordNeededError:
            user_state[event.sender_id]['step'] = '2fa'
            await event.respond("🔐 Enter 2FA Password:")
        except Exception as e:
            await event.respond(f"❌ Error: {e}")
async def sender_worker():
    daily_stats = {} 
    while True:
        try:
            sched_str = database.get_setting('schedule_time')
            msg = database.get_setting('active_msg')
            if sched_str == 'stopped' or not sched_str or not msg:
                await asyncio.sleep(30); continue
            
            if get_pht() < datetime.strptime(sched_str, '%Y-%m-%d %H:%M'):
                await asyncio.sleep(60); continue

            accounts = database.get_accounts()
            today = get_pht().strftime('%Y-%m-%d')
            for acc in accounts:
                if acc.get('status') == 'banned': continue
                # ... [Worker continues as before] ...
        except Exception: await asyncio.sleep(30)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(sender_worker())
    bot.run_until_disconnected()
