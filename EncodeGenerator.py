import os

import cv2
import face_recognition
import pickle

# Importing the Student images
folderPath = r'images/faces'
PathList = os.listdir(folderPath)
imgList = []
studentIds = []
print(PathList)

for path in PathList:
    imgList.append(cv2.imread(os.path.join(folderPath, path)))
    studentIds.append(path.split('.')[0])

    filename = f'{folderPath}/{path}'

print(studentIds)


def find_encodings(images_list, names):
    encode_list = []
    final_names = []
    for img, name in zip(images_list, names):
        if img is None:
            print(f"❌ Could not read image for {name}")
            continue
            
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img)
        
        if len(encodings) > 0:
            encode_list.append(encodings[0])
            final_names.append(name)
            print(f"✅ Encoded: {name}")
        else:
            print(f"⚠️ No face found in image for {name}. Skipping.")

    return encode_list, final_names


if __name__ == '__main__':
    print("Encoding Started...")
    encode_list_known, studentIds = find_encodings(imgList, studentIds)
    encode_list_known_with_ids = [encode_list_known, studentIds]
    print(f"Encoding complete. Processed {len(studentIds)} faces.")

    with open('images/encoded_file.p', 'wb') as f:
        pickle.dump(encode_list_known_with_ids, f)

    print('Encoding file saved')
