import os
import shutil
from zipfile import ZipFile
from otter_service_stdalone import fs_logging as log


def handle_one_notebook(path):
    """This configures a folder to hold the single notebook created for otter grader

    Args:
        path (str): this path to the notebook

    Returns:
        str: the notebook path
    """
    notebook_name = path.split(".")[0]
    os.mkdir(notebook_name)
    shutil.move(path, notebook_name)
    return notebook_name


def one_notebook(path):
    """test whyether this is just one notebook

    Args:
        path (str): the path to the submitted file

    Returns:
        bool: True it is a notebook, False otherwise
    """
    return path.endswith(".ipynb")


def just_notebooks(dir_path):
    """standard grouping of straight zip folder with only notebooks

    Args:
        dir_path (str): the path to the sumbitted file

    Returns:
        bool: True it is a zip file, False otherwise
    """
    for _, _, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".zip"):
                return False
    return True


def zip_with_zips(dir_path):
    """zip with zips and possibly notebooks

    Args:
        dir_path (str): path to submitted file

    Returns:
        bool: True the zip files contains zips files, False otherwise
    """
    for root, dirs, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".zip"):
                return True
    return False


def zip_with_zips_process_dir(path):
    """this is called by zips_with_zips to process an embedded zip file

    Args:
        path (str): path to embedded zip file

    Returns:
        str: the path to unzipped zip file
    """
    for root, _, files in os.walk(path):
        for f in files:
            f_path = os.path.join(root, f)
            if f_path.endswith(".zip"):
                zip_folder = f_path.split(".")[0]
                if not os.path.exists(zip_folder):
                    os.mkdir(zip_folder)
                with ZipFile(f_path, 'r') as zObject:
                    zObject.extractall(path=zip_folder)
                for sub_root, _, sub_files in os.walk(zip_folder):
                    for sub_f in sub_files:
                        n_path = os.path.join(sub_root, sub_f)
                        if n_path.endswith(".ipynb"):
                            new_notebook_path = [path, f"{zip_folder.split('/')[-1]}.ipynb"]
                            shutil.move(n_path, "/".join(new_notebook_path))
                            shutil.rmtree(zip_folder)
                            os.remove(zip_folder + ".zip")
    return path


def handle_upload(path, results_id):
    """main handler for uploads

    Args:
        path (str): path can be single notebook, zip of notebooks, zip of zips
        results_id (str): the folder name where the notebooks and results are written

    Raises:
        Exception: if we do not recognize the file extension raise an exception
        e: this is raised again from the except

    Returns:
        str: path to folder that will be processed by otter grader
    """
    try:
        log.write_logs(results_id, "Step 4: Configure Notebooks Folder for Otter Grader",
                       "Determine what format of notebooks uploaded: zip or ipynb",
                       "debug",
                       f'{os.environ.get("ENVIRONMENT")}-debug')
        if one_notebook(path):
            log.write_logs(results_id, "Step 4a: Configure Notebooks Folder for Otter Grader",
                           "Single Notebook Uploaded",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            return handle_one_notebook(path)
        else:
            if path.endswith(".zip"):
                zip_folder = path.split(".")[0]
                with ZipFile(path, 'r') as zObject:
                    zObject.extractall(path=zip_folder)

                log.write_logs(results_id, "Step 4a: Configure Notebooks Folder for Otter Grader",
                               "Zipped file of notebooks Uploaded",
                               "debug",
                               f'{os.environ.get("ENVIRONMENT")}-debug')
                if just_notebooks(zip_folder):
                    log.write_logs(results_id, "Step 4b: Configure Notebooks Folder",
                                   "Zipped file of JUST notebooks Uploaded",
                                   "debug",
                                   f'{os.environ.get("ENVIRONMENT")}-debug')
                    return zip_folder
                elif zip_with_zips(zip_folder):
                    log.write_logs(results_id, "Step 4b: Configure Notebooks Folder",
                                   "Zipped file of notebooks AND zips of notebooks Uploaded",
                                   "debug",
                                   f'{os.environ.get("ENVIRONMENT")}-debug')
                    return zip_with_zips_process_dir(zip_folder)
        err = "Trouble recognizing uploaded file. Please submit a zip file or one ipynb file"
        raise Exception(err)
    except Exception as e:
        raise e
