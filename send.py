import asyncio
import random
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import database

# CREDENTIALS
API_ID = 39849897
API_HASH = '21eb2d7f293519cc5eb575c9639e1423'
BOT_TOKEN = '8306476254:AAFLnK109G7jQo4gGvRUrzfHfd8kXfZ_UtY'
OWNER_ID = 5861858910

bot = TelegramClient('bot_commander', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Temporary storage for login states
user_login_state = {}

@bot.on(events.NewMessage(pattern='/add_list'))
async def add_list(event):
    if event.sender_id != OWNER_ID: return
    parts = event.text.split(maxsplit=1)
    if len(parts) < 2:
        await event.respond("Usage: /add_list username1, username2")
        return
    users = [u.strip() for u in parts[1].split(',')]
    # Add to Supabase logic here
    await event.respond(f"✅ Added {len(users)} users to the queue.")

@bot.on(events.NewMessage(pattern='/edit_msg'))
async def edit_msg(event):
    if event.sender_id != OWNER_ID: return
    msg_text = event.text.split(maxsplit=1)[1]
    # Save to Supabase settings
    await event.respond(f"✅ Message updated to: {msg_text}")

@bot.on(events.NewMessage(pattern='/add_account'))
async def start_add_account(event):
    if event.sender_id != OWNER_ID: return
    await event.respond("📱 Please enter the phone number (e.g., +639...):")
    user_login_state[event.sender_id] = {'step': 'phone'}

@bot.on(events.NewMessage())
async def handle_login_steps(event):
    if event.sender_id not in user_login_state: return
    state = user_login_state[event.sender_id]
    
    if state['step'] == 'phone':
        phone = event.text.strip()
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        send_code = await client.send_code_request(phone)
        user_login_state[event.sender_id] = {'step': 'otp', 'phone': phone, 'client': client, 'hash': send_code.phone_code_hash}
        await event.respond("📩 Code sent. Please enter the OTP:")
        
    elif state['step'] == 'otp':
        otp = event.text.strip()
        client = state['client']
        try:
            await client.sign_in(state['phone'], otp, phone_code_hash=state['hash'])
            session_str = client.session.save()
            # SAVE TO DATABASE HERE
            await event.respond("✅ Account linked successfully!")
            del user_login_state[event.sender_id]
        except Exception as e:
            if "password" in str(e).lower():
                state['step'] = '2fa'
                await event.respond("🛡 2FA detected. Please enter your Cloud Password:")
            else:
                await event.respond(f"❌ Error: {e}")

    elif state['step'] == '2fa':
        try:
            await state['client'].sign_in(password=event.text.strip())
            await event.respond("✅ Account linked with 2FA!")
            del user_login_state[event.sender_id]
        except Exception as e:
            await event.respond(f"❌ 2FA Failed: {e}")

print("Commander Bot is starting...")
bot.run_until_disconnected()
