import os.path
import time
from argparse import Namespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from src import utils
from src.exceptions import InvalidConfig

test_filepath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "fixtures", "test_files"
)


def mocked_localtime():
    return time.struct_time((2024, 4, 13, 9, 0, 0, 5, 104, 1))


def mock_load_cookie(domain_name=None):
    cookie = Mock()
    cookie.name = "_otwarchive_session"
    cookie.value = "test_browser_cookie"
    jar = MagicMock()
    jar.__iter__.return_value = [cookie]
    return jar


def mock_load_no_cookie(domain_name=None):
    jar = MagicMock()
    jar.__iter__.return_value = []
    return jar


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


def test_setup_login_cookie(capsys):
    options = Namespace(
        cookie="testcookie", use_browser_cookie=False, mirror=utils.AO3_DEFAULT_URL
    )
    utils.setup_login(options)

    captured = capsys.readouterr()
    assert "Using the cookie value you passed in" in captured.out

    assert options.cookie == "testcookie"


@patch("src.utils.browser_cookie3.firefox", mock_load_cookie)
def test_setup_login_use_browser_cookie(capsys):
    options = Namespace(
        cookie=None, use_browser_cookie=True, mirror=utils.AO3_DEFAULT_URL
    )
    utils.setup_login(options)

    captured = capsys.readouterr()
    assert "Found _otwarchive_session cookie from the browser" in captured.out

    assert options.cookie == "test_browser_cookie"


@patch("src.utils.browser_cookie3.firefox", mock_load_cookie)
def test_setup_login_cookie_and_use_browser_cookie(capsys):
    options = Namespace(
        cookie="testcookie", use_browser_cookie=True, mirror=utils.AO3_DEFAULT_URL
    )
    utils.setup_login(options)

    captured = capsys.readouterr()
    assert "Found _otwarchive_session cookie from the browser" in captured.out

    assert options.cookie == "test_browser_cookie"


@patch("src.utils.browser_cookie3.firefox", mock_load_no_cookie)
def test_setup_login_use_browser_cookie_but_browser_cookie_not_found(capsys):
    options = Namespace(
        cookie=None, use_browser_cookie=True, mirror=utils.AO3_DEFAULT_URL
    )

    with pytest.raises(
        InvalidConfig, match="Tried to get the _otwarchive_session cookie"
    ):
        utils.setup_login(options)


@patch("src.utils.browser_cookie3.firefox", mock_load_no_cookie)
def test_setup_login_cookie_and_use_browser_cookie_but_browser_cookie_not_found(capsys):
    options = Namespace(
        cookie="testcookie", use_browser_cookie=True, mirror=utils.AO3_DEFAULT_URL
    )
    utils.setup_login(options)

    captured = capsys.readouterr()
    assert "Falling back to the cookie value you passed in" in captured.out

    assert options.cookie == "testcookie"
