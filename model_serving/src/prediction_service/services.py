import numpy as np
from fastapi import HTTPException, status
from src.utils.common import decode_base64_image, encode_image_into_base64
from tensorflow.keras.models import load_model
from aipilot.tf.cv import GradCam
from PIL import Image
from typing import Union
import cv2

def _wb(channel, perc = 0.05):
    mi, ma = (np.percentile(channel, perc), np.percentile(channel,100.0-perc))
    channel = np.uint8(np.clip((channel-mi)*255.0/(ma-mi), 0, 255))
    return channel
def apply_white_balance(input_img_path, output_img_path):
    if input_img_path.endswith(('.jpg','.png', '.jpeg', '.JPG', '.PNG', '.JPEG')):
        image = cv2.imread(input_img_path)
        # performing white balance
        imWB  = np.dstack([_wb(channel, 0.05) for channel in cv2.split(image)])
        gray_image = cv2.cvtColor(imWB, cv2.COLOR_BGR2GRAY)
        rgb_img = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2RGB)
        image = cv2.resize(rgb_img, (224, 224))
        cv2.imwrite(output_img_path, image)
    else:
        raise Exception("Invalid File Extension. Valid Extensions : ['.jpg','.png', '.jpeg', '.JPG', '.PNG', '.JPEG']")

def predict(base64_enc_img : str, model_path: str ,
            input_img_path: str, output_img_path: str):
    decode_base64_image(base64_enc_img, input_img_path)
    apply_white_balance(input_img_path=input_img_path,
                                  output_img_path=input_img_path)
    img_arr = np.asarray(Image.open(input_img_path))
    img_arr =  np.expand_dims(img_arr, axis=0)/255.0
    model = load_model(model_path)
    prediction_proba = np.round(model.predict(img_arr), decimals = 6)
    predicted_cls = np.argmax(prediction_proba, axis=1)[0]

    gradcam = GradCam(model, "conv5_block32_concat", in_img_path= input_img_path,
                      out_img_path=output_img_path,  normalize_img=True)
    gradcam.get_gradcam()

    base64_enc_class_activation_map = encode_image_into_base64(output_img_path)
    
    prediction_proba = list(prediction_proba[0])
    prediction_proba = [round(float(i), 2) for i in prediction_proba]
    if isinstance(prediction_proba, Union [list, np.ndarray]) and len(prediction_proba) == 3\
        and isinstance(prediction_proba[0], Union[float, np.float32])\
        and isinstance(prediction_proba[1], Union[float, np.float32])\
        and isinstance(prediction_proba[2], Union[float, np.float32])\
        and isinstance(base64_enc_class_activation_map, str):
        return prediction_proba, predicted_cls, base64_enc_class_activation_map
    else:
        message = "Unexpected prediction values"
        raise HTTPException(status_code=status.HTTP_417_EXPECTATION_FAILED,
                            detail=message)