import datetime
from argparse import Namespace

import pytest

from src.exceptions import InvalidConfig
from src.get_urls import get_all_sources_for_last_updated_file, get_oldest_date


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
    [
        {"sources": []},
        {
            "sources": {},
            "usernames": {},
            "collections": {},
            "series": {},
        },
    ],
    [
        {"sources": ["bookmarks"]},
        {
            "sources": {"bookmarks": None},
            "usernames": {},
            "collections": {},
            "series": {},
        },
    ],
    [
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
    ],
    [
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
    ],
    [
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
    ],
    [
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
    ],
    [
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
    ],
]


@pytest.mark.parametrize("extra_options,expected", get_oldest_date_test_data)
def test_get_oldest_date(extra_options, expected):
    # We start with some default options and just add extra things to test.
    options = Namespace(
        sources=[],
        usernames=[],
        series=[],
        collections=[],
        since=None,
        since_last_update=False,
        last_update_file="tests/fixtures/last_update_nonexistent.json",
    )
    for o, v in extra_options.items():
        setattr(options, o, v)

    assert get_oldest_date(options) == expected


get_oldest_date_test_data_exceptions = [
    [
        {
            "sources": ["bookmarks", "file"],
            "since_last_update": True,
            "last_update_file": "tests/fixtures/last_update_invalid.json",
        },
        InvalidConfig,
        "tests/fixtures/last_update_invalid.json should contain valid json",
    ]
]


@pytest.mark.parametrize(
    "extra_options,exception,message", get_oldest_date_test_data_exceptions
)
def test_get_oldest_date_expect_exceptions(extra_options, exception, message):
    # We start with some default options and just add extra things to test.
    options = Namespace(
        sources=[],
        usernames=[],
        series=[],
        collections=[],
        since=None,
        since_last_update=False,
        last_update_file="tests/fixtures/last_update_nonexistent.json",
    )
    for o, v in extra_options.items():
        setattr(options, o, v)

    with pytest.raises(exception, match=message):
        get_oldest_date(options)
