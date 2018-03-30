from flask import Flask, g, url_for
from flask_cors import CORS
from flask import render_template
import uuid
import flask_sijax
import os, glob
from imgproc import imgproc as impr
from threading import Timer
import  base64 
import cv2
import numpy as np
import logging

# The path where you want the extension to create the needed javascript files
# DON'T put any of your files in this directory, because they'll be deleted!
path = os.path.join('.', os.path.dirname(__file__), 'static/js/sijax/')

app = Flask(__name__)
CORS(app)
app.config['SIJAX_STATIC_PATH'] = path
# You need to point Sijax to the json2.js library if you want to support
# browsers that don't support JSON natively (like IE <= 7)
app.config['SIJAX_JSON_URI'] = '/static/js/sijax/json2.js'
flask_sijax.Sijax(app)

APP_ROOT = "/home/voitseh/Projects/wallsticker"
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/images')
WALL_FOLDER = os.path.join(UPLOAD_FOLDER, 'wall_gallery')
STICKER_FOLDER = os.path.join(UPLOAD_FOLDER, 'sticker_gallery')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024

curFrame = None
gallery_ID = ""

# temporary filenames for top galleries auto editing
wallFile = ""
stickerFile = ""

sticker_center = False
repeat_x = None
repeat_y = None
opacity = None

filenames_list = []

class Frame:
    def __init__(self,id):
        self.id = id
        self.items = {'wallFile':'', 'maskFile':'','stickerFile':''}


#################### PROCESS IMAGE ###############################
def b64file_extension(b64file):
    ext = b64file.split(',')[0].split('/')[1].split(';')[0]
    return ext

def decode_img(b64file, f_name):
    if ',' in b64file:
        imgdata = b64file.split(',')[1]
        decoded = base64.b64decode(imgdata)
        write_file(f_name, decoded)

