import cv2
import uuid
import os

import numpy as np
import math


def merge(wall, sticker, mask, result_name, sticker_place, rx, ry, alpha, path):
    if not os.path.exists(wall) or not os.path.exists(sticker):
        raise ValueError("Wall image of Sticker image not exists")
    print (alpha)
    result, mask = apply(wall, sticker, mask, sticker_place, rx, ry, alpha)
    # print('Alpha:', alpha)

    if not os.path.exists(path):
        os.makedirs(path)

    if result_name == '':
        # resPath = os.path.join(
        #     path, 'result-' + str(uuid.uuid4()) + '.jpg')
        raise ValueError("Result name is empty")
    else:
        resPath = os.path.join(path, result_name + '.jpg')
    if os.path.exists(resPath):
        os.remove(resPath)

    cv2.imwrite(resPath, result)
    return resPath

# CODE ****************


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

    if (h > target_h or w > target_w):
        print("Sticker size bigger than image")
        y_offset, x_offset, w_offset, h_offset = 0, 0
        image = resize(image, (target_h, target_w))
        return image
    else:
        y_offset = max(int(y - (h / 2)), 0)
        x_offset = max(int(x - (w / 2)), 0)

        h_offset = max(target_h - y_offset - h, 0)
        w_offset = max(target_w - x_offset - w, 0)

    result = cv2.copyMakeBorder(
        image, y_offset, h_offset, x_offset, w_offset, cv2.BORDER_CONSTANT, value=[0, 0, 0])
    return result


def scaleImage(image, scale=1.0):
    h, w = image.shape[:2]
    return resize(image, (int(w * scale), int(h * scale)))


def get_bound_box(cont):
    # center (x,y), (width, height), angle of rotation
    return cv2.minAreaRect(cont)


def convert_to_bounding_box(rect):
    if len(rect) < 3:
        return None
    w, h = abs(rect[1] - rect[0]), rect[2]
    x, y = (rect[0] + int(w / 2)), int(h / 2)
    return [(x, y), (h, w)]


def distanceP2P(a, b):  # measures distance between two points
    return ((a[0] - b[0])**2 + (a[1] - b[1])**2)**0.5


def largestRectangleAreaBestFit(mask):
    height = np.argmax(mask, axis=0)
    maxfit, maxarea = [], 0

    n = len(height)
    step = int(n / 4)

    for i in range(step, n - step):
        min = height[i]
        for j in range(i,  n - step):
            if height[j] < min:
                min = height[j]
            curr_area = min * (j - i + 1)

            if curr_area > maxarea:
                maxarea, maxfit = curr_area, [i, j, min]

    return convert_to_bounding_box(maxfit)


def draw_image(source, image, x, y, opacity=1.0):

    h,w  = image.shape[:2]    
    
    max_x, max_y = x + w, y + h    
    
    alpha = None
    if len(image.shape) < 3 or image.shape[2] < 4:
        if (len(image.shape) == 2):
            alpha = np.float32(image > 0)
        else:
            alpha = np.float32(image[:, :, 0] > 0)
    else:
        alpha = image[:, :, 3] / 255.0 

    alpha = alpha * min(1.0, max(opacity, 0.0))  

    for c in range(0,3):
        color = image[:, :, c] * (alpha)
        beta = source[y:max_y, x:max_x, c] * (1.0 - alpha)
        source[y:max_y, x:max_x, c] = color + beta
    return source


def make_sharpen(image, max_sharpen=3000):
    blur_amount = variance_of_laplacian(image)

    res = image.copy()
    while blur_amount < max_sharpen:
        alpha = min(
            1, max(float((max_sharpen - blur_amount)) / 22 / blur_amount, 0))
        res = sharpen(res, alpha, 1.0)
        blur_amount = variance_of_laplacian(res)

        if alpha < 0.01:
            break

    return res


def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0], rect[2] = pts[np.argmin(s)], pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1], rect[3] = pts[np.argmin(diff)], pts[np.argmax(diff)]
    return rect


