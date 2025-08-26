# test_key.py
import os
from supabase import create_client, Client
from dotenv import load_dotenv

print("--- Starting Supabase Key Test ---")

# 1. Load environment variables from your .env file
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("❌ ERROR: Could not find URL or Key in the .env file.")
    exit()

print("✅ URL and Key were loaded from the .env file.")

try:
    # 2. Initialize the Supabase client
    supabase: Client = create_client(url, key)
    print("✅ Supabase client initialized.")

    # 3. Attempt to perform an admin-only action
    print("⏳ Attempting to list users (this requires admin rights)...")
    response = supabase.auth.admin.list_users()
    
    # 4. Check the result
    print("\n✅ SUCCESS! The service role key is valid and has admin permissions.")
    print(f"Found {len(response.users)} user(s) in your project.")

except Exception as e:
    print("\n❌ FAILURE! The key is not working.")
    print("--- Error Details ---")
    print(e)
    print("---------------------")

print("\n--- Test Complete ---")