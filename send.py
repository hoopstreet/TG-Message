import asyncio
import random
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import AddContactRequest
from telethon.tl.types import UserStatusOffline
from datetime import datetime, timedelta
import database

# Use Environment Variables from Northflank
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
    if len(parts) < 2: return
    users = [u.strip().replace('@', '') for u in parts[1].split(',')]
    for u in users: database.add_to_queue(u)
    await event.respond(f"✅ Added {len(users)} users.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    if event.sender_id != OWNER_ID: return
    parts = event.text.split(maxsplit=1)
    if len(parts) < 2: return
    database.set_setting('active_msg', parts[1])
    await event.respond("✅ Message updated.")

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule_cmd(event):
    if event.sender_id != OWNER_ID: return
    database.set_setting('schedule_time', 'stopped')
    await event.respond("🕒 Enter Date & Time (YYYY-MM-DD HH:MM):")
    user_state[event.sender_id] = {'step': 'sched'}

@bot.on(events.NewMessage())
async def flow(event):
    if event.sender_id not in user_state: return
    state = user_state[event.sender_id]
    if state['step'] == 'sched':
        try:
            datetime.strptime(event.text.strip(), '%Y-%m-%d %H:%M')
            database.set_setting('schedule_time', event.text.strip())
            await event.respond(f"📅 Set for: {event.text.strip()}")
            del user_state[event.sender_id]
        except: await event.respond("❌ Format: YYYY-MM-DD HH:MM")

if __name__ == '__main__':
    print("Commander Bot is starting...")
    bot.run_until_disconnected()

async def sender_worker():
    while True:
        try:
            sched = database.get_setting('schedule_time')
            msg = database.get_setting('active_msg')
            if sched == 'stopped' or not sched or not msg:
                await asyncio.sleep(30); continue
            
            now_pht = datetime.utcnow() + timedelta(hours=8)
            target_time = datetime.strptime(sched, '%Y-%m-%d %H:%M')
            
            if now_pht < target_time:
                await asyncio.sleep(60); continue

            accounts = database.get_accounts()
            for acc in accounts:
                target = database.get_next_target()
                if not target or database.get_setting('schedule_time') == 'stopped': break
                
                client = TelegramClient(StringSession(acc['session_string']), API_ID, API_HASH)
                await client.connect()
                await client.send_message(target['username'], msg)
                database.update_queue(target['id'], 'sent')
                await client.disconnect()
                await asyncio.sleep(random.randint(300, 600))
        except Exception as e:
            print(f"Worker Error: {e}")
            await asyncio.sleep(30)

# Update the start logic

async def sender_worker():
    while True:
        try:
            sched = database.get_setting('schedule_time')
            msg = database.get_setting('active_msg')
            if sched == 'stopped' or not sched or not msg:
                await asyncio.sleep(30); continue
            
            now_pht = datetime.utcnow() + timedelta(hours=8)
            target_time = datetime.strptime(sched, '%Y-%m-%d %H:%M')
            
            if now_pht < target_time:
                await asyncio.sleep(60); continue

            accounts = database.get_accounts()
            for acc in accounts:
                target = database.get_next_target()
                if not target or database.get_setting('schedule_time') == 'stopped': break
                
                client = TelegramClient(StringSession(acc['session_string']), API_ID, API_HASH)
                await client.connect()
                await client.send_message(target['username'], msg)
                database.update_queue(target['id'], 'sent')
                await client.disconnect()
                await asyncio.sleep(random.randint(300, 600))
        except Exception as e:
            print(f"Worker Error: {e}")
            await asyncio.sleep(30)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(sender_worker())
    print("🚀 Commander Bot + Worker is LIVE...")
    bot.run_until_disconnected()
