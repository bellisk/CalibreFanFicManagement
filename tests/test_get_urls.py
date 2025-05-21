import datetime
import json
import os
import shutil
from argparse import Namespace
from unittest.mock import patch

import pytest

from src.exceptions import InvalidConfig
from src.get_urls import (
    get_all_sources_for_last_updated_file,
    get_oldest_date,
    update_last_updated_file,
)


def get_options():
    # A default set of options that can be updated for testing
    return Namespace(
        sources=[],
        usernames=[],
        series=[],
        collections=[],
        since=None,
        since_last_update=False,
        last_update_file="tests/fixtures/last_update_nonexistent.json",
    )


def test_get_all_sources_for_last_updated_file():
    options = Namespace(
        sources=["bookmarks", "file", "imap", "usernames", "collections", "series"],
        usernames=["testuser1", "testuser2"],
        collections=["collection1"],
        series=["series1", "series2", "series3"],
    )

    sources_for_file = get_all_sources_for_last_updated_file(options)

    assert sources_for_file == {
        "sources": ["bookmarks", "file", "imap", "usernames", "collections", "series"],
        "usernames": ["testuser1", "testuser2"],
        "series": ["series1", "series2", "series3"],
        "collections": ["collection1"],
    }


get_oldest_date_test_data = [
    pytest.param(
        {"sources": []},
        {
            "sources": {},
            "usernames": {},
            "collections": {},
            "series": {},
        },
        id="No sources, no since date",
    ),
    pytest.param(
        {"sources": ["bookmarks"]},
        {
            "sources": {"bookmarks": None},
            "usernames": {},
            "collections": {},
            "series": {},
        },
        id="Single source, no since date",
    ),
    pytest.param(
        {
            "sources": ["bookmarks", "collections", "usernames", "series"],
            "since": "01.01.2025",
            "collections": ["testcollection1"],
            "usernames": ["testuser1", "testuser2"],
            "series": ["testseries1", "testseries2", "testseries3"],
        },
        {
            "sources": {
                "bookmarks": datetime.datetime(2025, 1, 1),
                "collections": datetime.datetime(2025, 1, 1),
                "series": datetime.datetime(2025, 1, 1),
                "usernames": datetime.datetime(2025, 1, 1),
            },
            "usernames": {
                "testuser1": datetime.datetime(2025, 1, 1),
                "testuser2": datetime.datetime(2025, 1, 1),
            },
            "collections": {"testcollection1": datetime.datetime(2025, 1, 1)},
            "series": {
                "testseries1": datetime.datetime(2025, 1, 1),
                "testseries2": datetime.datetime(2025, 1, 1),
                "testseries3": datetime.datetime(2025, 1, 1),
            },
        },
        id="Multiple sources, since date",
    ),
    pytest.param(
        {
            "sources": ["bookmarks", "collections", "usernames", "series"],
            "since_last_update": True,
            "last_update_file": "tests/fixtures/last_update_valid.json",
            "collections": ["testcollection1"],
            "usernames": ["testuser1", "testuser2"],
            "series": ["testseries1", "testseries2", "testseries3"],
        },
        {
            "sources": {
                "bookmarks": datetime.datetime(2025, 2, 1),
                "collections": datetime.datetime(2025, 1, 1),
                "series": datetime.datetime(2025, 3, 1),
                "usernames": datetime.datetime(2025, 2, 1),
            },
            "usernames": {
                "testuser1": datetime.datetime(2025, 1, 1),
                "testuser2": datetime.datetime(2025, 2, 1),
            },
            "collections": {"testcollection1": datetime.datetime(2025, 1, 1)},
            "series": {
                "testseries1": datetime.datetime(2025, 1, 1),
                "testseries2": datetime.datetime(2025, 2, 1),
                "testseries3": datetime.datetime(2025, 3, 1),
            },
        },
        id="Multiple sources, no since date, since_last_update, valid last_update_file",
    ),
    pytest.param(
        {
            "sources": ["bookmarks", "collections", "usernames", "series", "file"],
            "since_last_update": True,
            "last_update_file": "tests/fixtures/last_update_valid.json",
            "since": "01.04.2025",
            "collections": ["testcollection1"],
            "usernames": ["testuser1", "testuser2"],
            "series": ["testseries1", "testseries2", "testseries3"],
        },
        {
            "sources": {
                "bookmarks": datetime.datetime(2025, 2, 1),
                "collections": datetime.datetime(2025, 1, 1),
                "file": datetime.datetime(2025, 4, 1),
                "series": datetime.datetime(2025, 3, 1),
                "usernames": datetime.datetime(2025, 2, 1),
            },
            "usernames": {
                "testuser1": datetime.datetime(2025, 1, 1),
                "testuser2": datetime.datetime(2025, 2, 1),
            },
            "collections": {"testcollection1": datetime.datetime(2025, 1, 1)},
            "series": {
                "testseries1": datetime.datetime(2025, 1, 1),
                "testseries2": datetime.datetime(2025, 2, 1),
                "testseries3": datetime.datetime(2025, 3, 1),
            },
        },
        id="Multiple sources, since date, since_last_update, valid last_update_file",
    ),
    pytest.param(
        {
            "sources": ["bookmarks", "file"],
            "since_last_update": True,
            "last_update_file": "tests/fixtures/last_update_empty.json",
        },
        {
            "collections": {},
            "series": {},
            "sources": {
                "bookmarks": None,
                "file": None,
            },
            "usernames": {},
        },
        id="Multiple sources, no since date, since_last_update, empty last_update_file",
    ),
    pytest.param(
        {
            "sources": ["bookmarks", "file"],
            "since_last_update": True,
            "last_update_file": "tests/fixtures/last_update_empty.json",
            "since": "01.04.2025",
        },
        {
            "collections": {},
            "series": {},
            "sources": {
                "bookmarks": datetime.datetime(2025, 4, 1),
                "file": datetime.datetime(2025, 4, 1),
            },
            "usernames": {},
        },
        id="Multiple sources, since date, since_last_update, empty last_update_file",
    ),
]


