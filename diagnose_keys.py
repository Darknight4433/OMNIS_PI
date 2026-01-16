
import os
import google.generativeai as genai
from api_keys import API_KEYS

def diagnose():
    if not API_KEYS:
        print("❌ No keys found in api_keys.py")
        return

    print(f"🔍 Testing {len(API_KEYS)} keys...\n")
    
    # Very safe model
    model_name = 'gemini-1.5-flash'
    
    for i, key in enumerate(API_KEYS):
        print(f"--- Key #{i+1} ---")
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Say 'Key Working'")
            print(f"✅ Status: SUCCESS")
            print(f"💬 Response: {response.text.strip()}")
        except Exception as e:
            print(f"❌ Status: FAILED")
            print(f"⚠️ Error: {e}")
        print("")

if __name__ == "__main__":
    diagnose()
