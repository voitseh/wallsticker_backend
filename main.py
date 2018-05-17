import flask_sijax
import os, glob
import utils
import imgutils
import logging
from flask import Flask, g
from flask_cors import CORS
from gevent.wsgi import WSGIServer
from flask import render_template
from os.path import exists

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

UPLOAD_FOLDER = os.path.join(app.root_path, 'static/images')
WALL_FOLDER = os.path.join(UPLOAD_FOLDER, 'wall_gallery')
MASK_WITH_BLACK_FOLDER = os.path.join(UPLOAD_FOLDER, 'mask_black')
MASK_WITH_TRANSPARENT_FOLDER = os.path.join(UPLOAD_FOLDER, 'mask_transparent')
STICKER_FOLDER = os.path.join(UPLOAD_FOLDER, 'sticker_gallery')
WALL_THUMBNAILS = os.path.join(UPLOAD_FOLDER, 'wall_thumbnails')
STICKER_THUMBNAILS = os.path.join(UPLOAD_FOLDER, 'sticker_thumbnails')
TMP_FOLDER = os.path.join(UPLOAD_FOLDER, 'tmp')

automode_files = {'wallFilePath': None, 'maskFilePath': None, 'stickerFilePath': None}
automode_settings = {'sticker_center': False, 'repeat_x': None, 'repeat_y': None, 'opacity': None}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024

class GalleryManager:
   
    _img_name_prefix = ''

    _gallery_image_id_index = 0

    _gallery_img_thumb_path = ''

    _img_thumb_path = ''
   
    _loaded_img_path, _loaded_img_src, _loaded_img_thumb_path = '', '', ''

    _clicked_img_name, _clicked_img_path, _clicked_img_src = '', '', ''

    _deleted_img_name = ''

    
    def __init__(self, IMG_FOLDER, IMG_THUMBNAILS, gallery_id, img_id_prefix, delbttn_id_prefix, img_type):
        self._IMG_FOLDER, self._IMG_THUMBNAILS = IMG_FOLDER, IMG_THUMBNAILS
        self._gallery_id, self._img_id_prefix, self._delbttn_id_prefix, self.img_type = gallery_id, img_id_prefix, delbttn_id_prefix, img_type
        
       
    #####################################################################################
    def reload_gallery(self, obj_response):
        self.clear_gallery(obj_response)
        self.fill_gallery_with_images(obj_response)  
     
    def clear_gallery(self, obj_response):
        obj_response.script("$('#%s').children().remove()"%(self._gallery_id));
        
    def fill_gallery_with_images(self, obj_response):
        self._gallery_image_id_index = 0
        for img_thumb_path in glob.glob(os.path.join(self._IMG_THUMBNAILS, "*.*")):
            self._gallery_img_thumb_path = img_thumb_path
            self.__response_gallery_img(obj_response)
            self._gallery_image_id_index += 1

    def __response_gallery_img(self, obj_response):
        img_name, img_src, img_id, delbttn_id = self.__make_gallery_img_attrs()
        obj_response.script("$('#%s').append($('<li>',{class:'image_grid'}).append($('<a href=#>').append($('<label>',{id:'not_uploaded'}).append($('<img>',{id:'%s', src:'%s', name:'%s'})).append($('<input>',{type:'radio', name:'%s'})).append($('<span>',{class:'caption'})).append($('<span>',{id:'%s', src:''})))));"%(self._gallery_id, img_id, img_src, img_name, self._img_id_prefix , delbttn_id))

    def __make_gallery_img_attrs(self):
        img_name = self._gallery_img_thumb_path.split('/')[-1]
        img_src = imgutils.encode_img(self._gallery_img_thumb_path)
        img_id = '{}{}'.format(self._img_id_prefix, str(self._gallery_image_id_index))
        delbttn_id = '{}{}'.format(self._delbttn_id_prefix, str(self._gallery_image_id_index))
        return img_name, img_src, img_id, delbttn_id

    ########################################################################################
    def on_input_new_img_bttn_click(self, obj_response):
        self._gallery_image_id_index = utils.get_number_of_files_in_directory(self._IMG_FOLDER)
        self._loaded_img_path = self._create_img_path()
        self._loaded_img_thumb_path = self._create_img_thumb_path()
        imgutils.decode_img_and_save_to_folder(self._loaded_img_src, self._loaded_img_path)
        imgutils.make_and_save_thumbnail(self._loaded_img_path, self._loaded_img_thumb_path)
        self._gallery_img_thumb_path = self._loaded_img_thumb_path
        self.__response_gallery_img(obj_response)
        

    def _create_img_path(self):
        img_file_ext = utils.get_file_extension(self._loaded_img_src)
        img_name = utils.create_filename('{}-'.format(self._img_name_prefix), img_file_ext)
        return utils.create_filepath(self._IMG_FOLDER, img_name)
        
    def _create_img_thumb_path(self):
        return utils.create_filepath(self._IMG_THUMBNAILS, self._loaded_img_path.split('/')[-1])
        
    #########################################################################################
    def on_del_img_bttn_click(self):
        self.__del_img_from_folder()
        self.__del_img_thumb_from_folder()

    def __del_img_from_folder(self):
        img_path = os.path.join(self._IMG_FOLDER, self._deleted_img_name)
        utils.remove_file(img_path)

    def __del_img_thumb_from_folder(self):
        img_thumb_path = os.path.join(self._IMG_THUMBNAILS, self._deleted_img_name)
        utils.remove_file(img_thumb_path)

    ########################################################################################
    def on_img_clicked(self, obj_response):
        self._clicked_img_path = utils.create_filepath(self._IMG_FOLDER, self._clicked_img_name)
        self._clicked_img_src = imgutils.encode_img(self._clicked_img_path)
        self._send_img_to_canvas(obj_response)
       
    def _send_img_to_canvas(self, obj_response):
        obj_response.script("$(%s).attr('src','%s');"%(self.img_type, self._clicked_img_src))

    

