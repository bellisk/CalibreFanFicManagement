import json
import os.path
import re
import time
from random import randint
from unittest.mock import patch

from src import analyse, options

from .mock_ao3 import MockAO3

valid_config_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "fixtures", "valid_config.ini"
)


def _get_options(analysis_type):
    args = [
        "fanficmanagement.py",
        "analyse",
        "-C",
        valid_config_path,
        "--analysis-type",
        analysis_type,
    ]
    with patch("sys.argv", args):
        return options.set_up_options()


def mock_check_library(path):
    return f'--with-library "{path}"'


def mocked_localtime():
    return time.struct_time((2024, 4, 13, 9, 0, 0, 5, 104, 1))


def mock_check_subprocess_output(command, *args, **kwargs):
    if command.startswith("calibredb search author"):
        return "1,2,3,4,5,6,7,8,9,10"
    elif command.startswith("calibredb list --search author"):
        result = [
            {
                "*identifier": f"https://archiveofourown.org/works/"
                f"{randint(100, 100000)}",
                "id": randint(0, 10000),
            }
            for i in range(10)
        ]
        return bytes(json.dumps(result), "utf-8")
    elif command.startswith("calibredb search allseries"):
        return "1,2"
    elif command.startswith("calibredb list --search allseries"):
        pattern = r"Series (\d)"
        m = re.search(pattern, command)
        if m is not None:
            m.group(1)
            result = [
                {
                    "*identifier": f"https://archiveofourown.org/works/{m.group(1)}{i}",
                    "id": 2,
                }
                for i in range(2)
            ]
            return bytes(json.dumps(result), "utf-8")
    print(command)


@patch("src.calibred.check_subprocess_output", mock_check_subprocess_output)
@patch("src.ao3_utils.AO3", MockAO3)
@patch("src.analyse.check_library_and_get_path", mock_check_library)
class TestAnalysisClass(object):
    def teardown_method(self):
        analysis_filepath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "fixtures", "analysis"
        )
        for f in os.listdir(analysis_filepath):
            os.remove(os.path.join(analysis_filepath, f))

    def test_analyse_user_subscriptions(self, capsys):
        command, namespace = _get_options(options.SOURCE_USER_SUBSCRIPTIONS)

        with patch("src.utils.localtime", mocked_localtime):
            analyse.analyse(namespace)

        captured = capsys.readouterr()

        # mock_check_output tells us that every author has 10 works in Calibre.
        # MockAO3 tells us that user2 and user3 have 20 and 30 fics on AO3, so they
        # should be reported here.
        users_msg = (
            "\x1b[1m04/13/2024 09:00:00\x1b[0m: \t \x1b[95mSubscribed users "
            "who have fewer works on Calibre than on AO3:"
        )

        for username in ["user2", "user3"]:
            users_msg += (
                f"\x1b[0m\n\x1b[1m04/13/2024 09:00:00\x1b[0m: \t \x1b[94m\t{username}"
            )

        assert users_msg in captured.out

        # MockAO3 returns 5 work urls for each user, which makes 10 in total.
        urls_found_msg = "Found 10 urls to import"
        assert urls_found_msg in captured.out

    def test_analyse_series_subscriptions(self, capsys):
        command, namespace = _get_options(options.SOURCE_SERIES_SUBSCRIPTIONS)

        with patch("src.utils.localtime", mocked_localtime):
            analyse.analyse(namespace)

        captured = capsys.readouterr()

        # mock_check_output tells us that every series has 2 works in Calibre.
        # MockAO3 tells us that series 3, 4, and 5 have 3, 4, and 5 works on AO3, so
        # they should be reported here.
        series_msg = (
            "\x1b[1m04/13/2024 09:00:00\x1b[0m: \t \x1b[95mSubscribed users "
            "who have fewer works on Calibre than on AO3:"
        )
        for series_id in ["Series 3", "Series 4", "Series 5"]:
            series_msg += (
                f"\x1b[0m\n\x1b[1m04/13/2024 09:00:00\x1b[0m: \t \x1b[94m\t{series_id}"
            )

        # We need to import 1 url for series 3, 2 for series 4, and 3 for series 5.
        urls_found_msg = "Found 6 urls to import"
        assert urls_found_msg in captured.out
