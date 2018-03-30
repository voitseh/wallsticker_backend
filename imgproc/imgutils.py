'''
import numpy as np
import cv2
import math

def grayscale(img):
    return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

def gaussian_blur(img, kernel_size, sigma=1):    
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)


def canny(img, low_threshold, high_threshold):
    return cv2.Canny(img, low_threshold, high_threshold)


def find_countours(thresholded):
    image, countours, hierarchies = cv2.findContours(
        thresholded, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    return countours


def resize(image, newsize):
    return cv2.resize(image, (newsize), interpolation=cv2.INTER_CUBIC)


def resizeWithPadding(image, center, newsize):
    h, w = image.shape[:2]
    target_h, target_w = newsize
    x, y = center  
    y_offset = int( y - h / 2)
    x_offset = int( x - w / 2)
    
    w_offset = target_h - y_offset - h
    h_offset = target_w - x_offset - w
    
    w_offset += target_w - w_offset - x_offset - w
    h_offset += target_h - h_offset - y_offset - h
    
    result = cv2.copyMakeBorder(image,y_offset, h_offset, x_offset, w_offset,cv2.BORDER_CONSTANT,value=[0,0,0])
    return result


def scaleImage(image, scale=1.0):
    h, w = image.shape[:2]
    return resize(image, (int(w * scale), int(h * scale)))


def get_bound_box(cont):
    return cv2.minAreaRect(cont) #center (x,y), (width, height), angle of rotation

def draw_image(source, image, x, y):
    h,w  = image.shape[:2]    
    
    max_x, max_y = x + w, y + h    
    
    if image.shape[2] < 4:
        return source
    
    alpha = image[:, :, 3] / 255.0
    for c in range(0, 3):
        color = image[:, :, c] * (alpha)
        beta = source[y:max_y, x:max_x, c] * (1.0 - alpha)
        source[y:max_y, x:max_x, c] = color + beta
    return source


def process_image(image):
    gray = grayscale(image)

    #equ = cv2.equalizeHist(gray)
    edges = canny(gray, 0, 255)

    se = np.ones((15,15),np.uint8)    
    dilated = cv2.dilate(edges, se, iterations=1)

    h, w = dilated.shape[:2]
    dilated[:, 1], dilated[1, :] = 255, 255
    dilated[:, w - 1], dilated[h - 1, :] = 255, 255
    return dilated

def find_wall(mask):
    contours = find_countours(mask.copy())    
    h, w = mask.shape[:2]
    overlay_mask = np.zeros((h,w), dtype=np.uint8)
    
    max_area = 0
    max_cont = None
    for cont in contours:
        ar = cv2.contourArea(cont)
        if ar > max_area:
            max_area = ar
            max_cont = cont  
     
    bounding_box = None
    if max_cont is not None:
        cv2.fillPoly(overlay_mask,[max_cont], color=(255,255,255))
        bounding_box = get_bound_box(max_cont)
    else:
        overlay_mask = mask
   
    ret, threshold = cv2.threshold(overlay_mask, 127, 255, cv2.THRESH_BINARY)    
    return threshold, bounding_box

def try_find_wall(mask):
    kernel = np.ones((9,9),np.uint8)    
    mask = cv2.dilate(mask, kernel, iterations=2)
    mask = 255 - mask
    
    return find_wall(mask)    
    

def fill_small_contours(mask):    
    contours = find_countours(mask.copy())    
    h, w = mask.shape[:2]
    overlay_mask = np.zeros((h,w), dtype=np.uint8)
        
    max_area = w * h/ 2
    for cont in contours:
        ar = cv2.contourArea(cont)
        if ar < max_area:
            cv2.fillPoly(overlay_mask,[cont], color=(255,255,255))          
        
    overlay_mask = mask + overlay_mask
    
    ret, threshold = cv2.threshold(overlay_mask, 127, 255, cv2.THRESH_BINARY)  
    return threshold

def draw_sticker(image, sticker, mask, wall_bound_box):
    sh, sw = sticker.shape[:2]
    imgh, imgw = image.shape[:2]
    x, y = wall_bound_box[0]
    wallw, wallh =  wall_bound_box[1]

    
    sticker = scaleImage(sticker, min(float(wallh)/sh, float(wallw)/sw))
   
    sticker_padded = resizeWithPadding(sticker, wall_bound_box[0], mask.shape)
    print (sticker_padded.shape, mask.shape)
    colored_mask = cv2.bitwise_and(sticker_padded,sticker_padded,mask=mask) 
    
    result = image.copy()
    draw_image(result, colored_mask, 0, 0)
    return result

def apply_sticker_with_mask(image, sticker, mask): 
    temp = 255 - mask
    wall_mask, bound_box = find_wall(temp)
    return draw_sticker(image, sticker, mask, bound_box)


def apply_sticker(image, sticker):
    mask = process_image(image) 
    
    min_contours = fill_small_contours(mask)
    
    wall_mask, bound_box = try_find_wall(min_contours)
       
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(9,9))
    wall_mask = cv2.dilate(wall_mask, kernel, iterations=3)
  
    wall_mask = gaussian_blur(wall_mask, 17, 5)
    ret, mask = cv2.threshold(wall_mask, 127, 255, cv2.THRESH_BINARY) 

    return draw_sticker(image, sticker, mask, bound_box), mask

def process(wall_file, sticker_file, mask_file=None):
    wall = cv2.imread(wall_file, cv2.IMREAD_COLOR)
    sticker = cv2.imread(sticker_file, -1)
    
    result, mask = None, None
    if mask_file is None:
        result, mask = apply_sticker(wall, sticker)        
    else:
        mask = cv2.imread(mask_file, -1)
        if mask.shape[2] > 3:
            mask = mask[:, :, 3] 
        else:
            mask = grayscale(mask)
            ret, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        result = apply_sticker_with_mask(wall, sticker, mask)
        
    return result, mask
'''