class WallGalleryManager(GalleryManager):

    __wall_gallery_image_id_index = 0

    __custom_mask_name, __custom_mask_src, __custom_mask_id_index = '', '', ''
    __target_html_element_where_custom_mask_will_be_added_id = ''

    __tooltip_text_of_wall_where_custom_mask_loads = ''

    __common_substring_of_wall_and_appropriate_mask_names = ''

    def __init__(self):
        global WALL_FOLDER, WALL_THUMBNAILS, MASK_WITH_BLACK_FOLDER, MASK_WITH_TRANSPARENT_FOLDER
        self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type,  self._img_name_prefix = 'wall_gallery', '_wall', 'del_wall', 'image', 'wall'
        GalleryManager.__init__(self, WALL_FOLDER, WALL_THUMBNAILS, self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type)
        
    ###############################################################################################
    def reload_walls_and_masks_gallery(self, obj_response):
        super().clear_gallery(obj_response)
        self.__fill_gallery_with_walls(obj_response)
        self.__fill_gallery_with_masks(obj_response)

    def __fill_gallery_with_walls(self, obj_response):
        super().fill_gallery_with_images(obj_response)
    
    def __fill_gallery_with_masks(self, obj_response):
        self.__wall_gallery_image_id_index = 0
        for wall_thumb_path in glob.glob(os.path.join(self._IMG_THUMBNAILS, "*.*")):
            self._gallery_img_thumb_path = wall_thumb_path
            self.__response_appropriate_mask(obj_response)
            self.__wall_gallery_image_id_index += 1

   
    def __response_appropriate_mask(self, obj_response):
        appropriate_mask_src = self.__make_mask_src(MASK_WITH_BLACK_FOLDER)
        target_element_for_mask_adding_id = '{}{}'.format(self.__delbttn_id_prefix, self.__wall_gallery_image_id_index)
        obj_response.script("$('#%s').attr('src', '%s')"%(target_element_for_mask_adding_id, appropriate_mask_src))

    def __make_mask_src(self, mask_folder):
        mask_path = self.__get_mask_path(mask_folder)
        automode_files['wallMaskPath']  = mask_path
        mask_src = imgutils.encode_img(mask_path)
        return mask_src

    def __get_mask_path(self, mask_folder):
        self.__common_substring_of_wall_and_appropriate_mask_names = self._gallery_img_thumb_path.split('wall-')[-1].split('.')[0]
        if utils.find_file_in_folder_by_filename_substring(mask_folder, self.__common_substring_of_wall_and_appropriate_mask_names) != None:
            mask_path = utils.find_file_in_folder_by_filename_substring(mask_folder, self.__common_substring_of_wall_and_appropriate_mask_names)
        else:
            mask_name = 'mask-{}{}'.format(self.__common_substring_of_wall_and_appropriate_mask_names, '.png')
            mask_path = utils.create_filepath(mask_folder, mask_name)
            imgutils.process_mask(self._gallery_img_thumb_path, mask_path)
        return mask_path

    
    ##############################################################################################
    def on_input_new_wall_bttn_click(self,obj_response, wall_src):
        self._loaded_img_src = wall_src
        super().on_input_new_img_bttn_click(obj_response)
        self.__wall_gallery_image_id_index = self._gallery_image_id_index 
        self._gallery_img_thumb_path = self._loaded_img_thumb_path
        self.__response_appropriate_mask(obj_response)
        self.__create_mask_with_transparent()       
        
    def __create_mask_with_transparent(self):
        black_mask_path = self.__get_mask_path(MASK_WITH_BLACK_FOLDER)
        transparent_mask_path = utils.create_filepath(MASK_WITH_TRANSPARENT_FOLDER, black_mask_path.split('/')[-1])
        imgutils.black_to_transparent(black_mask_path, transparent_mask_path)


    ##############################################################################################
    def on_input_custom_mask_bttn_click(self,obj_response, custom_mask_data):
        self.__get_loaded_custom_mask_data(custom_mask_data)
        custom_mask_with_black_path = utils.create_filepath(MASK_WITH_BLACK_FOLDER, custom_mask_data[0])

        custom_mask_with_transparent_path = utils.create_filepath(MASK_WITH_TRANSPARENT_FOLDER, custom_mask_with_black_path.split('/')[-1])
        self.__delete_old_masks()
        
        imgutils.decode_img_and_save_to_folder(self.__custom_mask_src, custom_mask_with_transparent_path)
        imgutils.decode_img_and_save_to_folder(self.__custom_mask_src, custom_mask_with_black_path)
        imgutils.transparent_to_black(custom_mask_with_black_path)
        self.__custom_mask_src = imgutils.encode_img(custom_mask_with_black_path)
        self.__define_target_html_element_id_for_mask_adding()
        self.response_custom_mask(obj_response)  
           
    def __get_loaded_custom_mask_data(self, custom_mask_data):
        self.__custom_mask_name = custom_mask_data[0].split('.')[0]
        self.__custom_mask_src = custom_mask_data[1]
        self.__custom_mask_id_index = custom_mask_data[2]
        self.__tooltip_text_of_wall_in_which_custom_mask_loads = custom_mask_data[3]
        
    def __define_target_html_element_id_for_mask_adding(self):
        self.__target_html_element_where_custom_mask_will_be_added_id = '{}{}'.format(self.__img_id_prefix, self.__custom_mask_id_index) if self.__tooltip_text_of_wall_in_which_custom_mask_loads == 'show wall' else '{}{}'.format(self.__delbttn_id_prefix, self.__custom_mask_id_index)
    
    def __delete_old_masks(self):
        self.__del_mask_with_black()
        self.__del_mask_with_transparency()
        
    def __del_mask_with_black(self):
        if utils.find_file_in_folder_by_filename_substring(MASK_WITH_BLACK_FOLDER, self.__common_substring_of_wall_and_appropriate_mask_names) != None:
            mask_path = utils.find_file_in_folder_by_filename_substring(MASK_WITH_BLACK_FOLDER, self.__common_substring_of_wall_and_appropriate_mask_names)
            utils.remove_file(mask_path) 

    def __del_mask_with_transparency(self):
        if utils.find_file_in_folder_by_filename_substring(MASK_WITH_TRANSPARENT_FOLDER, self.__common_substring_of_wall_and_appropriate_mask_names) != None:
            mask_path = utils.find_file_in_folder_by_filename_substring(MASK_WITH_TRANSPARENT_FOLDER, self.__common_substring_of_wall_and_appropriate_mask_names)
            utils.remove_file(mask_path) 

    def response_custom_mask(self, obj_response):
        obj_response.script("$('#%s').attr('src','%s');"%(self.__target_html_element_where_custom_mask_will_be_added_id, self.__custom_mask_src))
   

    #############################################################################################
    def on_del_wall_and_appropriate_mask_bttn_click(self, img_to_be_deleted_name):
        self._deleted_img_name = img_to_be_deleted_name
        super().on_del_img_bttn_click()
        self.__del_appropriate_mask()
        
    def __del_appropriate_mask(self):
        self.__common_substring_of_wall_and_appropriate_mask_names =  self._deleted_img_name.split('wall-')[-1].split('.')[0]
        self.__del_mask_with_black()
        self.__del_mask_with_transparency()
    
    #############################################################################################
    def on_wall_gallery_img_click(self,obj_response, clicked_wall_data):
       
        self._clicked_img_name = clicked_wall_data[0]
      
        self.__common_substring_of_wall_and_appropriate_mask_names = self._clicked_img_name.split('wall-')[-1].split('.')[0]
       
        if clicked_wall_data[1] != 'uploaded':
            self.__response_wall_to_canvas(obj_response)
        else:
            self._clicked_img_path = utils.create_filepath(WALL_FOLDER, self._clicked_img_name)
        
        self._gallery_img_thumb_path = utils.create_filepath(self._IMG_THUMBNAILS, self._clicked_img_name)
        self.__response_mask_to_canvas(obj_response)

    def __response_wall_to_canvas(self, obj_response):
        super().on_img_clicked(obj_response)

    def __response_mask_to_canvas(self, obj_response):
        mask_src = self.__make_mask_src(MASK_WITH_TRANSPARENT_FOLDER)
        obj_response.script("$(mask).attr('src','%s');"%(mask_src))
    
   
