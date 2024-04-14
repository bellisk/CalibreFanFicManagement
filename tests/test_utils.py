import os.path
import time
from unittest.mock import patch

from src import utils

test_filepath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "fixtures", "test_files"
)


def mocked_localtime():
    return time.struct_time((2024, 4, 13, 9, 0, 0, 5, 104, 1))


def test_log_no_color():
    with patch("src.utils.localtime", mocked_localtime):
        msg = utils.log("Test message", output=False)

    assert msg == "\033[1m04/13/2024 09:00:00\033[0m: \t Test message\n"


def test_log_color():
    with patch("src.utils.localtime", mocked_localtime):
        msg = utils.log("Test message", color=utils.Bcolors.HEADER, output=False)

    assert msg == "\033[1m04/13/2024 09:00:00\033[0m: \t \033[95mTest message\033[0m\n"


def test_log_live_output(capsys):
    with patch("src.utils.localtime", mocked_localtime):
        msg = utils.log("Test message", color=utils.Bcolors.HEADER, output=True)

    assert msg == ""
    captured = capsys.readouterr()
    assert (
        captured.out
        == "\033[1m04/13/2024 09:00:00\033[0m: \t \033[95mTest message\033[0m\n"
    )


def test_get_files_no_fileteype():
    files = utils.get_files(test_filepath, filetype=None, fullpath=False)

    assert sorted(files) == ["test.csv", "test.ini", "test.txt"]


def test_get_files_fileteype():
    files = utils.get_files(test_filepath, filetype="csv", fullpath=False)

    assert sorted(files) == ["test.csv"]


def test_get_files_no_fileteype_fullpath():
    files = utils.get_files(test_filepath, filetype=None, fullpath=True)

    assert sorted(files) == [
        os.path.join(test_filepath, "test.csv"),
        os.path.join(test_filepath, "test.ini"),
        os.path.join(test_filepath, "test.txt"),
    ]


def test_get_files_fileteype_fullpath():
    files = utils.get_files(test_filepath, filetype="csv", fullpath=True)

    assert sorted(files) == [os.path.join(test_filepath, "test.csv")]
