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
DAILY_LIMIT = 20 # Max messages per account per day

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}

def get_pht():
    return datetime.utcnow() + timedelta(hours=8)

def get_random_greeting():
    greetings = ["Hi", "Hello", "Good day", "Hey", "Mabuhay", "Greetings"]
    return random.choice(greetings)

async def sender_worker():
    # local tracker for daily limits
    daily_stats = {} # {phone: {'count': 0, 'date': 'YYYY-MM-DD'}}

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

            today = get_pht().strftime('%Y-%m-%d')
            
            for acc in accounts:
                phone = acc.get('phone', 'unknown')
                
                # Check Daily Limit
                if phone not in daily_stats or daily_stats[phone]['date'] != today:
                    daily_stats[phone] = {'count': 0, 'date': today}
                
                if daily_stats[phone]['count'] >= DAILY_LIMIT:
                    print(f"⚠️ Account {phone} reached daily limit. Skipping.")
                    continue

                target = database.get_next_target()
                if not target: break
                
                client = TelegramClient(StringSession(acc['session_string']), API_ID, API_HASH)
                try:
                    await client.connect()
                    
                    # 1. Randomized 'Human' Thinking Gap
                    await asyncio.sleep(random.randint(20, 60))
                    
                    # 2. Show "Typing..." for 5 seconds
                    async with client.action(target['username'], 'typing'):
                        await asyncio.sleep(5)
                        
                        # 3. Add Randomized Greeting to the message
                        full_msg = f"{get_random_greeting()}! {msg}"
                        await client.send_message(target['username'], full_msg)
                    
                    database.update_queue(target['id'], 'sent')
                    daily_stats[phone]['count'] += 1
                    print(f"[{get_pht().strftime('%H:%M')}] ✅ {phone} sent to {target['username']} ({daily_stats[phone]['count']}/{DAILY_LIMIT})")
                    
                    # 4. Mandatory Safety Break (12-25 minutes)
                    # This protects the whole IP and the account group
                    wait_time = random.randint(720, 1500)
                    await asyncio.sleep(wait_time)

                except (UserDeactivatedError, SessionRevokedError):
                    print(f"❌ Account {phone} is BANNED. Removing from rotation.")
                    continue
                except FloodWaitError as e:
                    print(f"⏳ Flood: Waiting {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"⚠️ Error: {e}")
                finally:
                    await client.disconnect()
        except Exception as e:
            await asyncio.sleep(30)
@bot.on(events.NewMessage(pattern='/status'))
async def status_cmd(event):
    if event.sender_id != OWNER_ID: return
    q = database.supabase.table('queue').select('*', count='exact').execute()
    sent = database.supabase.table('queue').select('*', count='exact').eq('status', 'sent').execute()
    accs = database.get_accounts()
    await event.respond(f"🛡️ **Safety Dashboard**\n\n🕒 PHT: {get_pht().strftime('%I:%M %p')}\n📱 Active Senders: {len(accs)}\n✅ Total Sent: {sent.count}\n⏳ Remaining Queue: {q.count - sent.count}\n🚀 Daily Limit: {DAILY_LIMIT}/acc")

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'list'}
    await event.respond("📂 Send username list (comma separated):")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'msg'}
    await event.respond("📝 Send promo text (A greeting will be added automatically):")

@bot.on(events.NewMessage(pattern='/schedule'))
async def schedule_cmd(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'sched'}
    await event.respond(f"🕒 Enter Date (YYYY-MM-DD HH:MM AM/PM):")

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
        await event.respond("✅ Promo message updated."); del user_state[event.sender_id]
    
    elif state['step'] == 'sched':
        try:
            dt = datetime.strptime(event.text.strip(), '%Y-%m-%d %I:%M %p')
            database.set_setting('schedule_time', dt.strftime('%Y-%m-%d %H:%M'))
            await event.respond(f"📅 Schedule set for: {event.text.strip()}"); del user_state[event.sender_id]
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
            await event.respond("✅ Account linked safely!"); del user_state[event.sender_id]
        except SessionPasswordNeededError:
            user_state[event.sender_id]['step'] = '2fa'
            await event.respond("🔐 2FA detected. Enter Cloud Password:")
        except Exception as e: await event.respond(f"❌ Error: {e}")
    
    elif state['step'] == '2fa':
        try:
            await state['client'].sign_in(password=event.text.strip())
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Linked (2FA)!"); del user_state[event.sender_id]
        except: await event.respond("❌ Wrong password.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(sender_worker())
    bot.run_until_disconnected()
