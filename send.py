import asyncio
import random
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import AddContactRequest
from telethon.tl.types import UserStatusOffline
from datetime import datetime, timedelta
import database

API_ID = int(os.getenv('API_ID', 39849897))
API_HASH = os.getenv('API_HASH', '21eb2d7f293519cc5eb575c9639e1423')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8306476254:AAFLnK109G7jQo4gGvRUrzfHfd8kXfZ_UtY')
OWNER_ID = int(os.getenv('OWNER_ID', 5861858910))

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}
@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    if event.sender_id != OWNER_ID: return
    parts = event.text.split(maxsplit=1)
    if len(parts) < 2: return await event.respond("📂 Usage: /add_list u1, u2")
    users = [u.strip().replace('@', '') for u in parts[1].split(',')]
    for u in users: database.add_to_queue(u)
    await event.respond(f"✅ Added {len(users)} users.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    if event.sender_id != OWNER_ID: return
    parts = event.text.split(maxsplit=1)
    if len(parts) < 2: return await event.respond("📝 Usage: /edit_msg text")
    database.set_setting('active_msg', parts[1])
    await event.respond("✅ Text updated.")

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule_cmd(event):
    if event.sender_id != OWNER_ID: return
    database.set_setting('schedule_time', 'stopped')
    user_state[event.sender_id] = {'step': 'sched'}
    await event.respond("📅 Enter: YYYY-MM-DD hh:mm AM/PM")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'phone'}
    await event.respond("📱 Enter Phone (+63...):")
@bot.on(events.NewMessage())
async def flow(event):
    if event.text.startswith('/') or event.sender_id not in user_state: return
    state = user_state[event.sender_id]
    if state['step'] == 'sched':
        try:
            dt = datetime.strptime(event.text.strip(), '%Y-%m-%d %I:%M %p')
            database.set_setting('schedule_time', dt.strftime('%Y-%m-%d %H:%M'))
            await event.respond(f"📅 Set for: {event.text.strip()}")
            del user_state[event.sender_id]
        except: await event.respond("❌ Use: YYYY-MM-DD 08:00 AM")
    elif state['step'] == 'phone':
        phone = event.text.strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        sc = await client.send_code_request(phone)
        user_state[event.sender_id].update({'step': 'otp', 'phone': phone, 'client': client, 'hash': sc.phone_code_hash})
        await event.respond("📩 Enter OTP:")
    elif state['step'] == 'otp':
        try:
            await state['client'].sign_in(state['phone'], event.text.strip(), phone_code_hash=state['hash'])
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Account linked!"); del user_state[event.sender_id]
        except Exception as e: await event.respond(f"❌ Error: {e}")
async def sender_worker():
    while True:
        try:
            sched, msg = database.get_setting('schedule_time'), database.get_setting('active_msg')
            if sched == 'stopped' or not sched or not msg:
                await asyncio.sleep(30); continue
            now_pht = datetime.utcnow() + timedelta(hours=8)
            target = datetime.strptime(sched, '%Y-%m-%d %H:%M')
            if now_pht < target:
                await asyncio.sleep(60); continue
            accounts = database.get_accounts()
            for acc in accounts:
                t = database.get_next_target()
                if not t or database.get_setting('schedule_time') == 'stopped': break
                client = TelegramClient(StringSession(acc['session_string']), API_ID, API_HASH)
                try:
                    await client.connect()
                    await client.send_message(t['username'], msg)
                    database.update_queue(t['id'], 'sent')
                except: database.update_queue(t['id'], 'failed')
                finally: await client.disconnect()
                await asyncio.sleep(random.randint(30, 60))
        except Exception as e:
            print(f"Worker Error: {e}"); await asyncio.sleep(30)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(sender_worker())
    print("🚀 Commander Bot + Worker is LIVE...")
    bot.run_until_disconnected()
