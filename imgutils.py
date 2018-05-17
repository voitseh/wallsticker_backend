import uuid
import cv2
import  base64 
import utils
import numpy as np
from PIL import Image
from wand.image import Image as wandImage
from imgproc import imgproc as impr




def decode_img_and_save_to_folder(b64file, img_path):
    if ',' in b64file:
        imgdata = b64file.split(',')[1]
        decoded = base64.b64decode(imgdata)
        utils.write_file(img_path, decoded)

def encode_img(file_path):
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    encoded_string = str(encoded_string).split("b'")[-1].split("b'")[-1][:-1]
    encoded_string = 'data:image/png;base64,{}'.format(encoded_string)
    return encoded_string
 

def make_and_save_thumbnail(native_file_path, file_thumbnail_path):
    thumbnail_size = (300,300)
    im = Image.open(native_file_path)
    im.thumbnail(thumbnail_size,  Image.ANTIALIAS)
    im.save(file_thumbnail_path)

def process_mask(img_path, mask_path):
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)
    mask, bound_box, contour = impr.generate_mask(img)
    cv2.imwrite(mask_path, mask)
    
    

def black_to_transparent(src_path, dest_path):
    src = cv2.imread(src_path, 1)
    tmp = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    _,alpha = cv2.threshold(tmp,0,255,cv2.THRESH_BINARY)
    b, g, r = cv2.split(src)
    rgba = [b,g,r, alpha]
    dst = cv2.merge(rgba,4)
    cv2.imwrite(dest_path, dst)

def transparent_to_black(file_path):
    img = cv2.imread(file_path, -1)
    result = remove_transparency(img, 0)
    
    cv2.imwrite(file_path, result)

def remove_transparency(source, background_color):
    source_img = cv2.cvtColor(source[:,:,:3], cv2.COLOR_BGR2GRAY)
    source_mask = source[:,:,3]  * (1 / 255.0)

    background_mask = 1.0 - source_mask

    bg_part = (background_color * (1 / 255.0)) * (background_mask)
    source_part = (source_img * (1 / 255.0)) * (source_mask)

    return np.uint8(cv2.addWeighted(bg_part, 255.0, source_part, 255.0, 0.0))

def process_automode_img(automode_files, automode_settings, dest_folder):
    
    sticker_place = False
    rx, ry = 1, 1
    alpha = 1.0
    if automode_settings['sticker_center']:
        sticker_place = True
    if automode_settings['repeat_x']:
        rx = int(automode_settings['repeat_x'])
    if automode_settings['repeat_y']:
        ry = int(automode_settings['repeat_y'])
    if automode_settings['opacity']:
        alpha = float(automode_settings['opacity'])
    
    result_name = 'result-' + str(uuid.uuid4())
    result_img_path = impr.merge(automode_files['wallFilePath'], automode_files['stickerFilePath'], automode_files['maskFilePath'],
                            result_name, sticker_place, rx, ry, alpha, dest_folder)
    return result_img_path

