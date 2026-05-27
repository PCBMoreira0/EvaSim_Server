import time
import numpy as np
import cv2
import mediapipe as mp
import tensorflow as tf

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Rescaling
from tensorflow.keras.layers import Conv2D, MaxPool2D, Dense, Dropout, Flatten
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.losses import categorical_crossentropy
from tensorflow.keras.optimizers import Adam

import sys    
import os.path
from pathlib import Path

# Importações da nova API do MediaPipe Tasks
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CONFIGURAÇÃO DE CAMINHOS ---
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.append(str(CURRENT_DIR.parent))
MODELS_PATH = str(CURRENT_DIR / 'saved_models') + '/'

emotions = {
    0: ['Angry', (0,0,255), (255,255,255)],
    1: ['Disgust', (0,102,0), (255,255,255)],
    2: ['Fear', (255,255,153), (0,51,51)],
    3: ['Happy', (153,0,153), (255,255,255)],
    4: ['Sad', (255,0,0), (255,255,255)],
    5: ['Surprise', (0,255,0), (255,255,255)],
    6: ['Neutral', (160,160,160), (255,255,255)]
}
num_classes = len(emotions)
input_shape = (48, 48, 1)

weights_1 = MODELS_PATH + 'vggnet.h5'
weights_2 = MODELS_PATH + 'vggnet_up.h5'

class VGGNet(Sequential):
    def __init__(self, input_shape, num_classes, checkpoint_path, lr=1e-3):
        super().__init__()
        self.add(Rescaling(1./255, input_shape=input_shape))
        self.add(Conv2D(64, (3, 3), activation='relu', kernel_initializer='he_normal'))
        self.add(BatchNormalization())
        self.add(Conv2D(64, (3, 3), activation='relu', kernel_initializer='he_normal', padding='same'))
        self.add(BatchNormalization())
        self.add(MaxPool2D())
        self.add(Dropout(0.5))

        self.add(Conv2D(128, (3, 3), activation='relu', kernel_initializer='he_normal', padding='same'))
        self.add(BatchNormalization())
        self.add(Conv2D(128, (3, 3), activation='relu', kernel_initializer='he_normal', padding='same'))
        self.add(BatchNormalization())
        self.add(MaxPool2D())
        self.add(Dropout(0.4))

        self.add(Conv2D(256, (3, 3), activation='relu', kernel_initializer='he_normal', padding='same'))
        self.add(BatchNormalization())
        self.add(Conv2D(256, (3, 3), activation='relu', kernel_initializer='he_normal', padding='same'))
        self.add(BatchNormalization())
        self.add(MaxPool2D())
        self.add(Dropout(0.5))

        self.add(Conv2D(512, (3, 3), activation='relu', kernel_initializer='he_normal', padding='same'))
        self.add(BatchNormalization())
        self.add(Conv2D(512, (3, 3), activation='relu', kernel_initializer='he_normal', padding='same'))
        self.add(BatchNormalization())
        self.add(MaxPool2D())
        self.add(Dropout(0.4))

        self.add(Flatten())
        
        self.add(Dense(1024, activation='relu'))
        self.add(Dropout(0.5))
        self.add(Dense(256, activation='relu'))

        self.add(Dense(num_classes, activation='softmax'))

        self.compile(optimizer=Adam(learning_rate=lr),
                     loss=categorical_crossentropy,
                     metrics=['accuracy'])
        
        self.checkpoint_path = checkpoint_path

model_1 = VGGNet(input_shape, num_classes, weights_1)
model_1.load_weights(model_1.checkpoint_path)

model_2 = VGGNet(input_shape, num_classes, weights_2)
model_2.load_weights(model_2.checkpoint_path)


# ==========================================
# CONFIGURAÇÃO DO MEDIAPIPE TASKS (Inference)
# ==========================================

DETECTOR_MODEL_PATH = MODELS_PATH + 'blaze_face_short_range.tflite'

base_options = python.BaseOptions(model_asset_path=DETECTOR_MODEL_PATH)
options = vision.FaceDetectorOptions(
    base_options=base_options,
    min_detection_confidence=0.5
)

