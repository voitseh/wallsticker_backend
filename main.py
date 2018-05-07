import flask_sijax
import os, glob
import utils
import imgutils
import logging
from flask import Flask, g
from flask_cors import CORS
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
MASK_FOLDER = os.path.join(UPLOAD_FOLDER, 'mask_gallery')
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

    _img_thumb_path = ''
   
    _loaded_img_path, _loaded_img_src, _loaded_img_thumb_path = '', '', ''

    _clicked_img_name, _clicked_img_path, _clicked_img_src = '', '', ''

    _deleted_img_name = ''

    def __init__(self, obj_response, IMG_FOLDER, IMG_THUMBNAILS, gallery_id, img_id_prefix, delbttn_id_prefix, img_type):
        self._IMG_FOLDER, self._IMG_THUMBNAILS = IMG_FOLDER, IMG_THUMBNAILS
        self._gallery_image_id_index = utils.get_number_of_files_in_directory(self._IMG_FOLDER)
        self._gallery_id, self._img_id_prefix, self._delbttn_id_prefix, self.img_type = gallery_id, img_id_prefix, delbttn_id_prefix, img_type
        self._obj_response = obj_response
       
    #####################################################################################
    def reload_gallery(self):
        self.clear_gallery()
        self.fill_gallery_with_images()  
     
    def clear_gallery(self):
        self._obj_response.script("$('#%s').children().remove()"%(self._gallery_id));
        
    def fill_gallery_with_images(self):
        self._gallery_image_id_index = 0
        for img_thumb_path in glob.glob(os.path.join(self._IMG_THUMBNAILS, "*.*")):
            self._img_thumb_path = img_thumb_path
            self.__response_gallery_img()
            self._gallery_image_id_index += 1

    def __response_gallery_img(self):
        img_name, img_src, img_id, delbttn_id = self.__make_img_attrs()
        self._obj_response.script("$('#%s').append($('<li>',{class:'image_grid'}).append($('<a href=#>').append($('<label>').append($('<img>',{id:'%s', src:'%s', name:'%s'})).append($('<input>',{type:'radio', name:'selimg'})).append($('<span>',{class:'caption'})).append($('<span>',{id:'%s', src:''})))));"%(self._gallery_id, img_id, img_src, img_name, delbttn_id))

    def __make_img_attrs(self):
        img_name = self._img_thumb_path.split('/')[-1]
        img_src = imgutils.encode_img(self._img_thumb_path)
        img_id = '{}{}'.format(self._img_id_prefix, str(self._gallery_image_id_index))
        delbttn_id = '{}{}'.format(self._delbttn_id_prefix, str(self._gallery_image_id_index))
        return img_name, img_src, img_id, delbttn_id

    ########################################################################################
    def on_input_new_img_bttn_click(self):
        self._create_img_path()
        self._create_img_thumb_path()
        imgutils.decode_img_and_save_to_folder(self._loaded_img_src, self._loaded_img_path)
        imgutils.make_and_save_thumbnail(self._loaded_img_path, self._loaded_img_thumb_path)
        self._img_thumb_path = self._loaded_img_thumb_path
        self.__response_gallery_img()
        self._gallery_image_id_index += 1

    def _create_img_path(self):
        img_file_ext = utils.get_file_extension(self._loaded_img_src)
        img_name = utils.create_filename('{}-'.format(self._img_name_prefix), img_file_ext)
        self._loaded_img_path = utils.create_filepath(self._IMG_FOLDER, img_name)
        
    def _create_img_thumb_path(self):
        self._loaded_img_thumb_path = utils.create_filepath(self._IMG_THUMBNAILS, self._loaded_img_path.split('/')[-1])
        
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
    def on_img_clicked(self):
        self._clicked_img_path = utils.create_filepath(self._IMG_FOLDER, self._clicked_img_name)
        self._clicked_img_src = imgutils.encode_img(self._clicked_img_path)
        self._send_img_to_canvas()
       
    def _send_img_to_canvas(self):
        self._obj_response.script("$(%s).attr('src','%s');"%(self.img_type, self._clicked_img_src))

