import re
import zipfile
from packaging import version
import os
import shutil


def is_version_6_or_greater(zip_ref, target_file, reg):
    if target_file:
        with zip_ref.open(target_file) as file:
            content = file.read().decode('utf-8')
            match = reg.search(content)
            if match:
                version_str = match.group(2)
                try:
                    current_ver = version.parse(version_str)
                    target_ver = version.parse(os.environ.get("TARGET_OTTER_VERSION"))
                    return current_ver >= target_ver
                except Exception:
                    pass
            else:
                return True
    return False


def otter_version_correct(autograder_path):
    requirements_regex = re.compile(r"otter-grader(\[.*?\])?==([\d.]+)")
    environment_regex = re.compile(r"otter-grader(\[.*?\])?==([\d.]+)")
    # Open the zip file
    with zipfile.ZipFile(autograder_path, 'r') as zip_ref:
        # Get a list of files in the zip
        file_list = zip_ref.namelist()

        # Check if 'requirements.txt' or 'environment.yaml' exists
        req_target_file = None
        env_target_file = None
        if 'requirements.txt' in file_list:
            req_target_file = 'requirements.txt'
        if 'environment.yml' in file_list:
            env_target_file = 'environment.yml'

        otter_in_req = is_version_6_or_greater(zip_ref, req_target_file, requirements_regex)
        otter_in_env = is_version_6_or_greater(zip_ref, env_target_file, environment_regex)
        return otter_in_req or otter_in_env


def sanitize_filename(filename: str) -> str:
    """
    Remove periods and commas from filename except the extension dot.
    """
    # Split name and extension
    name, ext = os.path.splitext(filename)
    # Remove periods and commas from the name part
    clean_name = name.replace('.', '').replace(',', '').replace(' ', '')
    return f"{clean_name}{ext}"


def clean_directory(path: str):
    """
    Delete hidden folders like __MACOSX and sanitize all file names in the directory tree.
    """
    for root, dirs, files in os.walk(path, topdown=True):
        # Remove hidden/system folders
        for dir_name in list(dirs):
            if dir_name.startswith('.') or dir_name == '__MACOSX':
                dir_path = os.path.join(root, dir_name)
                shutil.rmtree(dir_path)
                dirs.remove(dir_name)  # remove from list to avoid walking it

        # Sanitize file names
        for file_name in files:
            old_path = os.path.join(root, file_name)
            new_name = sanitize_filename(file_name)
            new_path = os.path.join(root, new_name)
            if old_path != new_path:
                os.rename(old_path, new_path)