@pytest.mark.parametrize("extra_options,expected", get_oldest_date_test_data)
def test_get_oldest_date(extra_options, expected):
    options = get_options()

    for o, v in extra_options.items():
        setattr(options, o, v)

    assert get_oldest_date(options) == expected


get_oldest_date_test_data_exceptions = [
    pytest.param(
        {
            "sources": ["bookmarks", "file"],
            "since_last_update": True,
            "last_update_file": "tests/fixtures/last_update_invalid.json",
        },
        InvalidConfig,
        "tests/fixtures/last_update_invalid.json should contain valid json",
        id="Multiple sources, no since date, since_last_update, "
        "invalid last_update_file",
    )
]


@pytest.mark.parametrize(
    "extra_options,exception,message", get_oldest_date_test_data_exceptions
)
def test_get_oldest_date_expect_exceptions(extra_options, exception, message):
    options = get_options()

    for o, v in extra_options.items():
        setattr(options, o, v)

    with pytest.raises(exception, match=message):
        get_oldest_date(options)


update_last_updated_file_data = [
    pytest.param(
        {
            "sources": ["bookmarks", "file"],
            "last_update_file": "tests/fixtures/last_update_to_update.json",
        },
        {
            "sources": {
                "bookmarks": "01.05.2025",
                "collections": "01.01.2025",
                "usernames": "01.02.2025",
                "series": "01.03.2025",
                "file": "01.05.2025",
            },
            "usernames": {"testuser1": "01.01.2025", "testuser2": "01.02.2025"},
            "collections": {"testcollection1": "01.01.2025"},
            "series": {
                "testseries1": "01.01.2025",
                "testseries2": "01.02.2025",
                "testseries3": "01.03.2025",
            },
        },
        id="Write file with current date for sources bookmarks and file",
    )
]


@pytest.mark.parametrize("extra_options,expected", update_last_updated_file_data)
def test_update_last_updated_file(extra_options, expected):
    shutil.copyfile(
        "tests/fixtures/last_update_valid.json",
        "tests/fixtures/last_update_to_update.json",
    )

    options = get_options()

    for o, v in extra_options.items():
        setattr(options, o, v)

    with patch("src.get_urls.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime.datetime(2025, 5, 1)
        update_last_updated_file(options)

    with open("tests/fixtures/last_update_to_update.json", "r") as f:
        result = json.loads(f.read())

    assert result == expected

    os.remove("tests/fixtures/last_update_to_update.json")
