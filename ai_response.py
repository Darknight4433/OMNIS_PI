import os
import google.generativeai as genai
import time

# Fix for gRPC fork/poll error on Raspberry Pi
os.environ["GRPC_POLL_STRATEGY"] = "poll"

# Allow a local, untracked secrets file on devices (e.g., Raspberry Pi).
# The file `secrets_local.py` should define `GEMINI_KEY = 'your-key'`.
def _ensure_api_key():
    """Ensure `api_key` is set and genai is configured.
    This attempts the following (in order):
    - `GEMINI_KEY` environment variable
    - `secrets_local.py` file in the working directory
    If found, configure the `genai` client and return the key, otherwise None.
    """
    key = os.environ.get('GEMINI_KEY')
    if key:
        try:
            genai.configure(api_key=key)
        except Exception:
            pass
        return key

    # Try local file fallback dynamically (works if file is created after import)
    try:
        import importlib
        spec = importlib.util.find_spec('secrets_local')
        if spec is not None:
            secrets_local = importlib.import_module('secrets_local')
            key = getattr(secrets_local, 'GEMINI_KEY', None)
            if key:
                try:
                    genai.configure(api_key=key)
                except Exception:
                    pass
                return key
    except Exception:
        pass

    return None


# Determine api_key at import time if possible
api_key = _ensure_api_key()

if api_key:
    print(f"✅ Gemini API Key Found: {str(api_key)[:8]}...")
else:
    print("❌ Warning: GEMINI_KEY environment variable not set and no local secret found. AI responses will not work.")

def get_response(payload: str):
    """Legacy function - redirects to get_chat_response"""
    return get_chat_response(payload)


def get_chat_response(payload: str):
    """Get AI response using Google Gemini"""
    # Ensure we have a valid API key at call time (pick up secrets_local.py if added later)
    key = api_key or _ensure_api_key()
    if not key:
        return {"error": "Gemini API key not configured"}
    
    try:
        # (Re)configure genai with the discovered key to be safe
        try:
            genai.configure(api_key=key)
        except Exception as e:
            if os.environ.get('OMNIS_DEBUG') == '1':
                print(f"[DEBUG] Config error: {e}")

        # --- MODEL AUTO-DISCOVERY ---
        # Instead of guessing names (which causes 404s), we ask the API what it supports
        discovered_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    # Clean the name (remove 'models/' prefix if present for the constructor)
                    m_name = m.name.split('/')[-1]
                    discovered_models.append(m_name)
            
            # Sort to prioritize 1.5-flash, then 1.5-pro, then others
            priority = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro', 'gemini-pro']
            models_to_try = [p for p in priority if p in discovered_models]
            # Add any other discovered models as final fallbacks
            for m in discovered_models:
                if m not in models_to_try:
                    models_to_try.append(m)
            
            if os.environ.get('OMNIS_DEBUG') == '1' and models_to_try:
                print(f"[DEBUG] Found working models: {models_to_try}")
        except Exception as e:
            if os.environ.get('OMNIS_DEBUG') == '1':
                print(f"[DEBUG] Model discovery failed: {e}")
            # Absolute fallback if discovery fails
            models_to_try = ['gemini-1.5-flash', 'gemini-pro']

        content = None
        last_err = ""
        used_model = "None"

        # Relaxation of safety filters for educational use
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        for model_name in models_to_try:
            try:
                used_model = model_name
                model = genai.GenerativeModel(model_name)
                
                # Allow token tuning via env var for Pi or testing
                max_tokens = int(os.environ.get('GEMINI_MAX_TOKENS', '300'))
                temperature = float(os.environ.get('GEMINI_TEMPERATURE', '0.7'))

                # Improved prompt to allow general knowledge
                full_prompt = (
                    "You are OMNIS, a friendly and intelligent school assistant robot. "
                    "Keep answers brief, concise, and engaging. Be helpful. "
                    "Ignore markdown formatting like bold, asterisks, or bullet points.\n\n"
                    f"User: {payload}"
                )

                response = model.generate_content(
                    full_prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                    ),
                    safety_settings=safety_settings
                )

                # Try to get text content safely
                try:
                    if hasattr(response, 'text') and response.text:
                        content = response.text
                except Exception as e:
                    # Fallback for blocked content - try to get whatever is there
                    if hasattr(response, 'candidates') and response.candidates:
                        try:
                            candidate = response.candidates[0]
                            if candidate.content and candidate.content.parts:
                                content = candidate.content.parts[0].text
                        except:
                            pass
                
                if content and str(content).strip():
                    break # Success!
            except Exception as e:
                last_err = str(e)
                continue

        if content and str(content).strip():
            # Clean up the response text from special characters
            clean_text = str(content).strip().replace('*', '').replace('#', '').replace('_', '')
            return {
                'choices': [{
                    'message': {
                        'content': clean_text
                    }
                }]
            }
        else:
            # Handle empty content or blocked response
            print("\n" + "!" * 40)
            print(f"❌ Gemini API Failed")
            print(f"   Last Error: {last_err}")
            if 'response' in locals():
                try:
                    print(f"   Response Object: {response}")
                    if hasattr(response, 'prompt_feedback'):
                        print(f"   Prompt Feedback: {response.prompt_feedback}")
                except:
                    pass
            print("!" * 40 + "\n")
            
            error_msg = "I'm sorry, I'm having trouble thinking of an answer for that right now. Could you try rephrasing your question?"
            
            # Check for specific key/auth errors
            lower_err = last_err.lower()
            if "key" in lower_err or "auth" in lower_err or "403" in lower_err:
                error_msg = "My AI brain isn't responding. Please check my API key configuration."
            elif "safety" in lower_err or "block" in lower_err:
                error_msg = "I'm not sure how to answer that safely. Please ask me something else!"
            elif not content:
                error_msg = "I'm not sure how to answer that. Please ask me about MGM school rules!"
            
            return {
                'choices': [{
                    'message': {
                        'content': error_msg
                    }
                }]
            }
    except Exception as e:
        print(f"Error getting AI response: {e}")
        return {
            'choices': [{
                'message': {
                    'content': f"I couldn't process that. Error: {str(e)[:50]}"
                }
            }]
        }


if __name__ == '__main__':
    result = get_chat_response("tell me about langchain")
    if 'error' not in result:
        print(result['choices'][0]['message']['content'])
    else:
        print(f"Error: {result['error']}")
