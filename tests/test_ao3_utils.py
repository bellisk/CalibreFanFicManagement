from datetime import datetime
from unittest.mock import patch

from src import ao3_utils

from .mock_ao3 import MockAO3

oldest_date = datetime.strptime("01.01.2020", "%d.%m.%Y")


def test_get_ao3_bookmark_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_bookmark_urls(
        api,
        expand_series=True,
        max_count=3,
        oldest_date=oldest_date,
        sort_by_updated=True,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


def test_get_ao3_users_work_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_users_work_urls(
        api,
        username="test_user2",
        max_count=3,
        oldest_date=oldest_date,
    )

    print(urls)

    assert urls == {
        "https://archiveofourown.org/works/21",
        "https://archiveofourown.org/works/22",
        "https://archiveofourown.org/works/23",
    }


def test_get_ao3_gift_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_gift_urls(api, max_count=3, oldest_date=oldest_date)

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


def test_get_ao3_marked_for_later_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_marked_for_later_urls(
        api, max_count=3, oldest_date=oldest_date
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3", MockAO3)
def test_get_ao3_work_subscription_urls_no_oldest_date():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_work_subscription_urls(api, max_count=5, oldest_date=None)

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
        "https://archiveofourown.org/works/4",
        "https://archiveofourown.org/works/5",
    }


def test_get_ao3_work_subscription_urls_with_oldest_date():
    # We only want works published *after* 01.01.2023, not including that date
    oldest_work_date = datetime.strptime("01.01.2023", "%d.%m.%Y")

    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_work_subscription_urls(
        api, max_count=5, oldest_date=oldest_work_date
    )

    assert urls == {
        "https://archiveofourown.org/works/4",
        "https://archiveofourown.org/works/5",
    }


def test_get_ao3_series_subscription_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_series_subscription_urls(
        api, max_count=3, oldest_date=oldest_date
    )

    assert urls == {
        "https://archiveofourown.org/works/10",
        "https://archiveofourown.org/works/20",
        "https://archiveofourown.org/works/21",
        "https://archiveofourown.org/works/30",
        "https://archiveofourown.org/works/31",
        "https://archiveofourown.org/works/32",
    }


def test_get_ao3_user_subscription_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_user_subscription_urls(
        api, max_count=3, oldest_date=oldest_date
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
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_user_subscription_urls(
        api, max_count=0, oldest_date=oldest_date
    )

    assert urls == set([])


def test_get_ao3_series_work_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_series_work_urls(
        api,
        max_count=3,
        series_id="3",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/30",
        "https://archiveofourown.org/works/31",
        "https://archiveofourown.org/works/32",
    }


def test_get_ao3_collection_work_urls():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    urls = ao3_utils.get_ao3_collection_work_urls(
        api,
        max_count=10,
        collection_id="123",
        oldest_date=oldest_date,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


def test_get_ao3_subscribed_users_work_counts():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    counts = ao3_utils.get_ao3_subscribed_users_work_counts(api)

    assert counts == {"user1": 10, "user2": 20, "user3": 30}


def test_get_ao3_subscribed_series_work_stats():
    api = MockAO3()
    api.login("test_user", "test_cookie")
    stats = ao3_utils.get_ao3_subscribed_series_work_stats(api)

    assert stats == {
        "1": {"Title": "Series 1", "Works": "1"},
        "2": {"Title": "Series 2", "Works": "2"},
        "3": {"Title": "Series 3", "Works": "3"},
        "4": {"Title": "Series 4", "Works": "4"},
        "5": {"Title": "Series 5", "Works": "5"},
    }
