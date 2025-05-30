from argparse import ArgumentTypeError, Namespace

import pytest

from src import options


def test_validate_sources_valid():
    namespace = Namespace(sources=["file", "bookmarks"])
    options.validate_sources(namespace)

    assert namespace.sources == ["file", "bookmarks"]


def test_validate_sources_invalid_source():
    namespace = Namespace(sources=["file", "bookmarks", "foobar"])
    with pytest.raises(
        ArgumentTypeError, match="Valid 'sources' options are .* not foobar"
    ):
        options.validate_sources(namespace)


def test_validate_sources_missing_usernames():
    namespace = Namespace(sources=["usernames"], usernames=None)
    with pytest.raises(ArgumentTypeError, match="A list of usernames is required"):
        options.validate_sources(namespace)


def test_validate_sources_missing_series():
    namespace = Namespace(sources=["series"], series=None)
    with pytest.raises(ArgumentTypeError, match="A list of series ids is required"):
        options.validate_sources(namespace)


def test_validate_sources_missing_collections():
    namespace = Namespace(sources=["collections"], collections=None)
    with pytest.raises(ArgumentTypeError, match="A list of collection ids is required"):
        options.validate_sources(namespace)


def test_validate_sources_expand_subscriptions():
    namespace = Namespace(sources=["all_subscriptions"])
    options.validate_sources(namespace)

    assert sorted(namespace.sources) == [
        "all_subscriptions",
        "series_subscriptions",
        "user_subscriptions",
        "work_subscriptions",
    ]


def test_validate_sources_imap_valid():
    namespace = Namespace(
        sources=["imap"],
        email_server="imap.gmail.com",
        email_user="test_email_user",
        email_password="coolpassword",
        email_folder="My AO3 Label",
    )
    options.validate_sources(namespace)

    assert namespace.sources == ["imap"]
    assert namespace.email_server == "imap.gmail.com"
    assert namespace.email_user == "test_email_user"
    assert namespace.email_password == "coolpassword"
    assert namespace.email_folder == "My AO3 Label"


def test_validate_sources_imap_missing_email_options():
    namespace = Namespace(
        sources=["imap"],
    )

    with pytest.raises(
        ArgumentTypeError,
        match="The following options are required when source 'imap' is given",
    ):
        options.validate_sources(namespace)


def test_validate_user():
    namespace = Namespace(user="testuser")
    options.validate_user(namespace)

    assert namespace.user == "testuser"


def test_validate_missing_user():
    namespace = Namespace(user=None)
    with pytest.raises(ArgumentTypeError, match="The argument user is required"):
        options.validate_user(namespace)


def test_validate_cookie_only_cookie():
    namespace = Namespace(cookie="testcookie", use_browser_cookie=False)
    options.validate_cookie(namespace)

    assert namespace.cookie == "testcookie"


def test_validate_cookie_only_use_browser_cookie():
    namespace = Namespace(cookie="testcookie", use_browser_cookie=True)
    options.validate_cookie(namespace)

    assert namespace.use_browser_cookie is True


def test_validate_cookie_both_options():
    namespace = Namespace(cookie="testcookie", use_browser_cookie=True)
    options.validate_cookie(namespace)

    assert namespace.cookie == "testcookie"
    assert namespace.use_browser_cookie is True


def test_validate_cookie_neither_option():
    namespace = Namespace(cookie=None, use_browser_cookie=None)
    with pytest.raises(
        ArgumentTypeError, match="It's required either to pass in a cookie"
    ):
        options.validate_cookie(namespace)


def test_validate_since_valid():
    namespace = Namespace(since="01.01.2025")
    options.validate_since(namespace)

    assert namespace.since == "01.01.2025"


def test_validate_since_invalid():
    namespace = Namespace(since="yesterday")

    with pytest.raises(
        ArgumentTypeError, match="'since' option should have format DD.MM.YYYY"
    ):
        options.validate_since(namespace)


def test_validate_since_none():
    namespace = Namespace(since=None)
    options.validate_since(namespace)

    assert namespace.since is None


def test_validate_analysis_types_valid():
    namespace = Namespace(analysis_type=["user_subscriptions", "incomplete_works"])
    options.validate_analysis_type(namespace)

    assert namespace.analysis_type == ["user_subscriptions", "incomplete_works"]


def test_validate_analysis_types_invalid_source():
    namespace = Namespace(
        analysis_type=["user_subscriptions", "incomplete_works", "foobar"]
    )
    with pytest.raises(
        ArgumentTypeError, match="Valid 'analysis_type' options are .* not foobar"
    ):
        options.validate_analysis_type(namespace)
