
import time
import sys
import os

# Add current directory to path so we can import 'speaker'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from speaker import speak, is_speaking
    
    print("🔊 Starting Speaker Test...")
    print("Be ready to hear OMNIS talk!")
    
    test_phrase = "Hello! I am OMNIS. My speaker system is working perfectly on this Raspberry Pi."
    
    print(f"Queueing: '{test_phrase}'")
    speak(test_phrase)
    
    # Wait for it to start speaking
    timeout = 10 # 10 seconds wait for gTTS and init
    start_wait = time.time()
    while not is_speaking() and (time.time() - start_wait < timeout):
        time.sleep(0.1)
        
    if is_speaking():
        print("✅ Speaker is active and playing...")
        while is_speaking():
            time.sleep(0.5)
        print("✅ Speaker finished successfully.")
    else:
        print("❌ Timeout: Speaker never started. Check your audio settings or internet connection for gTTS.")

except Exception as e:
    print(f"❌ Error during speaker test: {e}")
