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
                    # 1. Generate Audio file
                    filename = f"speak_{uuid.uuid4()}.mp3"
                    tts = gTTS(text=text_to_speak, lang='en', tld='com')
                    tts.save(filename)

                    # 2. Play Audio (Cross Platform)
                    # Use pygame instead of system calls for Windows compatibility
                    try:
                        # Re-initialize mixer if needed
                        if not pygame.mixer.get_init():
                            try:
                                # Prioritize Card 1 (USB) on Raspberry Pi if detected
                                if os.path.exists('/proc/asound/card1'):
                                    os.environ['SDL_ALSA_CHANNELS'] = '2'
                                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
                                else:
                                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=4096)
                            except:
                                pygame.mixer.init() # Absolute fallback
                        
                        pygame.mixer.music.load(filename)
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                            
                        # Use try-except for unload as it's missing in some older pygame versions
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
