import asyncio
import random
import logging
from telethon import TelegramClient
from telethon.tl.functions.contacts import AddContactRequest
import database  # Import our Supabase helper

# YOUR CREDENTIALS
API_ID = 39849897
API_HASH = '21eb2d7f293519cc5eb575c9639e1423'

# Initialize Client
client = TelegramClient('hoopstreet_session', API_ID, API_HASH)

async def main():
    await client.start()
    print("Hoopstreet System Online. Checking Supabase for pending users...")

    while True:
        # 1. Fetch users from Supabase
        pending_users = database.get_pending_users()
        
        if not pending_users:
            print("No pending users found. Sleeping for 10 minutes...")
            await asyncio.sleep(600)
            continue

        for record in pending_users:
            username = record['username']
            row_id = record['id']
            
            try:
                print(f"Targeting: {username}")
                
                # Safety Step: Add Contact
                await client(AddContactRequest(
                    id=username, 
                    first_name="Hoopstreet", 
                    last_name="", 
                    phone="", 
                    add_phone_privacy_exception=False
                ))
                
                # Send Message
                await client.send_message(username, "Hello! Your custom message here.")
                
                # Update Supabase to 'sent'
                database.update_status(row_id, 'sent')
                print(f"Success! Updated {username} status to sent.")
                
                # Anti-Ban Delay (3-7 minutes for better safety)
                wait = random.randint(180, 420)
                print(f"Waiting {wait} seconds...")
                await asyncio.sleep(wait)
                
            except Exception as e:
                print(f"Error with {username}: {e}")
                database.update_status(row_id, 'failed')
                await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(main())