class WallGalleryManager(GalleryManager):

    __wall_gallery_image_id_index = 0

    __custom_mask_name, __custom_mask_src, __custom_mask_id_index = '', '', ''
    __target_html_element_where_custom_mask_will_be_added_id = ''

    __tooltip_text_of_wall_where_custom_mask_loads = ''

    __common_substring_of_wall_and_appropriate_mask_names = ''

    def __init__(self, obj_response):
        global WALL_FOLDER, WALL_THUMBNAILS, MASK_FOLDER
        self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type = 'wall_gallery', '_wall', 'del_wall', 'image'
        GalleryManager.__init__(self, obj_response, WALL_FOLDER, WALL_THUMBNAILS, self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type)
        
    ###############################################################################################
    def reload_walls_and_masks_gallery(self):
        super().clear_gallery()
        self.__fill_gallery_with_walls()
        self.__fill_gallery_with_masks()

    def __fill_gallery_with_walls(self):
        super().fill_gallery_with_images()
    
    def __fill_gallery_with_masks(self):
        self.__wall_gallery_image_id_index = 0
        for wall_thumb_path in glob.glob(os.path.join(self._IMG_THUMBNAILS, "*.*")):
            self._img_thumb_path = wall_thumb_path
            self.__create_common_substring_of_wall_and_mask_names()
            self.__response_appropriate_mask()
            self.__wall_gallery_image_id_index += 1

    def __create_common_substring_of_wall_and_mask_names(self):
        self.__common_substring_of_wall_and_appropriate_mask_names = self._img_thumb_path.split('wall-')[-1].split('.')[0]
       
    
    def __response_appropriate_mask(self):
        appropriate_mask_src = self.__make_mask_src()
        target_element_for_mask_adding_id = '{}{}'.format(self.__delbttn_id_prefix, self.__wall_gallery_image_id_index)
        self._obj_response.script("$('#%s').attr('src', '%s')"%(target_element_for_mask_adding_id, appropriate_mask_src))

    def __make_mask_src(self):
        mask_path = self.__get_mask_path()
        mask_src = imgutils.encode_img(mask_path)
        return mask_src

    def __get_mask_path(self):
        if utils.find_file_in_folder_by_filename_substring(MASK_FOLDER, self.__common_substring_of_wall_and_appropriate_mask_names) != None:
            mask_path = utils.find_file_in_folder_by_filename_substring(MASK_FOLDER, self.__common_substring_of_wall_and_appropriate_mask_names)
        else:
            mask_path = utils.create_filepath(MASK_FOLDER, self._img_thumb_path.split('/')[-1].replace('wall', 'mask').split('.')[0]+'.png')
            imgutils.process_mask(self._img_thumb_path, mask_path)
        return mask_path

    ##############################################################################################
    def on_input_new_wall_bttn_click(self, wall_src):
        self._img_name_prefix = 'wall'
        self._loaded_img_src = wall_src
        super().on_input_new_img_bttn_click()
        self.__wall_gallery_image_id_index = self._gallery_image_id_index - 1
        self._img_thumb_path = self._loaded_img_thumb_path
        self.__create_common_substring_of_wall_and_mask_names()
        self.__response_appropriate_mask()
        
    ##############################################################################################
    def on_input_custom_mask_bttn_click(self, custom_mask_data):
        self.__get_loaded_custom_mask_data(custom_mask_data)
        custom_mask_path = utils.create_filepath(MASK_FOLDER, custom_mask_data[0])
        self.__delete_old_mask()
        imgutils.decode_img_and_save_to_folder(self.__custom_mask_src, custom_mask_path)
        self.__define_target_html_element_id_for_mask_adding()
        self.response_custom_mask()
           
    def __get_loaded_custom_mask_data(self, custom_mask_data):
        self.__custom_mask_name = custom_mask_data[0].split('.')[0]
        self.__custom_mask_src = custom_mask_data[1]
        self.__custom_mask_id_index = custom_mask_data[2]
        self.__tooltip_text_of_wall_in_which_custom_mask_loads = custom_mask_data[3]
        
    def __define_target_html_element_id_for_mask_adding(self):
        self.__target_html_element_where_custom_mask_will_be_added_id = '{}{}'.format(self.__img_id_prefix, self.__custom_mask_id_index) if self.__tooltip_text_of_wall_in_which_custom_mask_loads == 'show mask' else '{}{}'.format(self.__delbttn_id_prefix, self.__custom_mask_id_index)
    
    def __delete_old_mask(self):
        self.__del_mask(self.__custom_mask_name)
        
    def __del_mask(self, mask_name_substring):
        if utils.find_file_in_folder_by_filename_substring(MASK_FOLDER, mask_name_substring) != None:
            mask_path = utils.find_file_in_folder_by_filename_substring(MASK_FOLDER, mask_name_substring)
            utils.remove_file(mask_path) 

    def response_custom_mask(self):
        self._obj_response.script("$('#%s').attr('src','%s');"%(self.__target_html_element_where_custom_mask_will_be_added_id, self.__custom_mask_src))
   

    #############################################################################################
    def on_del_wall_and_appropriate_mask_bttn_click(self, img_to_be_deleted_name):
        self._deleted_img_name = img_to_be_deleted_name
        super().on_del_img_bttn_click()
        self.__del_appropriate_mask()
        
    def __del_appropriate_mask(self):
        self.__common_substring_of_wall_and_appropriate_mask_names =  self._deleted_img_name.split('wall-')[-1].split('.')[0]
        self.__del_mask(self.__common_substring_of_wall_and_appropriate_mask_names)
    
    #############################################################################################
    def on_wall_gallery_img_click(self, clicked_wall_data):
        self._clicked_img_name = clicked_wall_data[0]
        self.__common_substring_of_wall_and_appropriate_mask_names = self._clicked_img_name.split('wall-')[-1].split('.')[0]
        self.__response_wall_to_canvas()
        self._img_thumb_path = self._clicked_img_path
        self.__response_mask_to_canvas()

    def __response_wall_to_canvas(self):
        super().on_img_clicked()

    def __response_mask_to_canvas(self):
        mask_src = self.__make_mask_src()
        self._obj_response.script("$(mask).attr('src','%s');"%(mask_src))
    
   