def encode_img(filename):
    with open(filename, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    return encoded_string

def process_base64(filename):
    filename = str(filename).split("b'")[-1].split("b'")[-1][:-1]
    filename = 'data:image/png;base64,{}'.format(filename)
    return filename

def autoEditTopGaleryImgs(obj_response, wallFile, stickerFile):
    # auto edit images from top galleries  
    if wallFile != "" and stickerFile != "":
        process(obj_response, wallFile, stickerFile);

def autoEditBottomGaleryImgs(obj_response, curFrame):
    # auto edit images from bottom gallery
    if curFrame != None:
        if  curFrame.items['wallFile'] != '' and curFrame.items['stickerFile'] != '':
            remove_img(obj_response, 'theImg')
            process(obj_response, curFrame.items['wallFile'], curFrame.items['stickerFile'], curFrame.items['maskFile']);
            

#################### UTILS ###############################
def save_file(file,filename):
    file.save(filename)
  
def rename_file(folder, prefix, file_ext):
    filename = os.path.join(folder, prefix + str(uuid.uuid4())+ '.{}'.format(file_ext))
    return filename

def remove_file(filename, default_folder = app.config['UPLOAD_FOLDER']):
    filepath = os.path.join(default_folder,filename)
    if os.path.isfile(filepath):
        os.remove(filepath)

def remove_files(file_dict):
    for key, value in file_dict.items():
        remove_file(value)

def write_file(f_name, file):
    with open(f_name, 'wb') as f:
        f.write(file)

#################### FOR BOTTOM GALLERY IMAGES AND LARGE IMAGE ###############################
def remove_img(obj_response, img_id):
    obj_response.script("$('#%s').remove()"%(img_id));

def show_img(obj_response, parent_id, img_id, new_img):
    #global native_img_dimensions
    # process base64 image to be readeble in browser
    new_img = process_base64(new_img)
    obj_response.script("$('#%s').append($('<img>',{ style:'position:absolute; left:0px; top:0px; z-index: 2', name:'bottom_gallery' ,id:'%s',src:'%s'}));"%(parent_id, img_id, new_img))
   
def change_img(obj_response, parent_id, img_id, new_img):
    #remove previous image from gallery
    if img_id != None:
        remove_img(obj_response, img_id);
    #send new image to frame
    show_img(obj_response, parent_id, img_id, new_img)
   
def response(obj_response, parent_id, img_id, filename):
    #global native_img_dimensions
    #native_img_dimensions = get_img_native_dimensions(filename)
    new_img = encode_img(filename)
    change_img(obj_response, parent_id, img_id, new_img)
    filenames_list.append(filename)
   
    
###################### GALLERIES ##############################
def remove_gallery_imgs(obj_response, parent_id):
    obj_response.script("$('#%s').children().remove()"%(parent_id));

def show_gallery_img(obj_response, parent_id, img_id, new_img, del_id):
    img_name = new_img.split('wall_gallery/')[-1]  if gallery_ID == 'wall_gallery' else new_img.split('sticker_gallery')[-1]
    file_address = UPLOAD_FOLDER + new_img.split('images')[-1]
    new_img = encode_img(file_address)
    new_img = process_base64(new_img)
    obj_response.script("$('#%s').append($('<li>',{class:'image_grid'}).append($('<a href=#>').append($('<label>').append($('<img>',{id:'%s', src:'%s', name:'%s'})).append($('<input>',{type:'radio', name:'selimg'})).append($('<span>',{class:'caption'})).append($('<span>',{id:'%s'})))));"%(parent_id, img_id, new_img, img_name, del_id))
   
def response_to_gallery(obj_response, parent_id, img_id, filename, del_id):
    filename = filename.split('/')[-1]
    result = url_for('static', filename='images/{}/{}'.format(parent_id,filename))
    show_gallery_img(obj_response, parent_id, img_id, result, del_id) 

def fill_gallery(obj_response, src_dir, gallery_ID):
    index = 0
    remove_gallery_imgs(obj_response, gallery_ID)
    if os.path.exists(src_dir):
        for filename in glob.glob(os.path.join( src_dir, "*.*")):
            img_id = '_img{}'.format(str(index))
            del_id = 'del_wall{}'.format(str(index)) if gallery_ID == 'wall_gallery' else 'del_sticker{}'.format(str(index))
            index += 1
            #senf new image to frame
            response_to_gallery(obj_response, gallery_ID, img_id, filename, del_id) 
    else: 
         print("{} is not exist!".format(src_dir))

################# RESPONSE MASK ########################
def black_to_transparent(file_name):
    src = cv2.imread(file_name, 1)
    tmp = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    _,alpha = cv2.threshold(tmp,0,255,cv2.THRESH_BINARY)
    b, g, r = cv2.split(src)
    rgba = [b,g,r, alpha]
    dst = cv2.merge(rgba,4)
    cv2.imwrite(file_name, dst)

def send_wall_mask(obj_response, wall_path):
    wall = cv2.imread(wall_path, cv2.IMREAD_COLOR)
    mask, bound_box, contour = impr.generate_mask(wall)
    mask_path = os.path.join(UPLOAD_FOLDER, 'mask-' + str(uuid.uuid4())+ '.png')
    cv2.imwrite(mask_path, mask)
    black_to_transparent(mask_path)
    mask_img = encode_img(mask_path)
    mask_img = process_base64(mask_img)
    obj_response.script("$(mask).attr('src','%s');"%mask_img)
    timer = Timer(7, remove_file, [mask_path.split('images/')[-1]])
    timer.start()
    
# save inputed Wall or Sticker files before response it to gaLLery
def save_to_subfolder(file, gallery_ID):
    if not os.path.exists(WALL_FOLDER):
        os.makedirs(WALL_FOLDER)
    if not os.path.exists(STICKER_FOLDER):
        os.makedirs(STICKER_FOLDER)
    file_ext = file.split('.')[-1]
    if gallery_ID == 'wall_gallery':
        filename = rename_file(WALL_FOLDER, 'wall-', file_ext)
        save_file(file,filename)
    else:
        filename = rename_file(STICKER_FOLDER, 'sticker-', file_ext)
        save_file(file,filename)

class SijaxHandler(object):
    
    """A container class for all Sijax handlers.
    Grouping all Sijax handler functions in a class
    (or a Python module) allows them all to be registered with
    a single line of code.
    """
    # data from current Frame object
    @staticmethod
    def client_data(obj_response, client_data):
        global  clickedBttnName, gallery_ID, wallFile, stickerFile, curFrame, sticker_center,repeat_x,repeat_y,opacity
        # handle adding new bottom gallery frame
        if  'lastFrameId' in client_data:
            lastFrameId = client_data['lastFrameId']
            curFrame = Frame(lastFrameId)
        
        # handle current frame id 
        if  'curFrameId' in client_data:
            curFrame.id = client_data['curFrameId']
        
        # handle deleted top gallery image
        if  'delGalleryImg' in client_data:
            filename = client_data['delGalleryImg']
            remove_file(filename, WALL_FOLDER) if gallery_ID == 'wall_gallery' else remove_file(filename.split('/')[-1], STICKER_FOLDER)
        
        # handle Wall || Sticker gallery checked Event to fill appropriate gallery
        if  'wall_gallery' in client_data:
            gallery_ID = client_data['wall_gallery']
            fill_gallery(obj_response, WALL_FOLDER, gallery_ID)
           
        if  'sticker_gallery' in client_data:
            gallery_ID = client_data['sticker_gallery']
            fill_gallery(obj_response, STICKER_FOLDER, gallery_ID)
    
        # handle needed mask for wall gallery image
        if 'wall_mask' in client_data:
            wall_path = os.path.join(WALL_FOLDER, client_data['wall_mask'])
            send_wall_mask(obj_response, wall_path)
            # uses for top galleries images editing with auto mode
            wallFile = wall_path
        
        if 'sticker' in client_data:
            #stickerFile = os.path.join(STICKER_FOLDER, client_data['sticker'] )
            stickerFile = STICKER_FOLDER + client_data['sticker']
        
        
        ############## dump files data ########################
        # handle wallFile, stickerFile or maskFile loading in frame (bottom gallery)
        if 'Wall' in client_data:
            file_ext = b64file_extension(client_data['Wall'])
            f_name = rename_file(UPLOAD_FOLDER, 'wall-', file_ext)
            decode_img(client_data['Wall'], f_name)
            curFrame.items['wallFile'] = f_name
            response(obj_response, curFrame.id, 'img{}'.format(curFrame.id), curFrame.items['wallFile'])
            
        if 'Mask' in client_data:
            file_ext = b64file_extension(client_data['Mask'])
            f_name = rename_file(UPLOAD_FOLDER, 'mask-', file_ext)
            decode_img(client_data['Mask'], f_name)
            curFrame.items['maskFile'] = f_name
            response(obj_response, curFrame.id, 'img{}'.format(curFrame.id), curFrame.items['maskFile'])
            
        if 'Sticker' in client_data:
            file_ext = b64file_extension(client_data['Sticker'])
            f_name = rename_file(UPLOAD_FOLDER, 'sticker-', file_ext)
            decode_img(client_data['Sticker'], f_name)
            curFrame.items['stickerFile'] = f_name
            response(obj_response, curFrame.id, 'img{}'.format(curFrame.id), curFrame.items['stickerFile'])
    
        ############## top galleries ###############################
        # handle loading new Wall file to send it into Wall gallery
        if 'wallFile' in client_data:
            file_ext = b64file_extension(client_data['wallFile'])
            f_name = rename_file(WALL_FOLDER, 'wall-', file_ext)
            decode_img(client_data['wallFile'], f_name)
            gallery_ID = 'wall_gallery'
            fill_gallery(obj_response, WALL_FOLDER, gallery_ID)
        
        # handle loading new Sticker file to send it into Sticker gallery 
        if 'stickerFile' in client_data:
            file_ext = b64file_extension(client_data['stickerFile'])
            f_name = rename_file(STICKER_FOLDER, 'sticker-', file_ext)
            decode_img(client_data['stickerFile'], f_name)
            gallery_ID = 'sticker_gallery'
            fill_gallery(obj_response, STICKER_FOLDER, gallery_ID)


        # apply result images from bottom gallery into UPLOAD_FOLDER
        if 'imagesDict' in client_data:
            for img_item in client_data['imagesDict']:
                if img_item != None:
                    if '_result' in img_item and img_item['_result'] != "":
                        file_ext = b64file_extension(img_item['_result'])
                        f_name = rename_file(UPLOAD_FOLDER, 'result-', file_ext)
                        decode_img(img_item['_result'], f_name)
        
        ########## dump auto form_values data #####################
        # handle form values change in auto mode form
        if 'sticker_center' in client_data:   
            sticker_center = client_data['sticker_center']
            autoEditTopGaleryImgs(obj_response, wallFile, stickerFile)
            autoEditBottomGaleryImgs(obj_response, curFrame)
            
        if 'repeat_x' in client_data: 
            repeat_x = client_data['repeat_x']
            #autoEditTopGaleryImgs(obj_response, wallFile, stickerFile)
            #autoEditBottomGaleryImgs(obj_response, curFrame)
        
        if 'repeat_y' in client_data:
            repeat_y = client_data['repeat_y']
            autoEditTopGaleryImgs(obj_response, wallFile, stickerFile)
            autoEditBottomGaleryImgs(obj_response, curFrame)
        
        if 'opacity' in client_data: 
            opacity = client_data['opacity']
            autoEditTopGaleryImgs(obj_response, wallFile, stickerFile)
            autoEditBottomGaleryImgs(obj_response, curFrame)
        
        if 'edited_and_pushed' in client_data:
            if client_data['edited_and_pushed'] == 'true':
                for f_name in filenames_list:
                    remove_file(f_name)
                del filenames_list[:]
                #remove_files(curFrame.items)
                curFrame.items['wallFile'] = ''
                curFrame.items['stickerFile'] = ''
                curFrame.items['maskFile'] = ''
                wallFile = ''
                stickerFile = ''
                client_data['edited_and_pushed'] = 'false'
                sticker_center = None
                repeat_x = None
                repeat_y = None
                opacity = None

@flask_sijax.route(app, "/")
def index():
    
    if g.sijax.is_sijax_request:
        # Sijax request detected - let Sijax handle it
        g.sijax.register_callback('client_data', SijaxHandler.client_data) 
        # The request looks like a valid Sijax request
        # The handlers are already registered above.. we can process the request
        return g.sijax.process_request()
    return render_template(index.html)
 

def process(obj_response, wallFile, stickerFile, maskFile = None):
    global sticker_center, repeat_x, repeat_y, opacity
    sticker_place = False
    rx, ry = 1, 1
    alpha = 1.0
    if sticker_center:
        print('sticker_center: ', sticker_center)
        sticker_place = True
    if repeat_x:
        print('repx', repeat_x )
        rx = int(repeat_x)
    if repeat_y:
        print('repy', repeat_y )
        ry = int(repeat_y)
    if opacity:
        print('opacity: ', opacity)
        alpha = float(opacity)
  
    result_name = 'result-' + str(uuid.uuid4())
    result = impr.merge(wallFile, stickerFile, maskFile,
                        result_name, sticker_place, rx, ry, alpha, UPLOAD_FOLDER)
    response(obj_response, 'formCanvasResponse','theImg', result)
   
    tmp = os.path.join(app.root_path, result) 
    # remove tmp files
    tmp = os.path.join(app.root_path, result) 
    timer = Timer(5, remove_file, [tmp])
    timer.start()
    
@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=63100, debug=True)



