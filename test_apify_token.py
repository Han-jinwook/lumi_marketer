"""
Test Apify token validity
"""
import os
from dotenv import load_dotenv
from apify_client import ApifyClient

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_TOKEN")

print(f"🔑 Apify Token: {APIFY_TOKEN[:10]}...{APIFY_TOKEN[-5:] if APIFY_TOKEN and len(APIFY_TOKEN) > 15 else ''}")
print(f"📏 Token Length: {len(APIFY_TOKEN) if APIFY_TOKEN else 0}")

if not APIFY_TOKEN:
    print("❌ APIFY_TOKEN is not set in .env file")
    exit(1)

try:
    client = ApifyClient(APIFY_TOKEN)
    
    # Try to get user info
    print("\n🔍 Testing Apify connection...")
    user = client.user().get()
    
    if user:
        print(f"✅ Authentication successful!")
        print(f"👤 User: {user.get('username', 'N/A')}")
        print(f"📧 Email: {user.get('email', 'N/A')}")
        print(f"💰 Credits: ${user.get('monthlyUsageUsd', 0):.2f} / ${user.get('monthlyLimitUsd', 0):.2f}")
    else:
        print("❌ Authentication failed - no user data returned")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Possible issues:")
    print("   1. Token is invalid or expired")
    print("   2. Token doesn't have proper permissions")
    print("   3. Network connection issue")
    print("\n📝 How to get a valid token:")
    print("   1. Go to https://console.apify.com/account/integrations")
    print("   2. Create a new API token")
    print("   3. Copy the token and update .env file")
