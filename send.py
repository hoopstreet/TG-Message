import asyncio, random, os, database
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import *
from datetime import datetime, timedelta

API_ID = int(os.getenv('API_ID', 39849897))
API_HASH = os.getenv('API_HASH', '21eb2d7f293519cc5eb575c9639e1423')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8306476254:AAFLnK109G7jQo4gGvRUrzfHfd8kXfZ_UtY')
OWNER_ID = int(os.getenv('OWNER_ID', 5861858910))

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}

def get_pht():
    return datetime.utcnow() + timedelta(hours=8)

async def sender_worker():
    acc_index = 0
    while True:
        try:
            sched, msg = database.get_setting('schedule_time'), database.get_setting('active_msg')
            if sched == 'stopped' or not sched or not msg:
                await asyncio.sleep(30); continue
            
            if get_pht() < datetime.strptime(sched, '%Y-%m-%d %H:%M'):
                await asyncio.sleep(60); continue

            accounts = database.get_accounts()
            if not accounts:
                await asyncio.sleep(60); continue

            # Cycle through accounts to spread the load
            acc = accounts[acc_index % len(accounts)]
            target = database.get_next_target()
            
            if target:
                client = TelegramClient(StringSession(acc['session_string']), API_ID, API_HASH)
                try:
                    await client.connect()
                    # Mimic human "reading" time
                    await asyncio.sleep(random.randint(15, 45))
                    await client.send_message(target['username'], msg)
                    database.update_queue(target['id'], 'sent')
                    print(f"[{get_pht().strftime('%H:%M')}] ✅ {acc.get('phone', 'Account')} sent to {target['username']}")
                    acc_index += 1 # Only move to next account on success
                except (UserDeactivatedError, SessionRevokedError):
                    print(f"❌ Account Banned/Logged out. Skipping...")
                    # Optional: database.mark_account_dead(acc['id'])
                except FloodWaitError as e:
                    print(f"⏳ Flood: Waiting {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                finally:
                    await client.disconnect()

                # MANDATORY LONG GAP: 10-20 minutes
                # This is the "Human Factor" that prevents mass bans
                await asyncio.sleep(random.randint(600, 1200))
            else:
                await asyncio.sleep(30)
        except Exception as e:
            await asyncio.sleep(30)
@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if event.sender_id != OWNER_ID: return
    q = database.supabase.table('queue').select('*', count='exact').execute()
    sent = database.supabase.table('queue').select('*', count='exact').eq('status', 'sent').execute()
    accs = database.get_accounts()
    await event.respond(f"📊 **PHT: {get_pht().strftime('%I:%M %p')}**\nTotal: {q.count}\nSent: {sent.count}\nAccounts: {len(accs)}")

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
    await event.respond(f"🕒 Enter Date (YYYY-MM-DD HH:MM AM/PM):")

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
            await event.respond(f"📅 Set for: {event.text.strip()}."); del user_state[event.sender_id]
        except: await event.respond("❌ Format: 2026-04-29 08:00 AM")
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