class StickerGalleryManager(GalleryManager):

    def __init__(self, _obj_response):
        global STICKER_FOLDER, STICKER_THUMBNAILS
        self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type = 'sticker_gallery', '_sticker', 'del_sticker', 'sticker'
        super().__init__(_obj_response, STICKER_FOLDER, STICKER_THUMBNAILS, self.__gallery_id, self.__img_id_prefix, self.__delbttn_id_prefix, self.__img_type)

    def reload_stickers_gallery(self):
        super().reload_gallery() 
     
    def on_input_new_sticker_bttn_click(self, sticker_src):
        self._img_name_prefix = 'sticker'
        self._loaded_img_src = sticker_src
        super().on_input_new_img_bttn_click()

    def on_del_sticker_bttn_click(self, img_to_be_deleted_name):
        self._deleted_img_name = img_to_be_deleted_name
        super().on_del_img_bttn_click()
    
    def on_sticker_gallery_img_click(self, clicked_sticker_data):
        self._clicked_img_name = clicked_sticker_data
        super().on_img_clicked()
        

class AutoModeManager:
   
    __result_img_path = ''
   
    def __init__(self, obj_response):
        global TMP_FOLDER, automode_files, automode_settings
        self.obj_response = obj_response
        
    def response_processed_image(self):
        if automode_files['wallFilePath'] != None and automode_files['stickerFilePath'] != None:
            self.__result_img_path = imgutils.process_automode_img(automode_files, automode_settings, TMP_FOLDER)
            self.__response_automode_img()

    def __response_automode_img(self):
        self.__remove_previous_automode_img()
        result_img_src = imgutils.encode_img(self.__result_img_path)
        self.obj_response.script("$('#formCanvasResponse').append($('<img>',{ style:'position:absolute; left:0px; top:0px; z-index: 2', name:'bottom_gallery' ,id:'theImg',src:'%s'}));"%(result_img_src))
    
    def __remove_previous_automode_img(self):
        self.obj_response.script("$('#theImg').remove()");
   
    def set_default_values(self):
        utils.clear_dir(self.__TMP_FOLDER)
        automode_files['wallFilePath'], automode_files['maskFilePath'], automode_files['stickerFilePath'] = None, None, None
        automode_settings['sticker_center'] = False
        automode_settings['repeat_x'], automode_settings['repeat_y'], automode_settings['opacity'] = None, None, None