class StickerGalleryManager(GalleryManager):

    def __init__(self):
        global STICKER_FOLDER, STICKER_THUMBNAILS
        self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type,  self._img_name_prefix = 'sticker_gallery', '_sticker', 'del_sticker', 'sticker', 'sticker'
        super().__init__(STICKER_FOLDER, STICKER_THUMBNAILS, self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type)

    def reload_stickers_gallery(self, obj_response):
        super().reload_gallery(obj_response) 
     
    def on_input_new_sticker_bttn_click(self,obj_response, sticker_src):
        self._loaded_img_src = sticker_src
        super().on_input_new_img_bttn_click(obj_response)

    def on_del_sticker_bttn_click(self, img_to_be_deleted_name):
        self._deleted_img_name = img_to_be_deleted_name
        super().on_del_img_bttn_click()
    
    def on_sticker_gallery_img_click(self, obj_response, clicked_sticker_data):
        self._clicked_img_name = clicked_sticker_data[0]
        if clicked_sticker_data[1] != 'uploaded':
            super().on_img_clicked(obj_response)
        else:
            self._clicked_img_path = utils.create_filepath(STICKER_FOLDER, self._clicked_img_name)

        
class AutoModeManager:
   
    __result_img_path = ''
   
    def __init__(self):
        global TMP_FOLDER, automode_files, automode_settings
        
    def response_processed_image(self, obj_response):
        if automode_files['wallFilePath'] != None and automode_files['stickerFilePath'] != None:
            self.__result_img_path = imgutils.process_automode_img(automode_files, automode_settings, TMP_FOLDER)
            self.__response_automode_img(obj_response)

    def __response_automode_img(self, obj_response):
        self.__remove_previous_automode_img(obj_response)
        result_img_src = imgutils.encode_img(self.__result_img_path)
        obj_response.script("$('#formCanvasResponse').append($('<img>',{ style:'position:absolute; left:0px; top:0px; z-index: 2', name:'bottom_gallery' ,id:'theImg',src:'%s'}));"%(result_img_src))
    
    def __remove_previous_automode_img(self, obj_response):
        obj_response.script("$('#theImg').remove()");
   
