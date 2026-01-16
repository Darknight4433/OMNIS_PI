"""
Lightweight in-memory shared state for coordination between
the face-detection loop (`main.py`) and the speech thread (`sr_class.py`).

This avoids complex IPC and is fine while the process runs in one interpreter.
"""
from typing import Optional
import numpy as np

# When True, the speech thread should treat the next recognized phrase as a name
awaiting_name: bool = False
# The face encoding (128-d float array) captured for the unknown primary face
awaiting_encoding: Optional[object] = None
# Small RGB image (numpy array) cropped around the unknown face (ready to write)
awaiting_face_image: Optional[object] = None
detected_people = [] # Live list of people currently in frame
