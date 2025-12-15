import os
import threading

import cv2
import face_recognition
import pickle

import numpy as np
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from PyQt5.QtGui import QImage


def encode_pickle(payload: str, file: str):
    data = []
    with open(file, 'rb') as f:
        data = pickle.load(f)

    data.append(payload)


class FaceRecognitionThread(QThread):
    # Signal for sending processed frames to UI.
    frame_signal = pyqtSignal(QImage)
    name_signal = pyqtSignal(str)
    image_signal = pyqtSignal(QImage)

    def __init__(self, camera_url=0):
        super(FaceRecognitionThread, self).__init__()
        self.stop_event = threading.Event()
        self.url = camera_url

    def run(self) -> None:
        print("Loading Encoder File")
        with open('images/encoded_file.p', 'rb') as f:
            encode_list_known_with_ids = pickle.load(f)

        encode_list_known, faceIds = encode_list_known_with_ids
        print("Loaded Encoder File.")

        known_faces = faceIds
        known_encodings = encode_list_known

        cap = cv2.VideoCapture(self.url)

        while not self.stop_event.is_set():
            # Read Frames
            _, frame = cap.read()

            if frame is None:
                continue

            print(frame.shape)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(frame)
            face_current_encodings = face_recognition.face_encodings(frame, face_locations)

            student_name = "Unknown"
            # Default avatar if no face or unknown
            image_student = cv2.imread(r'Resources/avatar.png') 
            
            if not face_locations:
                 # If no face detected, we still might want to show the camera feed
                 pass

            for face_location, face_encoding in zip(face_locations, face_current_encodings):
                # Compare face encodings with known encodings
                matches = face_recognition.compare_faces(known_encodings, face_encoding)
                face_distance = face_recognition.face_distance(known_encodings, face_encoding)

                match_index = np.argmin(face_distance)

                if matches[match_index]:
                    print(f"Known face detected: {known_faces[match_index]}")
                    # Check if file exists before reading
                    img_path = f'images/{known_faces[match_index]}.jpg'
                    if os.path.exists(img_path):
                        image_student = cv2.imread(img_path)
                    
                    student_name = known_faces[match_index]
                    y1, x2, y2, x1 = face_location
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(frame, known_faces[match_index], (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                0.9, (0, 255, 0), 2)
                    cv2.putText(frame, "Listening...", (0, 0), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (0, 255, 0), 1)
                else:
                    # image_student is already set to avatar.png
                    student_name = "Unknown"
                    print("Unrecognised Face Found")
                    y1, x2, y2, x1 = face_location
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.putText(frame, "Unknown", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                                0.5, (15, 0, 255), 2)
            
            # Frame
            height, width, channels = frame.shape
            bytes_per_line = channels * width
            # Frame is RGB now, so use Format_RGB888
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Student Image
            if image_student is not None:
                height, width, channels = image_student.shape
                bytes_per_line = channels * width
                # cv2.imread reads in BGR, so use Format_BGR888 for image_student
                q1_image = QImage(image_student.data, width, height, bytes_per_line, QImage.Format_BGR888)
                self.image_signal.emit(q1_image)

            # Emit the frame signal to update UI
            self.frame_signal.emit(q_image)
            self.name_signal.emit(student_name)

    def stop(self):
        self.stop_event.set()




