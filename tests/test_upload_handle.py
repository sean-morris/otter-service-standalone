import otter_service_stdalone.upload_handle as uh
import pytest
import os
import shutil


@pytest.fixture
def resources():
    s1 = "tests/files/hw3-submissions-mixed/student_1.ipynb"
    s4 = "tests/files/hw3-submissions-mixed/student_4.ipynb"
    l4 = "tests/files/lab04/lab04.ipynb"
    n1 = "tests/files/hw3-submissions-only-notebooks"
    n2 = "tests/files/hw3-submissions-notebooks-zips-mixed"
    shutil.copy("tests/files/student_1.zip", "/".join(s1.split("/")[:-1]))
    shutil.copy("tests/files/student_4.zip", "/".join(s4.split("/")[:-1]))
    yield "resources"
    if os.path.exists(s1):
        os.remove(s1)
    if os.path.exists(s4):
        os.remove(s4)
    if os.path.exists(l4):
        shutil.move(l4, "tests/files/")
        os.rmdir("tests/files/lab04")
    if os.path.exists(n1):
        shutil.rmtree(n1)
    if os.path.exists(n2):
        shutil.rmtree(n2)


def test_one_notebook(resources):
    assert uh.one_notebook("./files/lab04.ipynb") is True
    assert uh.one_notebook("./files/hw3-submissions.zip") is False


def test_just_notebooks(resources):
    assert uh.just_notebooks("tests/files/hw3-submissions-notebooks/") is True
    assert uh.just_notebooks("tests/files/hw3-submissions-mixed") is False


def test_zip_with_zips(resources):
    assert uh.zip_with_zips("tests/files/hw3-submissions-notebooks/") is False
    assert uh.zip_with_zips("tests/files/hw3-submissions-mixed") is True


def test_zip_with_zips_process_dir(resources):
    p = "tests/files/hw3-submissions-mixed"
    assert "files/hw3-submissions-mixed" in uh.zip_with_zips_process_dir(p)


def test_handle_one_notebook(resources):
    assert "files/lab04" in uh.handle_one_notebook("tests/files/lab04.ipynb")


def test_handle_upload(resources):
    zip = "tests/files/hw3-submissions-only-notebooks.zip"
    mixed_zip = "tests/files/hw3-submissions-notebooks-zips-mixed.zip"
    assert "files/lab04" in uh.handle_upload("tests/files/lab04.ipynb")
    assert "files/hw3-submissions-only-notebooks" in uh.handle_upload(zip)
    assert "files/hw3-submissions-only-notebooks" in uh.handle_upload(zip)
    assert "files/hw3-submissions-notebooks-zips-mixed" in uh.handle_upload(mixed_zip)