def four_point_transform(pts):

    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))

    dst = np.float32(
        [[0, 0], [maxWidth, 0], [maxWidth, maxHeight], [0, maxHeight]])
    if (dst == rect).all():
        return None
    inverseM = cv2.getPerspectiveTransform(dst, rect)

    return inverseM


def variance_of_laplacian(image):
    return cv2.Laplacian(image, cv2.CV_64F).var()


def sharpen(image, alpha=1.0, strength=1.0):
    matrix_no_change = np.float32([[0, 0, 0], [0, 1, 0], [0, 0, 0]])
    matrix_effect = np.float32(
        [[-1, -1, -1], [-1, 8 + strength, -1], [-1, -1, -1]])

    matrix = (1 - alpha) * matrix_no_change + alpha * matrix_effect
    result = cv2.filter2D(image, -1, matrix)
    return result


def get_polygon(cont):
    coef = 0.01
    len_points, approx = 0, None
    while len_points != 4:
        epsilon = coef * cv2.arcLength(cont, True)
        approx = cv2.approxPolyDP(cont, epsilon, True)
        len_points = len(approx)
        if (coef > 0.2):
            break
        coef += 0.01

    return approx


def process_image(image):
    sharped = make_sharpen(image)
    gray = grayscale(sharped)

    edges = canny(gray, 0, 255)

    se = np.ones((15, 15), np.uint8)
    dilated = cv2.dilate(edges, se, iterations=1)

    h, w = dilated.shape[:2]
    dilated[:, 1], dilated[1, :] = 255, 255
    dilated[:, w - 1], dilated[h - 1, :] = 255, 255

    return dilated


def find_wall(mask):
    contours = find_countours(mask.copy())
    overlay_mask = np.zeros(mask.shape[:2], dtype=np.uint8)

    max_area, max_cont = 0, None
    for cont in contours:
        ar = cv2.contourArea(cont)
        if ar > max_area:
            max_area, max_cont = ar, cont

    bounding_box, perspective_matrix = None, None
    if max_cont is not None:
        cv2.fillPoly(overlay_mask, [max_cont], color=(255, 255, 255))
        bounding_box = get_bound_box(max_cont)

        polygon = get_polygon(max_cont)
        perspective_matrix = None
        if (len(polygon) == 4):
            perspective_matrix = four_point_transform(polygon.reshape((4, 2)))
    else:
        overlay_mask = mask

    ret, threshold = cv2.threshold(overlay_mask, 127, 255, cv2.THRESH_BINARY)
    return threshold, bounding_box, perspective_matrix


def find_small_contours(mask):
    contours = find_countours(mask.copy())
    h, w = mask.shape[:2]
    overlay_mask = np.zeros((h, w), dtype=np.uint8)

    max_area = w * h / 2
    for cont in contours:
        ar = cv2.contourArea(cont)
        if ar < max_area:
            cv2.fillPoly(overlay_mask, [cont], color=(255, 255, 255))

    overlay_mask = mask + overlay_mask

    ret, threshold = cv2.threshold(overlay_mask, 127, 255, cv2.THRESH_BINARY)
    return threshold


def tile_sticker(sticker, rx, ry, wall_bound_box):
    wallh, wallw =  wall_bound_box

    possible_rx = int((float(wallw) / sticker.shape[1])) + 1
    possible_ry = int((float(wallh) / sticker.shape[0])) + 1
   
    
    if (rx > 1):
        rx = max(possible_rx, rx)
        ry = possible_ry
    elif ry > 1:
        rx = possible_rx
        ry = max(possible_ry, ry)
    
    newsticker = sticker.copy()
    for i in range(rx - 1):
        sticker = np.hstack((sticker, newsticker))

    wsticker = sticker.copy()
    for i in range(ry - 1):
        sticker = np.vstack((sticker, wsticker))

    return sticker


