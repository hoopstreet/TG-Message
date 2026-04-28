import asyncio, random, os, database, re
from telethon import TelegramClient, events, functions, types, utils
from telethon.sessions import StringSession
from telethon.errors import *
from datetime import datetime, timedelta

API_ID = int(os.getenv('API_ID', 39849897))
API_HASH = os.getenv('API_HASH', '21eb2d7f293519cc5eb575c9639e1423')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8664911522:AAHA9qT6L7dv-OlrfNv5lAOiDsg29SujCx8')
OWNER_ID = int(os.getenv('OWNER_ID', 5861858910))

DEVICE, SYS_VERSION, APP_VERSION, LANG = "iPhone 15 Pro", "iOS 17.4.1", "10.9.1", "en-PH"

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_state = {}

def get_pht():
    return datetime.utcnow() + timedelta(hours=8)

def parse_username(text):
    # Regex to extract username from links or @mentions
    match = re.search(r'(?:t\.me\/|@|^)([a-zA-Z0-9_]{5,32})', text.strip())
    return match.group(1) if match else None

async def validate_user(client, username):
    try:
        entity = await client.get_entity(username)
        if not isinstance(entity, types.User) or entity.bot: return None
        # Activity check: Last 7 days
        status = entity.status
        if isinstance(status, types.UserStatusOffline):
            if (datetime.now(status.was_online.tzinfo) - status.was_online).days > 7:
                return None
        elif isinstance(status, types.UserStatusEmpty): return None
        return entity.username
    except: return None
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
    await event.respond(f"📱 Active: {active_count}\n🚫 Banned: {banned_count}\n✅ Total List: {q.count}\n📤 Total Sent: {sent.count}\n⏳ Remaining: {q.count - sent.count}\n🕒 PHT: {get_pht().strftime('%I:%M %p')}\n🛡️ Schedule: {is_active}\n📅 Sched: {sched}")
@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list_cmd(event):
    if event.sender_id != OWNER_ID: return
    user_state[event.sender_id] = {'step': 'list'}
    await event.respond("📂 Send list (usernames, @mentions, or t.me links):")

@bot.on(events.NewMessage())
async def flow(event):
    if event.text.startswith('/') or event.sender_id not in user_state: return
    state = user_state[event.sender_id]
    
    if state['step'] == 'list':
        raw_inputs = re.split(r'[,\s\n]+', event.text)
        added, skipped = 0, 0
        accs = database.get_accounts()
        if not accs: 
            await event.respond("❌ No active accounts found to validate list."); return
        
        await event.respond("🔍 Filtering bots & inactive users...")
        v_client = TelegramClient(StringSession(accs[0]['session_string']), API_ID, API_HASH)
        await v_client.connect()
        
        for raw in raw_inputs:
            uname = parse_username(raw)
            if not uname: continue
            
            # Duplicate check
            exists = database.supabase.table('queue').select('username').eq('username', uname).execute()
            if exists.data:
                skipped += 1; continue
            
            valid_name = await validate_user(v_client, uname)
            if valid_name:
                database.add_to_queue(valid_name)
                added += 1
            else: skipped += 1
            
        await v_client.disconnect()
        await event.respond(f"✅ Added: {added}\n⏩ Skipped (Duplicate/Bot/7d Inactive): {skipped}")
        del user_state[event.sender_id]
    elif state['step'] == 'phone':
        phone = event.text.strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH, 
            device_model=DEVICE, system_version=SYS_VERSION, app_version=APP_VERSION,
            lang_code="en", system_lang_code=LANG)
        await client.connect()
        sc = await client.send_code_request(phone)
        user_state[event.sender_id].update({'step': 'otp', 'phone': phone, 'client': client, 'hash': sc.phone_code_hash})
        await event.respond(f"📩 OTP sent to {phone}. Enter code:")
    
    elif state['step'] == 'otp':
        try:
            await state['client'].sign_in(state['phone'], event.text.strip(), phone_code_hash=state['hash'])
            database.save_account(state['phone'], state['client'].session.save())
            await event.respond("✅ Account linked from Tacloban/Cebu device profile!"); await state['client'].disconnect()
            del user_state[event.sender_id]
        except Exception as e: await event.respond(f"❌ Error: {e}")

if __name__ == '__main__':
    bot.run_until_disconnected()
