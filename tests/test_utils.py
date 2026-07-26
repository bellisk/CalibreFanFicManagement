import json
import locale
import os.path
import time
from argparse import Namespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from ao3_utils import AO3_DEFAULT_URL
from src import utils
from src.exceptions import InvalidConfig

test_filepath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "fixtures", "test_files"
)


def mocked_localtime():
    return time.struct_time((2024, 4, 13, 9, 0, 0, 5, 104, 1))


def mock_browser_with_cookie():
    def browser(domain_name=None):
        cookie = Mock()
        cookie.name = "_otwarchive_session"
        cookie.value = "test_browser_cookie"
        jar = MagicMock()
        jar.__iter__.return_value = [cookie]
        return jar

    return browser


def mock_browser_no_cookie():
    def browser(domain_name=None):
        jar = MagicMock()
        jar.__iter__.return_value = []
        return jar

    return browser


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


@patch("src.utils.browser_cookie3.all_browsers", [mock_browser_with_cookie()])
def test_set_browser_cookie(capsys):
    options = Namespace(cookie=None, use_browser_cookie=True, mirror=AO3_DEFAULT_URL)
    utils.set_browser_cookie(options)

    captured = capsys.readouterr()
    assert "Found _otwarchive_session cookie from the browser" in captured.out

    assert options.cookie == "test_browser_cookie"


@patch("src.utils.browser_cookie3.all_browsers", [mock_browser_with_cookie()])
def test_set_browser_cookie_overrides_provided_cookie(capsys):
    options = Namespace(
        cookie="testcookie", use_browser_cookie=True, mirror=AO3_DEFAULT_URL
    )
    utils.set_browser_cookie(options)

    captured = capsys.readouterr()
    assert "Found _otwarchive_session cookie from the browser" in captured.out

    assert options.cookie == "test_browser_cookie"


@patch(
    "src.utils.browser_cookie3.all_browsers",
    [mock_browser_no_cookie(), mock_browser_with_cookie()],
)
def test_set_browser_cookie_ignore_browser_with_no_cookie(capsys):
    options = Namespace(cookie=None, use_browser_cookie=True, mirror=AO3_DEFAULT_URL)
    utils.set_browser_cookie(options)

    captured = capsys.readouterr()
    assert "Found _otwarchive_session cookie from the browser" in captured.out

    assert options.cookie == "test_browser_cookie"


@patch("src.utils.browser_cookie3.all_browsers", [mock_browser_no_cookie()])
def test_set_browser_cookie_browser_raises_error_when_cookie_not_found(capsys):
    options = Namespace(cookie=None, use_browser_cookie=True, mirror=AO3_DEFAULT_URL)

    with pytest.raises(
        InvalidConfig, match="Tried to get the _otwarchive_session cookie"
    ):
        utils.set_browser_cookie(options)


@patch("src.utils.browser_cookie3.all_browsers", [mock_browser_no_cookie()])
def test_set_browser_cookie_falls_back_to_provided_cookie_when_browser_cookie_not_found(
    capsys,
):
    options = Namespace(
        cookie="testcookie", use_browser_cookie=True, mirror=AO3_DEFAULT_URL
    )
    utils.set_browser_cookie(options)

    captured = capsys.readouterr()
    assert "Falling back to the cookie value you passed in" in captured.out

    assert options.cookie == "testcookie"


def test_get_all_metadata_options():
    # The locale for AO3, for converting formatted numbers.
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

    fic_metadata_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "fixtures", "fic_metadata.json"
    )
    with open(fic_metadata_path, "r") as f:
        metadata = json.loads(f.read())

    options = utils.get_all_metadata_options(metadata)

    assert options == {
        "#ao3categories": "Gen",
        "#characters": (
            "Merlin Hermes,Mr． Fool (Lord of the Mysteries),Tarot Club "
            "(Lord of the Mysteries)"
        ),
        "#fandoms": (
            "诡秘之主 - 爱潜水的乌贼 | Lord of the Mysteries - Cuttlefish that Loves "
            "Diving"
        ),
        "#freeformtags": (
            "Crack Treated Seriously,Fluff,POV Third Person,i just felt "
            "compelled to tag that with my history,mostly gen some minor "
            "background leo(og)klein and merlymon ig,not tagging anyone "
            "else in specific pretty much everyone appears"
        ),
        "#rating": "General Audiences",
        "#series01": "mysteries of the lord variety [11]",
        "#ships": "Mr． Fool & Tarot Club (Lord of the Mysteries)",
        "#status": "In-Progress",
        "#warnings": "No Archive Warnings Apply",
        "#words": 2464,
        "series": "Doth the Worm hath Sentience? [4]",
        "tags": "",
    }
