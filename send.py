import asyncio
import random
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import AddContactRequest
from telethon.tl.types import UserStatusOffline
from datetime import datetime, timedelta
import database

API_ID = 39849897
API_HASH = '21eb2d7f293519cc5eb575c9639e1423'
BOT_TOKEN = '8306476254:AAFLnK109G7jQo4gGvRUrzfHfd8kXfZ_UtY'
OWNER_ID = 5861858910

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_login_state = {}

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    if event.sender_id != OWNER_ID: return
    parts = event.text.split(maxsplit=1)
    if len(parts) < 2: return
    users = [u.strip().replace('@', '') for u in parts[1].split(',')]
    for u in users:
        database.add_to_queue(u)
    await event.respond(f"✅ Cleaned and Added {len(users)} users. Duplicates ignored.")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_account(event):
    if event.sender_id != OWNER_ID: return
    await event.respond("📱 Enter Phone Number (+63...):")
    user_login_state[event.sender_id] = {'step': 'phone'}

@bot.on(events.NewMessage())
async def login_flow(event):
    if event.sender_id not in user_login_state: return
    state = user_login_state[event.sender_id]
    
    if state['step'] == 'phone':
        phone = event.text.strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        sc = await client.send_code_request(phone)
        user_login_state[event.sender_id].update({'step':'otp','phone':phone,'client':client,'hash':sc.phone_code_hash})
        await event.respond("📩 Enter OTP:")
    elif state['step'] == 'otp':
        try:
            await state['client'].sign_in(state['phone'], event.text.strip(), phone_code_hash=state['hash'])
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Account Active & Saved.")
            del user_login_state[event.sender_id]
        except Exception as e: await event.respond(f"❌ Error: {e}")

async def sender_worker():
    while True:
        accounts = database.get_accounts()
        if not accounts:
            await asyncio.sleep(60); continue
            
        for acc in accounts:
            target = database.get_next_target()
            if not target: break
            
            client = TelegramClient(StringSession(acc['session_string']), API_ID, API_HASH)
            try:
                await client.connect()
                # Safety Check: Ignore if inactive > 7 days
                entity = await client.get_entity(target['username'])
                if isinstance(entity.status, UserStatusOffline):
                    if entity.status.was_online < datetime.now() - timedelta(days=7):
                        database.update_queue(target['id'], 'ignored_inactive')
                        continue
                
                await client(AddContactRequest(id=entity, first_name="Client", last_name="", phone="", add_phone_privacy_exception=False))
                await client.send_message(entity, "Your Message Content Here")
                database.update_queue(target['id'], 'sent')
                
                wait = random.randint(300, 600) # 5-10 min delay
                await asyncio.sleep(wait)
            except Exception as e:
                database.update_queue(target['id'], f'failed: {e}')
            finally:
                await client.disconnect()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(sender_worker())
    bot.run_until_disconnected()
