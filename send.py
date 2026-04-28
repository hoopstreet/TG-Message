import asyncio, random, os, database
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError, PeerFloodError, UserPrivacyRestrictedError
from datetime import datetime, timedelta

API_ID = int(os.getenv('API_ID', 39849897))
API_HASH = os.getenv('API_HASH', '21eb2d7f293519cc5eb575c9639e1423')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8306476254:AAFLnK109G7jQo4gGvRUrzfHfd8kXfZ_UtY')
OWNER_ID = int(os.getenv('OWNER_ID', 5861858910))

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}
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
            if not accounts:
                await asyncio.sleep(60); continue

            for acc in accounts:
                t = database.get_next_target()
                if not t: break
                
                client = TelegramClient(StringSession(acc['session_string']), API_ID, API_HASH)
                try:
                    await client.connect()
                    # Randomized delay before sending (mimics typing/reading)
                    await asyncio.sleep(random.randint(10, 25))
                    await client.send_message(t['username'], msg)
                    database.update_queue(t['id'], 'sent')
                    print(f"✅ Sent to {t['username']}")
                except FloodWaitError as e:
                    print(f"⚠️ Flood wait for {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                except (PeerFloodError, UserPrivacyRestrictedError):
                    database.update_queue(t['id'], 'restricted_skip')
                except Exception as e:
                    database.update_queue(t['id'], 'failed')
                    print(f"❌ Error: {e}")
                finally:
                    await client.disconnect()
                
                # HUMAN DELAY: Wait 5-10 minutes between messages
                # Sending faster than this is the #1 cause of bans
                wait_time = random.randint(300, 600)
                await asyncio.sleep(wait_time)

        except Exception as e:
            await asyncio.sleep(30)
# Re-adding command handlers
@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if event.sender_id != OWNER_ID: return
    q = database.supabase.table('queue').select('*', count='exact').execute()
    sent = database.supabase.table('queue').select('*', count='exact').eq('status', 'sent').execute()
    accs = database.get_accounts()
    sched = database.get_setting('schedule_time')
    await event.respond(f"📊 Stats\nTotal: {q.count}\nSent: {sent.count}\nActive Accs: {len(accs)}\nSched: {sched}")

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

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule_cmd(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'sched'}
    await event.respond("🕒 Enter Date (YYYY-MM-DD HH:MM AM/PM):")

@bot.on(events.NewMessage(pattern='/add_account'))
async def add_acc(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'phone'}
    await event.respond("📱 Enter Phone:")

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
        await event.respond("✅ Message saved."); del user_state[event.sender_id]
    elif state['step'] == 'sched':
        try:
            dt = datetime.strptime(event.text.strip(), '%Y-%m-%d %I:%M %p')
            database.set_setting('schedule_time', dt.strftime('%Y-%m-%d %H:%M'))
            await event.respond(f"📅 Set for: {event.text.strip()}"); del user_state[event.sender_id]
        except: await event.respond("❌ Format error.")
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
            await event.respond("✅ Linked!"); del user_state[event.sender_id]
        except SessionPasswordNeededError:
            user_state[event.sender_id]['step'] = '2fa'
            await event.respond("🔐 Enter 2FA Password:")
    elif state['step'] == '2fa':
        try:
            await state['client'].sign_in(password=event.text.strip())
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Linked!"); del user_state[event.sender_id]
        except: await event.respond("❌ Wrong pass.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(sender_worker())
    bot.run_until_disconnected()