class Dispatcher(object):

    __obj_response = ''
    __client_data = ''
    __custom_img_data = ''
   
    def __init__(self):
        global WALL_FOLDER, WALL_THUMBNAILS, STICKER_FOLDER, STICKER_THUMBNAILS, MASK_FOLDER, TMP_FOLDER, automode_files, automode_settings 
        self.__check_paths()
      
    def dispatch(self, obj_response, client_data):
        
        self.__obj_response = obj_response
        self.__client_data = client_data
        
        self.__make_instances()
        
        if 'custom_wall' in self.__client_data:
            self.__custom_img_data = self.__client_data['custom_wall']
            automode_files['wallFilePath'] = self.__on_custom_img_loaded_to_canvas()
            
        if 'custom_mask' in self.__client_data:
            self.__custom_img_data = self.__client_data['custom_mask']
            automode_files['maskFilePath']  = self.__on_custom_img_loaded_to_canvas()

        if 'custom_sticker' in self.__client_data:
            self.__custom_img_data = self.__client_data['custom_sticker']
            automode_files['stickerFilePath']  = self.__on_custom_img_loaded_to_canvas()

        if  'wall_gallery' in self.__client_data:
            self.__wall_gallery_manager.reload_walls_and_masks_gallery()

        if  'sticker_gallery' in self.__client_data:
            self.__sticker_gallery_manager.reload_stickers_gallery()
        
        if 'galleryWallFile' in self.__client_data:
           self.__wall_gallery_manager.on_input_new_wall_bttn_click(self.__client_data['galleryWallFile'])
          
        if 'galleryMaskFile' in self.__client_data:
            self.__wall_gallery_manager.on_input_custom_mask_bttn_click(self.__client_data['galleryMaskFile'])
            
        if 'galleryStickerFile' in self.__client_data:
            self.__sticker_gallery_manager.on_input_new_sticker_bttn_click(self.__client_data['galleryStickerFile'])

        if 'wall_mask' in self.__client_data:
            self.__wall_gallery_manager.on_wall_gallery_img_click(self.__client_data['wall_mask'])
            automode_files['wallFilePath']  = self.__wall_gallery_manager._clicked_img_path 
        

        if 'sticker' in self.__client_data:
            self.__sticker_gallery_manager.on_sticker_gallery_img_click(self.__client_data['sticker'])
            automode_files['stickerFilePath']  = self.__sticker_gallery_manager._clicked_img_path 


        if  'delGalleryImg' in self.__client_data:
            self.__on_delete_bttn_pressed(self.__client_data['delGalleryImg'])

        if 'sticker_center' in self.__client_data: 
            automode_settings['sticker_center'] = self.__client_data['sticker_center']
            self.__auto_mode_manager.response_processed_image()
        
        if 'repeat_x' in self.__client_data:
            automode_settings['repeat_x'] = self.__client_data['repeat_x']
            self.__auto_mode_manager.response_processed_image()
    
        if 'repeat_y' in self.__client_data:
            automode_settings['repeat_y'] = self.__client_data['repeat_y']
            self.__auto_mode_manager.response_processed_image()

        if 'opacity' in self.__client_data:
            automode_settings['opacity'] = self.__client_data['opacity']
            self.__auto_mode_manager.response_processed_image()
            
        if 'downloaded' in self.__client_data:
            if client_data['downloaded'] == 'true':
                self.__auto_mode_manager.set_default_values()
        
      
    def __check_paths(self):
        self.__create_folder(WALL_THUMBNAILS)
        self.__create_folder(WALL_FOLDER)
        self.__create_folder(STICKER_THUMBNAILS)
        self.__create_folder(STICKER_FOLDER)
        self.__create_folder(MASK_FOLDER)
    
    def __create_folder(self, folder_path):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    def __make_instances(self):
        self.__wall_gallery_manager = WallGalleryManager(self.__obj_response)
        self.__sticker_gallery_manager = StickerGalleryManager(self.__obj_response)
        self.__auto_mode_manager = AutoModeManager(self.__obj_response)


    def __on_custom_img_loaded_to_canvas():
        custom_img_name, custom_img_src = self.__custom_img_data[0], self.__custom_img_data[1]
        custom_img_path = create_filepath(TMP_FOLDER, custom_img_name)
        decode_img_and_save_to_folder(custom_img_src, custom_img_path)
        return custom_img_path

    def __on_delete_bttn_pressed(self, bttn_data):
        img_to_be_deleted_name, delete_bttn_id = bttn_data[0], bttn_data[1]
        self.__wall_gallery_manager.on_del_wall_and_appropriate_mask_bttn_click(img_to_be_deleted_name) if delete_bttn_id == 'delete_wall_mask' else self.__sticker_gallery_manager.on_del_sticker_bttn_click(img_to_be_deleted_name)
          

@flask_sijax.route(app, "/")
def index():
    
    if g.sijax.is_sijax_request:
        # Sijax request detected - let Sijax handle it
        g.sijax.register_callback('client_data', Dispatcher().dispatch) 
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
   app.run(host='0.0.0.0', port=63100, debug=True)
   
