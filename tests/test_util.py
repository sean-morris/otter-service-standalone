import otter_service_stdalone.util as util
import shutil
import os
import re


def test_autograder_zip_version():
    a1 = "tests/files/hw01-autograder_6_0_4.zip"
    a2 = "tests/files/hw02-autograder_6_1_0.zip"
    a3 = "tests/files/hw02-autograder_5_5_0.zip"
    a4 = "tests/files/hw03-autograder_6_1_3.zip"
    a5 = "tests/files/hw03-autograder_no_version.zip"
    assert util.otter_version_correct(a1) is False
    assert util.otter_version_correct(a2) is False
    assert util.otter_version_correct(a3) is False
    assert util.otter_version_correct(a4)
    assert util.otter_version_correct(a5)


def test_clean_directory():
    clean_this_dir = "tests/files/clean_up_dir"
    tmp_dir = clean_this_dir + "_tmp"
    shutil.copytree(clean_this_dir, tmp_dir)
    util.clean_directory(tmp_dir)
    allowed_pattern = re.compile(r'^[\w\-]+(\.[\w\-]+)?$')
    for root, dirs, files in os.walk(tmp_dir):
        for d in dirs:
            assert not d.startswith('.') and d != '__MACOSX', f"Hidden dir found: {d}"
            assert allowed_pattern.match(d), f"Invalid characters in directory name: {d}"

        for f in files:
            assert not f.startswith('.'), f"Hidden file found: {f}"
            assert allowed_pattern.match(f), f"Invalid characters in filename: {f}"
    shutil.rmtree(tmp_dir)
