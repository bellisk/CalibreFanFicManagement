import os.path
from argparse import Namespace
from unittest.mock import patch

from src import options

valid_config_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "fixtures", "valid_config.ini"
)


def test_get_config_file_arguments():
    namespace = Namespace(config=valid_config_path, command="download")

    config_file_args = options.get_config_file_arguments(namespace)

    assert config_file_args == [
        "download",
        "--user",
        "testuser",
        "--cookie",
        "testcookie",
        "--max-count",
        "10",
        "--expand-series",
        "--sources",
        "file,bookmarks,later,works,gifts,all_subscriptions",
        "--since-last-update",
        "--library",
        "tests/fixtures/Calibre Fanfic Library",
        "--input",
        "tests/fixtures/fanfiction.txt",
        "--fanficfare-config",
        "tests/fixtures/personal.ini",
        "--last-update-file",
        "tests/fixtures/last_update.json",
        "--analysis-dir",
        "tests/fixtures/analysis",
        "--analysis-type",
        "incomplete_works",
        "--live",
    ]


def test_set_up_options_from_config_file():
    args = ["fanficmanagement.py", "download", "-C", valid_config_path]
    with patch("sys.argv", args):
        command, namespace = options.set_up_options()

    assert command == "download"
    assert vars(namespace) == {
        "command": "download",
        "user": "testuser",
        "cookie": "testcookie",
        "use_browser_cookie": False,
        "sources": [
            "file",
            "bookmarks",
            "later",
            "works",
            "gifts",
            "all_subscriptions",
            "series_subscriptions",
            "user_subscriptions",
            "work_subscriptions",
        ],
        "max_count": 10,
        "usernames": [],
        "series": [],
        "collections": [],
        "since": None,
        "since_last_update": True,
        "expand_series": True,
        "force": False,
        "input": "tests/fixtures/fanfiction.txt",
        "library": "tests/fixtures/Calibre Fanfic Library",
        "dry_run": False,
        "config": valid_config_path,
        "fanficfare_config": "tests/fixtures/personal.ini",
        "live": True,
        "last_update_file": "tests/fixtures/last_update.json",
        "analysis_dir": "tests/fixtures/analysis",
        "analysis_type": ["incomplete_works"],
        "fix": False,
    }


def test_set_up_options_from_cli():
    args = [
        "fanficmanagement.py",
        "download",
        "-u",
        "testuser",
        "-c",
        "testcookie",
        "-m",
        "20",
        "--collections",
        "testcollection1,testcollection2",
    ]
    with patch("sys.argv", args):
        command, namespace = options.set_up_options()

    assert command == "download"
    assert vars(namespace) == {
        "command": "download",
        "user": "testuser",
        "cookie": "testcookie",
        "use_browser_cookie": False,
        "sources": ["file", "bookmarks", "later"],
        "max_count": 20,
        "usernames": [],
        "series": [],
        "collections": ["testcollection1", "testcollection2"],
        "since": None,
        "since_last_update": False,
        "expand_series": False,
        "force": False,
        "input": "fanfiction.txt",
        "library": None,
        "dry_run": False,
        "config": None,
        "fanficfare_config": None,
        "live": False,
        "last_update_file": "last_update.json",
        "analysis_dir": "analysis",
        "analysis_type": [
            "user_subscriptions",
            "series_subscriptions",
            "incomplete_works",
        ],
        "fix": False,
    }


def test_set_up_options_from_config_file_and_override_with_cli():
    args = [
        "fanficmanagement.py",
        "download",
        "-C",
        valid_config_path,
        "-u",
        "newtestuser",
        "-c",
        "newtestcookie",
        "-m",
        "30",
        "--source",
        "works,gifts,later,collections",
        "--collections",
        "testcollection1,testcollection2",
    ]
    with patch("sys.argv", args):
        command, namespace = options.set_up_options()

    assert command == "download"
    assert vars(namespace) == {
        "command": "download",
        "user": "newtestuser",
        "cookie": "newtestcookie",
        "use_browser_cookie": False,
        "sources": ["works", "gifts", "later", "collections"],
        "max_count": 30,
        "usernames": [],
        "series": [],
        "collections": ["testcollection1", "testcollection2"],
        "since": None,
        "since_last_update": True,
        "expand_series": True,
        "force": False,
        "input": "tests/fixtures/fanfiction.txt",
        "library": "tests/fixtures/Calibre Fanfic Library",
        "dry_run": False,
        "config": valid_config_path,
        "fanficfare_config": "tests/fixtures/personal.ini",
        "live": True,
        "last_update_file": "tests/fixtures/last_update.json",
        "analysis_dir": "tests/fixtures/analysis",
        "analysis_type": ["incomplete_works"],
        "fix": False,
    }