def draw_sticker(image, sticker, mask, wall_bound_box, repeat_x=1, repeat_y=1, perspective_matrix=None, opacity = 1.0):
    sh, sw = sticker.shape[:2]
    imgh, imgw = image.shape[:2]
    x, y = wall_bound_box[0]
    wallh, wallw = wall_bound_box[1]

    # possible problem with bound box rotation
    if wallh > image.shape[0]:
        wallw, wallh = wallh, wallw

    scale_ratio = min(float(wallw / repeat_x) / sw,
                      float(wallh / repeat_y) / sh)

    tile_mode = repeat_x > 1 or repeat_y > 1
    scaler = 1.0 if tile_mode else 0.95
    sticker = scaleImage(sticker, scale_ratio * scaler)

    if tile_mode:
        sticker = tile_sticker(sticker, repeat_x, repeat_y, (wallh, wallw))

    sticker = sticker[:int(wallh), :int(wallw)]
    sticker_padded = resizeWithPadding(sticker, wall_bound_box[0], mask.shape)

    #if perspective_matrix is not None:
        #sticker_padded = cv2.warpPerspective(sticker_padded, perspective_matrix, ( mask.shape[1],mask.shape[0] ))
        
    colored_mask = cv2.bitwise_and(sticker_padded,sticker_padded,mask=mask) 
    

    result = image.copy()
    draw_image(result, colored_mask, 0, 0, opacity)
    return result


def validate_placement(placement_default, rx, ry):
    if ry > 1:
        rx, placement_default = 1, True
    elif ry <= 0:
        ry = 1

    if rx > 1:
        ry, placement_default = 1, True
    elif rx <= 0:
        rx = 1

    if not placement_default:
        rx, ry = 1, 1

    return placement_default, rx, ry


def generate_mask(image):
    mask = process_image(image)

    min_contours = find_small_contours(mask)

    wall_mask, bound_box, contour = find_wall(255 - mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    wall_mask = cv2.dilate(wall_mask, kernel, iterations=3)

    wall_mask = gaussian_blur(wall_mask, 17, 5)
    ret, mask = cv2.threshold(wall_mask, 127, 255, cv2.THRESH_BINARY)
    return mask, bound_box, contour


def apply_sticker_with_mask(image, sticker, mask, placement_default=True, repeat_x=1, repeat_y=1, opacity = 1.0):
    wall_mask, bound_box, perspective_matrix = find_wall(mask)

    placement_default, repeat_x, repeat_y = validate_placement(
        placement_default, repeat_x, repeat_y)

    if not placement_default:
        max_fit_bb = largestRectangleAreaBestFit((255 - mask))
        if max_fit_bb is not None:
            bound_box = max_fit_bb

    return draw_sticker(image, sticker, mask, bound_box, repeat_x, repeat_y, perspective_matrix, opacity)


def apply_sticker(image, sticker, placement_default=True, repeat_x=1, repeat_y=1, opacity = 1.0):
    mask, bound_box, perspective_matrix = generate_mask(image)
    placement_default, repeat_x, repeat_y = validate_placement(
        placement_default, repeat_x, repeat_y)

    if not placement_default:
        max_fit_bb = largestRectangleAreaBestFit((255 - mask))
        if max_fit_bb is not None:
            bound_box = max_fit_bb

    return draw_sticker(image, sticker, mask, bound_box, repeat_x, repeat_y, perspective_matrix, opacity), mask


def apply(wall_file, sticker_file, mask_file=None, placement_default=True, repeat_x=1, repeat_y=1, opacity = 1.0):
    wall = cv2.imread(wall_file, cv2.IMREAD_COLOR)
    sticker = cv2.imread(sticker_file, -1)
    result, mask = None, None
    if mask_file is None or not os.path.exists(mask_file):
        result, mask = apply_sticker(
            wall, sticker, placement_default, repeat_x, repeat_y, opacity)
    else:
        mask = cv2.imread(mask_file, -1)
        if mask.shape[:2] != wall.shape[:2]:
            result, mask = apply_sticker(
                wall, sticker, placement_default, repeat_x, repeat_y, opacity)
        else:
            if mask.shape[2] > 3:
                mask = mask[:, :, 3]
            else:
                mask = grayscale(mask)
                ret, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

            result = apply_sticker_with_mask(
                wall, sticker, mask, placement_default, repeat_x, repeat_y, opacity)

    return result, mask
