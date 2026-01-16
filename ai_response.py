import os
import google.generativeai as genai
import time

# Fix for gRPC fork/poll error on Raspberry Pi
os.environ["GRPC_POLL_STRATEGY"] = "poll"

# --- CONFIGURATION ---
MAX_TOKENS = 300  # Increased for fuller responses (was 150)
TEMPERATURE = 0.7 
SYSTEM_PROMPT = (
    "You are OMNIS, a friendly school robot from MGM Model School. "
    "Keep answers short (2-3 sentences). Be polite and helpful. "
    "Ignore markdown. Do not use asterisks or bullet points."
)

# --- API KEY ROTATION MANAGER ---
try:
    from api_keys import API_KEYS
except ImportError:
    API_KEYS = []

# Fallback: Check env var or legacy secrets
env_key = os.environ.get('GEMINI_KEY')
if env_key and env_key not in API_KEYS:
    API_KEYS.insert(0, env_key)

try:
    import secrets_local
    legacy_key = getattr(secrets_local, 'GEMINI_KEY', None)
    if legacy_key and legacy_key not in API_KEYS:
        API_KEYS.append(legacy_key)
except: pass

current_key_index = 0

def configure_next_key() -> bool:
    """Rotates to the next available API key. Returns True if successful."""
    global current_key_index
    
    if not API_KEYS:
        print("❌ No API Keys available!")
        return False
        
    attempts = 0
    while attempts < len(API_KEYS):
        key = API_KEYS[current_key_index]
        try:
            print(f"🔑 Switching to API Key #{current_key_index + 1}...")
            genai.configure(api_key=key)
            return True
        except Exception as e:
            print(f"   Key #{current_key_index + 1} failed setup: {e}")
            
        # Rotate index
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        attempts += 1
            
    return False

# Initial configuration
if API_KEYS:
    configure_next_key()
    print(f"✅ Gemini Configured with {len(API_KEYS)} keys available.")
else:
    print("❌ No Gemini Keys found. AI response will fail.")


def get_chat_response(payload: str):
    """Get AI response using Google Gemini with Key Rotation"""
    global current_key_index
    
    if not API_KEYS:
        return {"choices": [{"message": {"content": "I need an API key to think."}}]}

    # Model list: prioritize stable, widely available models
    models_to_try = [
        'gemini-2.0-flash',          # New stable flash
        'gemini-1.5-flash',          # Reliable fallback
        'gemini-1.5-pro',            # High-capability fallback
        'gemini-2.0-flash-exp'       # Experimental
    ]
    
    max_retries = len(API_KEYS) 
    retries = 0
    
    while retries < max_retries:
        content = None
        last_err = ""
        should_rotate_key = False
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {payload}"

                response = model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=MAX_TOKENS,
                        temperature=TEMPERATURE,
                    )
                )
                
                if hasattr(response, 'text') and response.text:
                    content = response.text.strip()
                elif hasattr(response, 'parts'):
                    content = response.parts[0].text.strip()
                elif response.candidates:
                    content = response.candidates[0].content.parts[0].text.strip()
                
                if content: break 

            except Exception as e:
                err_str = str(e).lower()
                # 429/Quota/Rate Limit: These means the KEY is exhausted. Rotate key.
                if any(x in err_str for x in ["429", "quota", "limit", "resource", "exhausted"]):
                    print(f"⚠️ Key #{current_key_index + 1} quota reached. Rotating...")
                    should_rotate_key = True
                    break 
                
                # 404/Permission/Auth: These usually mean the MODEL is not found or key is bad.
                # Try next model on the same key first.
                last_err = f"Model {model_name} failed: {e}"
                continue

        if content:
            clean_text = content.replace('*', '').replace('#', '').replace('**', '')
            return {'choices': [{'message': {'content': clean_text}}]}
            
        if should_rotate_key:
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            configure_next_key()
            retries += 1
            continue
        else:
            # If we've tried all models on this key and still no luck, try next key
            print(f"⚠️ Key #{current_key_index + 1} could not process request. Trying next key...")
            current_key_index = (current_key_index + 1) % len(API_KEYS)
            configure_next_key()
            retries += 1
            continue

    return {'choices': [{'message': {'content': "My daily brain power is exhausted. Please check my API keys."}}]}

if __name__ == '__main__':
    # Test
    print(get_chat_response("What is the capital of India?"))
