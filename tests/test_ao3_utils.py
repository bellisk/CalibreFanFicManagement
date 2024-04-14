from datetime import datetime
from unittest.mock import MagicMock, patch

from ao3 import AO3
from src import ao3_utils
from .mock_ao3 import MockAO3

api = AO3()
oldest_date = datetime.strptime("01.01.2020", "%d.%m.%Y")


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_bookmark_urls():
    urls = ao3_utils.get_ao3_bookmark_urls(
        cookie="cookie",
        expand_series=True,
        max_count=3,
        user="testuser",
        oldest_date=oldest_date,
        sort_by_updated=True,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


def test_get_ao3_bookmark_urls_max_count_zero():
    urls = ao3_utils.get_ao3_bookmark_urls(
        cookie="cookie",
        expand_series=True,
        max_count=0,
        user="testuser",
        oldest_date=oldest_date,
        sort_by_updated=True,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_users_work_urls():
    urls = ao3_utils.get_ao3_users_work_urls(
        cookie="cookie",
        max_count=3,
        user="testuser",
        username="testuser2",
        oldest_date=oldest_date,
    )

    print(urls)

    assert urls == {
        "https://archiveofourown.org/works/21",
        "https://archiveofourown.org/works/22",
        "https://archiveofourown.org/works/23",
    }


def test_get_ao3_users_work_urls_max_count_zero():
    urls = ao3_utils.get_ao3_users_work_urls(
        cookie="cookie",
        max_count=0,
        user="testuser",
        username="testuser2",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_gift_urls():
    urls = ao3_utils.get_ao3_gift_urls(
        cookie="cookie",
        max_count=3,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


def test_get_ao3_gift_urls_max_count_zero():
    urls = ao3_utils.get_ao3_gift_urls(
        cookie="cookie",
        max_count=0,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_marked_for_later_urls():
    urls = ao3_utils.get_ao3_marked_for_later_urls(
        cookie="cookie",
        max_count=3,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


def test_get_ao3_marked_for_later_urls_max_count_zero():
    urls = ao3_utils.get_ao3_marked_for_later_urls(
        cookie="cookie",
        max_count=0,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_work_subscription_urls_no_oldest_date():
    urls = ao3_utils.get_ao3_work_subscription_urls(
        cookie="testcookie",
        max_count=5,
        user="testuser",
        oldest_date=None,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
        "https://archiveofourown.org/works/4",
        "https://archiveofourown.org/works/5",
    }


def test_get_ao3_work_subscription_urls_no_oldest_date_max_count_zero():
    urls = ao3_utils.get_ao3_work_subscription_urls(
        cookie="testcookie",
        max_count=0,
        user="testuser",
        oldest_date=None,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_work_subscription_urls_with_oldest_date():
    # We only want works published *after* 01.01.2023, not including that date
    oldest_work_date = datetime.strptime("01.01.2023", "%d.%m.%Y")

    urls = ao3_utils.get_ao3_work_subscription_urls(
        cookie="testcookie",
        max_count=5,
        user="testuser",
        oldest_date=oldest_work_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/4",
        "https://archiveofourown.org/works/5",
    }


def test_get_ao3_work_subscription_urls_with_oldest_date_max_count_zero():
    urls = ao3_utils.get_ao3_work_subscription_urls(
        cookie="testcookie",
        max_count=0,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_series_subscription_urls():
    urls = ao3_utils.get_ao3_series_subscription_urls(
        cookie="cookie",
        max_count=3,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/11",
        "https://archiveofourown.org/works/12",
        "https://archiveofourown.org/works/13",
        "https://archiveofourown.org/works/21",
        "https://archiveofourown.org/works/22",
        "https://archiveofourown.org/works/23",
        "https://archiveofourown.org/works/31",
        "https://archiveofourown.org/works/32",
        "https://archiveofourown.org/works/33",
    }


def test_get_ao3_series_subscription_urls_max_count_zero():
    urls = ao3_utils.get_ao3_series_subscription_urls(
        cookie="cookie",
        max_count=0,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_user_subscription_urls():
    urls = ao3_utils.get_ao3_user_subscription_urls(
        cookie="cookie",
        max_count=3,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/11",
        "https://archiveofourown.org/works/12",
        "https://archiveofourown.org/works/13",
        "https://archiveofourown.org/works/21",
        "https://archiveofourown.org/works/22",
        "https://archiveofourown.org/works/23",
        "https://archiveofourown.org/works/31",
        "https://archiveofourown.org/works/32",
        "https://archiveofourown.org/works/33",
    }


def test_get_ao3_user_subscription_urls_max_count_zero():
    urls = ao3_utils.get_ao3_user_subscription_urls(
        cookie="cookie",
        max_count=0,
        user="testuser",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_series_work_urls():
    urls = ao3_utils.get_ao3_series_work_urls(
        cookie="cookie",
        max_count=3,
        user="testuser",
        series_id="123",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/1231",
        "https://archiveofourown.org/works/1232",
        "https://archiveofourown.org/works/1233",
    }


def test_get_ao3_series_work_urls_max_count_zero():
    urls = ao3_utils.get_ao3_series_work_urls(
        cookie="cookie",
        max_count=0,
        user="testuser",
        series_id="123",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_collection_work_urls():
    urls = ao3_utils.get_ao3_collection_work_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        collection_id="123",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


def test_get_ao3_collection_work_urls_max_count_zero():
    urls = ao3_utils.get_ao3_collection_work_urls(
        cookie="cookie",
        max_count=0,
        user="testuser",
        collection_id="123",
        oldest_date=oldest_date,
    )

    assert urls == set([])


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_subscribed_users_work_counts():
    counts = ao3_utils.get_ao3_subscribed_users_work_counts(
        user="testuser", cookie="testcookie"
    )

    assert counts == {"user1": 10, "user2": 20, "user3": 30}


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_subscribed_series_work_stats():
    stats = ao3_utils.get_ao3_subscribed_series_work_stats(
        user="testuser", cookie="testcookie"
    )

    assert stats == {
        "1": {"Title": "Series 1"},
        "2": {"Title": "Series 2"},
        "3": {"Title": "Series 3"},
        "4": {"Title": "Series 4"},
        "5": {"Title": "Series 5"},
    }
