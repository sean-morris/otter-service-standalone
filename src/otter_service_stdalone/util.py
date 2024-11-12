import re
import zipfile


def is_version_5_or_greater(zip_ref, target_file, reg):
    if target_file:
        with zip_ref.open(target_file) as file:
            content = file.read().decode('utf-8')
            match = reg.search(content)
            if match:
                version = match.group(2)
                version_nums = version.split(".")
                if len(version_nums) > 0 and int(version_nums[0]) >= 5:
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

        otter_in_req = is_version_5_or_greater(zip_ref, req_target_file, requirements_regex)
        otter_in_env = is_version_5_or_greater(zip_ref, env_target_file, environment_regex)
        return otter_in_req or otter_in_env
