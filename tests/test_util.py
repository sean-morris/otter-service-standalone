import otter_service_stdalone.util as util


def test_autograder_zip_version():
    a1 = "tests/files/hw01-autograder_6_0_4.zip"
    a2 = "tests/files/hw02-autograder_6_1_0.zip"
    a3 = "tests/files/hw02-autograder_5_5_0.zip"
    assert util.otter_version_correct(a1) is True
    assert util.otter_version_correct(a2) is True
    assert util.otter_version_correct(a3) is False
