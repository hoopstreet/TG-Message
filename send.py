import asyncio, random, os, database
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import *
from datetime import datetime, timedelta

API_ID = int(os.getenv('API_ID', 39849897))
API_HASH = os.getenv('API_HASH', '21eb2d7f293519cc5eb575c9639e1423')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8664911522:AAHA9qT6L7dv-OlrfNv5lAOiDsg29SujCx8')
OWNER_ID = int(os.getenv('OWNER_ID', 5861858910))
DAILY_LIMIT = 20 

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
    
    active_count = sum(1 for a in all_accs if a.get('status') != 'banned')
    banned_count = sum(1 for a in all_accs if a.get('status') == 'banned')
    sched = database.get_setting('schedule_time')
    is_active = "🟢 ACTIVE" if sched != "stopped" else "🔴 INACTIVE"
    
    await event.respond(
        f"📱 Active: {active_count}\n"
        f"🚫 Banned: {banned_count}\n"
        f"✅ Total List: {q.count}\n"
        f"📤 Total Sent: {sent.count}\n"
        f"⏳ Remaining: {q.count - sent.count}\n"
        f"🕒 PHT: {get_pht().strftime('%I:%M %p')}\n"
        f"🛡️ Schedule: {is_active}\n"
        f"📅 Sched: {sched}"
    )
@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule_cmd(event):
    if event.sender_id != OWNER_ID: return
    if database.get_setting('schedule_time') != 'stopped':
        database.set_setting('schedule_time', 'stopped')
        await event.respond("🛑 **Previous Schedule Stopped.**")
    user_state[event.sender_id] = {'step': 'sched'}
    await event.respond(f"🕒 PHT: {get_pht().strftime('%Y-%m-%d %I:%M %p')}\nEnter Start Time:")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'list'}
    await event.respond("📂 Send username list:")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'msg'}
    await event.respond("📝 Send promo text:")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'phone'}
    await event.respond("📱 Enter Phone (+63...):")
@bot.on(events.NewMessage())
async def flow(event):
    if event.text.startswith('/') or event.sender_id not in user_state: return
    state = user_state[event.sender_id]
    if state['step'] == 'list':
        users = [u.strip().replace('@', '') for u in event.text.split(',')]
        for u in users: database.add_to_queue(u)
        await event.respond(f"✅ Added {len(users)} users."); del user_state[event.sender_id]
    elif state['step'] == 'msg':
        database.set_setting('active_msg', event.text)
        await event.respond("✅ Text updated."); del user_state[event.sender_id]
    elif state['step'] == 'sched':
        try:
            dt = datetime.strptime(event.text.strip(), '%Y-%m-%d %I:%M %p')
            database.set_setting('schedule_time', dt.strftime('%Y-%m-%d %H:%M'))
            await event.respond(f"🚀 **Scheduled!**\nStarts at {event.text.strip()}"); del user_state[event.sender_id]
        except: await event.respond("❌ Format: 2026-04-29 08:00 AM")
    elif state['step'] == 'phone':
        phone = event.text.strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH, device_model=DEVICE, system_version=SYS_VERSION, app_version=APP_VERSION)
        await client.connect()
        try:
            sc = await client.send_code_request(phone)
            user_state[event.sender_id].update({'step': 'otp', 'phone': phone, 'client': client, 'hash': sc.phone_code_hash})
            await event.respond(f"📩 OTP sent to {phone}. Enter code quickly:")
        except Exception as e:
            await event.respond(f"❌ OTP Fail: {e}"); await client.disconnect()
    elif state['step'] == 'otp':
        try:
            await state['client'].sign_in(state['phone'], event.text.strip(), phone_code_hash=state['hash'])
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Account linked!"); await state['client'].disconnect(); del user_state[event.sender_id]
        except Exception as e: await event.respond(f"❌ Error: {e}")

if __name__ == '__main__':
    bot.run_until_disconnected()
