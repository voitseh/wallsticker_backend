import uuid
import cv2
import  base64 
from PIL import Image
from imgproc import imgproc as impr



def decode_img_and_save_to_folder(b64file, img_path):
    if ',' in b64file:
        imgdata = b64file.split(',')[1]
        decoded = base64.b64decode(imgdata)
        write_file(img_path, decoded)

def encode_img(filename):
    with open(filename, "rb") as image_file:
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
    black_to_transparent(mask_path)
    

def black_to_transparent(file_name):
    src = cv2.imread(file_name, 1)
    tmp = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    _,alpha = cv2.threshold(tmp,0,255,cv2.THRESH_BINARY)
    b, g, r = cv2.split(src)
    rgba = [b,g,r, alpha]
    dst = cv2.merge(rgba,4)
    cv2.imwrite(file_name, dst)


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