class Dispatcher(object):

    __custom_img_data = ''
   
    def __init__(self):
        global WALL_FOLDER, WALL_THUMBNAILS, STICKER_FOLDER, STICKER_THUMBNAILS, MASK_WITH_BLACK_FOLDER, TMP_FOLDER, automode_files, automode_settings 
        self.__create_folders()
        self.__make_instances()

    def __create_folders(self):
        self.__create_folder(WALL_THUMBNAILS)
        self.__create_folder(WALL_FOLDER)
        self.__create_folder(STICKER_THUMBNAILS)
        self.__create_folder(STICKER_FOLDER)
        self.__create_folder(MASK_WITH_BLACK_FOLDER)
    
    def __create_folder(self, folder_path):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    def __make_instances(self):
        self.__wall_gallery_manager = WallGalleryManager()
        self.__sticker_gallery_manager = StickerGalleryManager()
        self.__auto_mode_manager = AutoModeManager()
    
      
    def dispatch(self, obj_response, client_data):
        
        if 'loaded_custom_wall' in client_data:
            self.__custom_img_data = client_data['loaded_custom_wall']
            automode_files['wallFilePath'] = self.__on_custom_img_loaded_to_canvas()
            
        if 'loaded_custom_mask' in client_data:
            self.__custom_img_data = client_data['loaded_custom_mask']
            automode_files['maskFilePath']  = self.__on_custom_img_loaded_to_canvas()

        if 'loaded_custom_sticker' in client_data:
            self.__custom_img_data = client_data['loaded_custom_sticker']
            automode_files['stickerFilePath']  = self.__on_custom_img_loaded_to_canvas()

        if  'loaded_wall_gallery' in client_data:
            self.__wall_gallery_manager.reload_walls_and_masks_gallery(obj_response)

        if  'loaded_sticker_gallery' in client_data:
            self.__sticker_gallery_manager.reload_stickers_gallery(obj_response)
        
        if 'loaded_gallery_wall_file' in client_data:
           self.__wall_gallery_manager.on_input_new_wall_bttn_click(obj_response, client_data['loaded_gallery_wall_file'])
          
        if 'loaded_gallery_mask_file' in client_data:
            self.__wall_gallery_manager.on_input_custom_mask_bttn_click(obj_response, client_data['loaded_gallery_mask_file'])
            
        if 'loaded_gallery_sticker_file' in client_data:
            self.__sticker_gallery_manager.on_input_new_sticker_bttn_click(obj_response, client_data['loaded_gallery_sticker_file'])

        if 'clicked_gallery_wall_mask' in client_data:
            self.__wall_gallery_manager.on_wall_gallery_img_click(obj_response, client_data['clicked_gallery_wall_mask'])
            automode_files['wallFilePath']  = self.__wall_gallery_manager._clicked_img_path 
        
        if 'clicked_gallery_sticker' in client_data:
            self.__sticker_gallery_manager.on_sticker_gallery_img_click(obj_response, client_data['clicked_gallery_sticker'])
            automode_files['stickerFilePath']  = self.__sticker_gallery_manager._clicked_img_path 
            
        if  'delGalleryImg' in client_data:
            self.__on_delete_bttn_pressed(client_data['delGalleryImg'])

        if 'automode_settings' in client_data: 
            automode_settings['sticker_center'] = client_data['automode_settings'][0]
            automode_settings['repeat_x'] = client_data['automode_settings'][1]
            automode_settings['repeat_y'] = client_data['automode_settings'][2]
            automode_settings['opacity'] = client_data['automode_settings'][3]
            self.__auto_mode_manager.response_processed_image(obj_response)
      
        if 'downloaded' in client_data:
            utils.clear_dir(TMP_FOLDER)
        
      
    def __on_custom_img_loaded_to_canvas(self):
        custom_img_name, custom_img_src = self.__custom_img_data[0], self.__custom_img_data[1]
        custom_img_path = utils.create_filepath(TMP_FOLDER, custom_img_name)
        imgutils.decode_img_and_save_to_folder(custom_img_src, custom_img_path)
        return custom_img_path

    def __on_delete_bttn_pressed(self, bttn_data):
        img_to_be_deleted_name, delete_bttn_id = bttn_data[0], bttn_data[1]
        self.__wall_gallery_manager.on_del_wall_and_appropriate_mask_bttn_click(img_to_be_deleted_name) if delete_bttn_id == 'delete_wall_mask' else self.__sticker_gallery_manager.on_del_sticker_bttn_click(img_to_be_deleted_name)
          

@flask_sijax.route(app, "/")
def index():
    dispatcher = Dispatcher()
    if g.sijax.is_sijax_request:
        # Sijax request detected - let Sijax handle it
        g.sijax.register_callback('client_data', dispatcher.dispatch) 
        # The request looks like a valid Sijax request
        # The handlers are already registered above.. we can process the request
        return g.sijax.process_request()
    return render_template(index.html)

@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500
           
if __name__ == '__main__':
   #app.run(host='0.0.0.0', port=63100, debug=True)
   http_server = WSGIServer(('', 63100), app)
   http_server.serve_forever()
   