face_detector = None

def get_detector():
    global face_detector
    if face_detector is None:
        face_detector = vision.FaceDetector.create_from_options(options)
    return face_detector

def close_detector():
    global face_detector
    if face_detector is not None:
        face_detector.close() # Libera os recursos C++ explicitamente
        face_detector = None

def detection_preprocessing(image, h_max=360):
    h, w, _ = image.shape
    if h > h_max:
        ratio = h_max / h
        w_ = int(w * ratio)
        image = cv2.resize(image, (w_,h_max))
    return image

def resize_face(face):
    x = tf.expand_dims(tf.convert_to_tensor(face), axis=2)
    return tf.image.resize(x, (48,48))

def recognition_preprocessing(faces):
    x = tf.convert_to_tensor([resize_face(f) for f in faces])
    return x

def inference(image):
    H, W, _ = image.shape
    
    # O Tasks precisa de uma imagem mp.Image RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
    
    face_detector = get_detector()
    # Executa a detecção
    detection_result = face_detector.detect(mp_image)

    prediction = ""

    if detection_result.detections:
        faces = []
        pos = []
        for detection in detection_result.detections:
            box = detection.bounding_box

            x = box.origin_x
            y = box.origin_y
            w = box.width
            h = box.height

            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(x + w, W)
            y2 = min(y + h, H)

            # Evita cortes inválidos
            if (x2 - x1) > 0 and (y2 - y1) > 0:
                face = image[y1:y2, x1:x2]
                face = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
                faces.append(face)
                pos.append((x1, y1, x2, y2))
    
        if faces:
            x_input = recognition_preprocessing(faces)

            y_1 = model_1.predict(x_input, verbose=0)
            y_2 = model_2.predict(x_input, verbose=0)
            l = np.argmax(y_1 + y_2, axis=1)

            for i in range(len(faces)):
                cv2.rectangle(image, (pos[i][0], pos[i][1]),
                              (pos[i][2], pos[i][3]), emotions[l[i]][1], 2, lineType=cv2.LINE_AA)
                
                cv2.rectangle(image, (pos[i][0], pos[i][1] - 20),
                              (pos[i][2] + 20, pos[i][1]), emotions[l[i]][1], -1, lineType=cv2.LINE_AA)
                
                cv2.putText(image, f'{emotions[l[i]][0]}', (pos[i][0], pos[i][1] - 5),
                            0, 0.6, emotions[l[i]][2], 2, lineType=cv2.LINE_AA)

                prediction = emotions[l[i]][0]
    
    return image, prediction

# ==========================================
# LÓGICA DE AVALIAÇÃO E EXECUÇÃO
# ==========================================

face = dict()

def reset_evaluation():
    for expression in ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral', '']:
        face[expression] = 0

reset_evaluation()

def evaluate(g):
    max_key = max(g, key=g.get)
    return max_key

def run():
    run = True
    response = None

    cap = cv2.VideoCapture(0)
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
    fps = cap.get(cv2.CAP_PROP_FPS)

    pTime = 0
    INTERVAL = 4
    timer = time.time()

    try:
        while run:
            success, image = cap.read()
            if success:
                image = cv2.resize(image, (640,480))
                frame, prediction = inference(cv2.flip(image, 1))

                face[prediction] += 1

                cTime = time.time()
                fps = 1 / (cTime - pTime)
                pTime = cTime

                t = time.time() - timer

                if t > INTERVAL:
                    result = evaluate(face).upper()
                    if result != '':
                        print(f"-> Published '{result}'")
                        response = result
                        run = False
                    reset_evaluation()
                    timer += t
            else:
                break

    except KeyboardInterrupt:
        pass

    cap.release()
    cv2.destroyAllWindows()
    return response

def run_from_image(file):
    response = None

    # Decodifica o arquivo para imagem
    nparr = np.frombuffer(file, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is not None:
        frame, prediction = inference(cv2.flip(image, 1))
        face[prediction] += 1
        result = evaluate(face).upper()
        if result != '':
            print(f"-> Published '{result}'")
            response = result
        reset_evaluation()

    return response

if __name__ == "__main__":
    run()