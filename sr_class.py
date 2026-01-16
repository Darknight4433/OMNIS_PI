import threading
import time
import os
import speech_recognition as sr

from speaker import GTTSThread, is_speaking
from ai_response import get_chat_response
from school_data import get_school_answer_enhanced
import shared_state
from register_face import register_name


class SpeechRecognitionThread(threading.Thread):
    def __init__(self, speaker: GTTSThread):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        self.speaker = speaker
        self.verbose = True
        self.conversation_active = False
        self.microphone = None
        self.conversation_timeout = 15
        
        env_wake = os.environ.get('WAKE_WORDS')
        if env_wake:
            self.wake_words = [w.strip().lower() for w in env_wake.split(',') if w.strip()]
        else:
            self.wake_words = ['omnis', 'hello']
        self.recognizer = sr.Recognizer()
        # SUPER SENSITIVITY SETTINGS
        self.recognizer.energy_threshold = 300  # Start lower (sensitive)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8  # Stop listening faster
        self.recognizer.phrase_threshold = 0.3  # Detect speech faster
        self.recognizer.non_speaking_duration = 0.4

    def _open_microphone(self) -> bool:
        # Debug: List all microphones
        print("\nSearching for microphones...")
        try:
            mics = sr.Microphone.list_microphone_names()
            for i, name in enumerate(mics):
                print(f"  [{i}] {name}")
        except:
            print("  (Could not list microphones)")

        # On Windows, using default (index=None) is usually best.
        # On Pi, we might need specific indices.
        indices_to_try = [None] # None = System Default
        
        # Add index 1, 0, 2 just in case
        for i in range(len(mics) if 'mics' in locals() else 3):
             if i not in indices_to_try: indices_to_try.append(i)

        for idx in indices_to_try:
            try:
                name = "Default" if idx is None else str(idx)
                print(f"[Microphone] Trying index {name}...")
                
                self.microphone = sr.Microphone(device_index=idx)
                
                # Fast calibration
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
                
                print(f"✅ Mic Connected on Index {name}")
                return True
            except Exception as e:
                # print(f"   Failed index {idx}: {e}")
                continue
        
        print("❌ Could not find any working microphone.")
        return False

    def run(self) -> None:
        print("\n" + "=" * 50)
        print("🎤 VOICE RECOGNITION STARTED")
        print("=" * 50)
        print("Say 'OMNIS' or 'HELLO' followed by your question")
        print("=" * 50 + "\n")

        while not self.stop_event.is_set() and not self._open_microphone():
            time.sleep(1)

        while not self.stop_event.is_set():
            try:
                # 1. Wait if speaking BEFORE opening the mic
                while is_speaking() and not self.stop_event.is_set():
                    print("🔇 Speaker active, waiting to listen...")
                    time.sleep(0.5)

                with self.microphone as source:
                    # Only adjust for noise if we aren't already in conversation
                    # or do it quickly to avoid missing the user
                    if not self.conversation_active:
                        print("🔊 Adjusting for ambient noise...")
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        
                        # AGGRESSIVE CAPPING for noisy environments
                        if self.recognizer.energy_threshold > 2000:
                            print(f"   (Auto-capping high noise: {self.recognizer.energy_threshold} -> 2000)")
                            self.recognizer.energy_threshold = 2000
                        
                        # Set minimum threshold higher to ignore background
                        if self.recognizer.energy_threshold < 300:
                             self.recognizer.energy_threshold = 300
                        print(f"   Noise level: {self.recognizer.energy_threshold}\n")

                    if self.conversation_active:
                        print("👂 Listening (conversation mode)...")
                    else:
                        print("👂 Listening for 'OMNIS'...")

                    try:
                        # Double check speaker just before listening
                        if is_speaking():
                            continue

                        # Dynamic energy adjustment helps in noisy environments
                        audio_data = self.recognizer.listen(
                            source, 
                            timeout=5, 
                            phrase_time_limit=10
                        )

                        # Skip processing if we started speaking while listening (rare but possible)
                        if is_speaking():
                            print("🔇 Discarding audio (speaker started)")
                            continue

                        print("🔄 Processing audio...")
                        text = self.recognizer.recognize_google(audio_data)
                        print(f"📝 Heard: '{text}'")
                        
                        # Fix common mishearings of "Omnis"
                        text_lower = text.lower()
                        text_lower = text_lower.replace("omni's", "omnis").replace("omni", "omnis").replace("omens", "omnis").replace("honest", "omnis")
                        
                        if getattr(shared_state, 'awaiting_name', False):
                            name_spoken = text.strip()
                            greetings = {'hello', 'hi', 'hey', 'thanks', 'thank you'}
                            norm = name_spoken.lower().strip()
                            if not name_spoken or norm in greetings or len(''.join(ch for ch in norm if ch.isalpha())) < 2:
                                self.speaker.speak("I didn't catch a name.")
                                shared_state.awaiting_name = False
                                shared_state.awaiting_encoding = None
                                shared_state.awaiting_face_image = None
                                continue
                            enc = getattr(shared_state, 'awaiting_encoding', None)
                            img = getattr(shared_state, 'awaiting_face_image', None)
                            ok = register_name(name_spoken, enc, img)
                            if ok:
                                self.speaker.speak(f"Thanks {name_spoken}, I will remember you.")
                            else:
                                self.speaker.speak(f"Sorry, I couldn't save your name.")
                            shared_state.awaiting_name = False
                            shared_state.awaiting_encoding = None
                            shared_state.awaiting_face_image = None
                            continue

                        tokens = text_lower.split()
                        
                        if self.conversation_active:
                            has_wake_word = False
                        else:
                            has_wake_word = any(w in tokens for w in self.wake_words)

                        if has_wake_word or self.conversation_active:
                            if has_wake_word:
                                 # Standard wake word response (unless we are silencing)
                                 pass 

                            question = text_lower
                            for w in self.wake_words:
                                question = question.replace(w, "")
                            question = question.strip()
                            
                            # --- VOICE COMMANDS ---
                            
                            # 1. SILENCE / STOP
                            if any(x in question for x in ["silence", "silent", "stop talking", "shut up", "hush"]):
                                print("\n🛑 SILENCE COMMAND DETECTED")
                                self.speaker.stop() # Stop current thread? Or just queue?
                                # We need a way to clear the queue in speaker.py really.
                                # For now, we just don't reply and reset state.
                                self.conversation_active = False 
                                # Maybe a quick ACK?
                                # self.speaker.speak("Ok.")
                                continue
                                
                            # 2. WHO IS HERE?
                            if any(x in question for x in ["who is here", "who are inside", "detect people", "guess me", "who am i"]):
                                people = getattr(shared_state, 'detected_people', [])
                                if not people:
                                    self.speaker.speak("I don't see anyone right now.")
                                else:
                                    # Filter out 'Unknown'
                                    knowns = [p for p in people if p != "Unknown"]
                                    unknown_count = people.count("Unknown")
                                    
                                    response_parts = []
                                    if knowns:
                                        names = ", ".join(knowns)
                                        response_parts.append(f"I can see {names}.")
                                    if unknown_count > 0:
                                        response_parts.append(f"and {unknown_count} unknown people.")
                                    
                                    if response_parts:
                                        self.speaker.speak(" ".join(response_parts))
                                    else:
                                        self.speaker.speak("I see some people, but I don't know their names.")
                                continue
                                
                            # 3. RESUME / CONTINUE
                            if any(x in question for x in ["continue", "speak again", "hello silence", "resume"]):
                                self.speaker.speak("Ok, I am listening.")
                                self.conversation_active = True
                                continue


                            if has_wake_word:
                               print("\n✅ WAKE WORD DETECTED!\n")
                               self.speaker.speak("Yes?") # Quick ack
                               self.conversation_active = True

                            
                            if question and len(question) >= 3:
                                print(f"❓ Question: {question}\n")
                                school_ans = get_school_answer_enhanced(question)
                                if school_ans:
                                    print(f"🏫 School Response: {school_ans}\n")
                                    self.speaker.speak(school_ans)
                                else:
                                    print("🤖 Getting AI response...")
                                    resp = get_chat_response(question)
                                    if isinstance(resp, dict) and 'choices' in resp:
                                        answer = resp['choices'][0]['message']['content']
                                        print(f"💬 AI Response: {answer}\n")
                                        self.speaker.speak(answer)
                                    else:
                                        self.speaker.speak("Sorry, I couldn't process that.")
                                
                                # Reset timeout on successful interaction
                                if 'timeout_count' not in locals(): timeout_count = 0
                                timeout_count = 0
                        else:
                            print("   (No wake word)\n")

                    except sr.WaitTimeoutError:
                        if self.conversation_active:
                            if 'timeout_count' not in locals(): timeout_count = 0
                            timeout_count += 1
                            if timeout_count >= 3:
                                print("⏱️ Timeout - say 'OMNIS' to start again\n")
                                self.conversation_active = False
                                timeout_count = 0
                    except sr.UnknownValueError:
                        print("   (Didn't catch that)\n")
                    except sr.RequestError as ex:
                        print(f"❌ Speech error: {ex}\n")
                    except Exception as e:
                        print(f"❌ Loop Error: {e}")
                        time.sleep(1)
            except Exception as e:
                print(f"❌ Microphone Error: {e}")
                time.sleep(2)
                
    def stop(self):
        self.stop_event.set()
        print("\n🛑 Voice recognition stopped\n")


if __name__ == '__main__':
    pass