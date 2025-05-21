from argparse import Namespace

from src.get_urls import get_all_sources_for_last_updated_file


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
