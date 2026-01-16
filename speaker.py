import os
import threading
import time
import uuid
import pygame
from gtts import gTTS

# Shared state to check if speaker is active
_global_speaker_active = False

def is_speaking():
    return _global_speaker_active

def speak_offline(text):
    """Fast offline TTS using espeak-ng"""
    try:
        # Use espeak-ng for instant feedback
        # -s 150 (speed), -p 50 (pitch), -v en (voice)
        os.system(f"espeak-ng -s 160 -p 40 '{text}' > /dev/null 2>&1")
        return True
    except:
        return False

class GTTSThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.queue = []
        self.lock = threading.Lock()
        self.running = True

    def run(self):
        global _global_speaker_active
        while self.running:
            text_to_speak = None
            
            self.lock.acquire()
            if self.queue:
                text_to_speak = self.queue.pop(0)
            self.lock.release()

            if text_to_speak:
                _global_speaker_active = True
                try:
                    # SPEED OPTIMIZATION: Use offline TTS for short common phrases
                    # This makes greetings and basic ACKs instant.
                    short_phrases = ["yes?", "ok.", "hello!", "hi.", "welcome."]
                    text_lower = text_to_speak.lower().strip()
                    
                    if len(text_to_speak) < 25 or any(p in text_lower for p in short_phrases):
                        if speak_offline(text_to_speak):
                             _global_speaker_active = False # Reset immediately
                             continue

                    # 1. Generate Audio file (High Quality for AI answers)
                    filename = f"speak_{uuid.uuid4()}.mp3"
                    tts = gTTS(text=text_to_speak, lang='en', tld='com')
                    tts.save(filename)

                    # 2. Play Audio (Cross Platform)
                    # For Raspberry Pi USB speakers (Card 1)
                    if os.path.exists('/proc/asound/card1'):
                         os.environ['AUDIODEV'] = 'hw:1,0'
                         os.environ['SDL_PATH_ALSA_DEVICE'] = 'hw:1,0'
                         os.environ['SDL_ALSA_DEVICE'] = 'hw:1,0'

                    # Try mpg123 first on Linux if available (more reliable for MP3 on Pi)
                    played = False
                    if os.name != 'nt':
                        try:
                            # Try to use mpg123 which handles card selection well
                            device = "hw:1,0" if os.path.exists('/proc/asound/card1') else "default"
                            res = os.system(f"mpg123 -q -a {device} {filename} > /dev/null 2>&1")
                            if res == 0:
                                played = True
                        except:
                            pass

                    if not played:
                        try:
                            # Re-initialize mixer if needed
                            if not pygame.mixer.get_init():
                                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
                            
                            pygame.mixer.music.load(filename)
                            pygame.mixer.music.play()
                            
                            while pygame.mixer.music.get_busy():
                                time.sleep(0.1)
                                
                            try:
                                if hasattr(pygame.mixer.music, 'unload'):
                                    pygame.mixer.music.unload()
                            except:
                                pass
                        except Exception as e:
                            print(f"Pygame Audio Error: {e}")
                    
                    # Cleanup
                    if os.path.exists(filename):
                        try:
                            os.remove(filename)
                        except:
                            pass

                except Exception as e:
                    print(f"Speaker Error: {e}")
                finally:
                    _global_speaker_active = False
            else:
                time.sleep(0.1)

    def speak(self, text):
        self.lock.acquire()
        self.queue.append(text)
        self.lock.release()

    def stop(self):
        self.running = False

# Global helper for main.py
_global_speaker_thread = None

def init_speaker_thread():
    global _global_speaker_thread
    if _global_speaker_thread is None:
        _global_speaker_thread = GTTSThread()
        _global_speaker_thread.start()
    return _global_speaker_thread

def speak(text):
    """Global speak function called by main.py"""
    s = init_speaker_thread()
    s.speak(text)
