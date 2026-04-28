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

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}

def get_pht():
    return datetime.utcnow() + timedelta(hours=8)

def get_random_greeting():
    return random.choice(["Hi", "Hello", "Good day", "Hey", "Mabuhay", "Greetings"])
@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if event.sender_id != OWNER_ID: return
    # Fetch total queue count and sent count
    q = database.supabase.table('queue').select('*', count='exact').execute()
    sent = database.supabase.table('queue').select('*', count='exact').eq('status', 'sent').execute()
    accs = database.get_accounts()
    sched = database.get_setting('schedule_time')
    status_text = "🟢 ACTIVE" if sched != "stopped" else "🔴 STOPPED"
    
    await event.respond(
        f"🛡️ **System: {status_text}**\n"
        f"🕒 PHT: {get_pht().strftime('%I:%M %p')}\n"
        f"📱 Senders: {len(accs)}\n"
        f"✅ Total List: {q.count}\n"
        f"📤 Total Sent: {sent.count}\n"
        f"⏳ Remaining: {q.count - sent.count}\n"
        f"📅 Sched: {sched}"
    )
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
        
    elif state['step'] == 'phone':
        phone = event.text.strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            # Send code and keep client in state to sign in later
            sc = await client.send_code_request(phone)
            user_state[event.sender_id].update({'step': 'otp', 'phone': phone, 'client': client, 'hash': sc.phone_code_hash})
            await event.respond(f"📩 OTP sent to {phone}. Enter code:")
        except Exception as e:
            await event.respond(f"❌ OTP Fail: {e}")
            await client.disconnect()

    elif state['step'] == 'otp':
        try:
            await state['client'].sign_in(state['phone'], event.text.strip(), phone_code_hash=state['hash'])
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Account linked!"); await state['client'].disconnect()
            del user_state[event.sender_id]
        except SessionPasswordNeededError:
            user_state[event.sender_id]['step'] = '2fa'
            await event.respond("🔐 Enter 2FA Password:")
        except Exception as e:
            await event.respond(f"❌ Error: {e}")
@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule_cmd(event):
    if event.sender_id != OWNER_ID: return
    database.set_setting('schedule_time', 'stopped')
    user_state[event.sender_id] = {'step': 'sched'}
    await event.respond(f"🕒 PHT: {get_pht().strftime('%Y-%m-%d %I:%M %p')}\nEnter Start Time:")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'phone'}
    await event.respond("📱 Enter Phone (+63...):")

async def sender_worker():
    # Existing worker logic remains here
    pass

if __name__ == '__main__':
    # Ensure worker starts
    loop = asyncio.get_event_loop()
    # (Note: Re-insert the worker logic from the previous stable version here)
    bot.run_until_disconnected()
