import os, glob
import uuid


def get_file_extension(b64file):
    file_ext = b64file.split(',')[0].split('/')[1].split(';')[0]
    return file_ext


def create_filename(prefix, file_ext):
    filename = prefix + str(uuid.uuid4())+ '.{}'.format(file_ext)
    return filename

def create_filepath(folder, filename):
    filepath = os.path.join(folder, filename) 
    return filepath

def remove_file(filepath):
    if os.path.isfile(filepath):
        os.remove(filepath)

def clear_dir(dir_path):
    files = glob.glob('/{}/*'.format(dir_path))
    for f in files:
        os.remove(f)

def write_file(file_path, file_src):
    with open(file_path, 'wb') as f:
        f.write(file_src)

def find_file_in_folder_by_filename_substring(folder_path, filename_substring):
    for file_path in glob.glob(os.path.join(folder_path, "*.*")):
        if filename_substring in file_path:
            return file_path
    return None

def get_number_of_files_in_directory(dir_path):
        files_list = os.listdir(dir_path) 
        return len(files_list)