import os
from supabase import create_client

# Hoopstreet Supabase Credentials
url = "https://ixdukafvxqermhgoczou.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml4ZHVrYWZ2eHFlcm1oZ29jem91Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTc1MjM3MiwiZXhwIjoyMDkxMzI4MzcyfQ.R4syxxjfZNKRlMtCfOHpY-XMwZ1LF3RJnQNacBc-dHk"

supabase = create_client(url, key)

def get_pending_users():
    # Pulls users where status is 'pending' from your ixdukafvxqermhgoczou project
    try:
        response = supabase.table('queue').select('*').eq('status', 'pending').execute()
        return response.data
    except Exception as e:
        print(f"Supabase Fetch Error: {e}")
        return []

def update_status(user_id, status):
    try:
        supabase.table('queue').update({'status': status}).eq('id', user_id).execute()
    except Exception as e:
        print(f"Supabase Update Error: {e}")
