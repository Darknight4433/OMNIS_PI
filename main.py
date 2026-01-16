import os
import pickle
import cv2
import numpy as np
import cvzone
import face_recognition
import time
from speaker import speak, is_speaking
from sr_class import SpeechRecognitionThread
import shared_state
from greeting_manager import GreetingManager

# Adapter for SR thread
class SpeakerAdapter:
    def speak(self, text):
        speak(text)

speaker_adapter = SpeakerAdapter()

# Global Configuration
FACE_MATCH_TOLERANCE = float(os.environ.get('FACE_MATCH_TOLERANCE', '0.50'))
MAX_FACES = int(os.environ.get('FACE_MAX_FACES', '4'))
FRAME_SKIP = 3  # Process Face Recognition every Nth frame for speed
RESIZE_FACTOR = 0.25 # Downscale factor for face recognition

# Initialize Greeting Manager
greeter = GreetingManager()

# Load Resources
print("Loading Resources...")
try:
    imgBackground = cv2.imread('Resources/background.png')
    folderModePath = 'Resources/Modes'
    imgModeList = [cv2.imread(os.path.join(folderModePath, p)) for p in sorted(os.listdir(folderModePath))]
except Exception as e:
    print(f"Warning: Could not load background/modes: {e}")
    imgBackground = np.zeros((720, 1280, 3), np.uint8) # Fallback black screen
    imgModeList = []

# Load Encodings
print("Loading Encoded File...")
try:
    with open(r'images/encoded_file.p', 'rb') as f:
        encode_list_known_with_ids = pickle.load(f)
    encode_list_known, studentIds = encode_list_known_with_ids
    print(f"Loaded {len(studentIds)} people.")
except Exception as e:
    print(f"Error loading encodings: {e}")
    encode_list_known, studentIds = [], []

# Reset shared state
try:
    shared_state.awaiting_name = False
except:
    pass

def main():
    global imgBackground
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)
    
    mode_type = 0
    speech_thread = None
    
    # Trackers
    frame_count = 0
    current_faces = []      # Last detected face locations
    current_ids = []        # Last detected face IDs
    
    # Start Voice Listener Immediately (Always-on Assistant)
    print("Starting Voice Assistant...")
    try:
        speech_thread = SpeechRecognitionThread(speaker_adapter)
        speech_thread.daemon = True
        speech_thread.start()
    except Exception as e:
        print(f"Error starting voice: {e}")

    print("Starting OMNIS Main Loop...")
    
    try:
        while True:
            success, img = cap.read()
            if not success or img is None:
                if frame_count % 30 == 0:
                    print("⚠️ Warning: Camera not reading. Check connection.")
                # Create a black placeholder image so the GUI still shows up
                img = np.zeros((480, 640, 3), np.uint8)
                success = True
            
            frame_count += 1
            
            # --- VISION PIPELINE (Optimized) ---
            # Only run heavy Face Recognition every N frames
            if frame_count % FRAME_SKIP == 0:
                imgS = cv2.resize(img, (0, 0), None, RESIZE_FACTOR, RESIZE_FACTOR)
                imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
                
                try:
                    face_locs = face_recognition.face_locations(imgS)
                    # Limit faces to prevent lag
                    if len(face_locs) > MAX_FACES:
                        face_locs = face_locs[:MAX_FACES]
                        
                    if face_locs:
                        face_encs = face_recognition.face_encodings(imgS, face_locs)
                        
                        new_ids = []
                        for encodeFace in face_encs:
                            matches = face_recognition.compare_faces(encode_list_known, encodeFace, tolerance=FACE_MATCH_TOLERANCE)
                            face_dist = face_recognition.face_distance(encode_list_known, encodeFace)
                            
                            match_index = np.argmin(face_dist) if len(face_dist) > 0 else -1
                            
                            if match_index != -1 and matches[match_index]:
                                new_ids.append(studentIds[match_index])
                            else:
                                new_ids.append("Unknown")
                        
                        current_faces = face_locs
                        current_ids = new_ids
                        # Update shared state for Voice Commands ("Who is here?")
                        shared_state.detected_people = current_ids
                    else:
                        current_faces = []
                        current_ids = []
                        shared_state.detected_people = []
                        
                except Exception as e:
                    print(f"Face Rec Error: {e}")
            
            # --- DRAWING PIPELINE ---
            try:
                # Paste webcam feed
                imgBackground[162:162+480, 55:55+640] = img
                if imgModeList:
                    imgBackground[44:44+633, 808:808+414] = imgModeList[mode_type]
            except Exception:
                pass # Prevent crash if resize fails or bg image mismatch
            
            detected_person_for_greeting = None
            
            if current_faces:
                # We have faces (either fresh or cached from previous frame)
                for i, (y1, x2, y2, x1) in enumerate(current_faces):
                    # Scale back up
                    y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                    person_id = current_ids[i]
                    
                    if person_id != "Unknown":
                        # Known Face
                        mode_type = 1
                        bbox = (55+x1, 162+y1, x2 - x1, y2 - y1)
                        imgBackground = cvzone.cornerRect(imgBackground, bbox=bbox, rt=0)
                        
                        # Find the largest/main face to greet
                        detected_person_for_greeting = person_id
                        
                        # UI: Name
                        (w, h), _ = cv2.getTextSize(person_id, cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                        offset = (414 - w) / 2
                        cv2.putText(imgBackground, str(person_id), (808 + int(offset), 445), cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)
                        
                        # UI: Image
                        img_path = f'images/faces/{person_id}.jpg'
                        if os.path.exists(img_path):
                            student_img = cv2.imread(img_path)
                            if student_img is not None:
                                try:
                                    student_img = cv2.resize(student_img, (216, 216))
                                    imgBackground[175:175 + 216, 909:909 + 216] = student_img
                                except: pass
                    
                    else:
                        # Unknown Face
                        mode_type = 0
                        cv2.rectangle(imgBackground, (55+x1, 162+y1), (55+x2, 162+y2), (0, 0, 255), 2)
                        
            else:
                mode_type = 0


            # --- GREETING PIPELINE ---
            # Don't interrupt if already speaking or listening
            if not is_speaking():
                if detected_person_for_greeting:
                    # Check our smart manager
                    greeting_text = greeter.get_greeting(detected_person_for_greeting)
                    if greeting_text:
                        print(f"Greeting: {greeting_text}")
                        speak(greeting_text)
                        
                        # Trigger Voice Listener if not active
                        # (Thread is now started globally, so we just ensure it's still running)
                        if not (speech_thread and speech_thread.is_alive()):
                             # Restart if crashed
                            try:
                                speech_thread = SpeechRecognitionThread(speaker_adapter)
                                speech_thread.daemon = True
                                speech_thread.start()
                            except: pass

                elif len(current_ids) > 0 and "Unknown" in current_ids:
                    # Maybe greet unknown?
                    if greeter.should_greet("Unknown"):
                        msg = greeter.get_unknown_greeting()
                        speak(msg)


            cv2.imshow("Face Attendance", imgBackground)
            if cv2.waitKey(1) == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if speech_thread:
            speech_thread.stop()

if __name__ == "__main__":
    main()
