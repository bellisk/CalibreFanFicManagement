from datetime import datetime
from unittest.mock import MagicMock, patch

from ao3 import AO3
from src import ao3_utils

api = AO3()


@patch("src.ao3_utils.AO3")
def test_get_ao3_bookmark_urls(mock_ao3):
    mock_ao3().user.bookmarks_ids.return_value = ["1", "2", "3"]

    urls = ao3_utils.get_ao3_bookmark_urls(
        cookie="cookie",
        expand_series=True,
        max_count=10,
        user="testuser",
        oldest_date="01.01.2020",
        sort_by_updated=True,
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3")
def test_get_ao3_users_work_urls(mock_ao3):
    mock_ao3().users_work_ids.return_value = ["1", "2", "3"]

    urls = ao3_utils.get_ao3_users_work_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        username="testuser2",
        oldest_date="01.01.2020",
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3")
def test_get_ao3_gift_urls(mock_ao3):
    mock_ao3().user.gift_ids.return_value = ["1", "2", "3"]

    urls = ao3_utils.get_ao3_gift_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        oldest_date="01.01.2020",
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3")
def test_get_ao3_marked_for_later_urls(mock_ao3):
    mock_ao3().user.marked_for_later_ids.return_value = ["1", "2", "3"]

    urls = ao3_utils.get_ao3_marked_for_later_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        oldest_date="01.01.2020",
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3")
def test_get_ao3_work_subscription_urls(mock_ao3):
    mock_ao3().user.work_subscription_ids.return_value = ["1", "2", "3"]

    def get_mock_work(work_id):
        mock_work = MagicMock(url="https://archiveofourown.org/works/" + work_id)
        mock_work.completed = datetime.strptime("2024-01-01", "%Y-%m-%d").date()
        return mock_work

    mock_ao3().work.side_effect = get_mock_work

    urls = ao3_utils.get_ao3_work_subscription_urls(
        cookie="testcookie",
        max_count=10,
        user="testuser",
        oldest_date=datetime.strptime("01.01.2020", "%d.%m.%Y"),
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3")
def test_get_ao3_series_subscription_urls(mock_ao3):
    mock_ao3().user.series_subscription_ids.return_value = ["1", "2", "3"]

    def mock_series_work_ids(series_id, max_count=0, oldest_date=None):
        return [series_id + "1", series_id + "2", series_id + "3"]

    mock_ao3().series_work_ids.side_effect = mock_series_work_ids

    urls = ao3_utils.get_ao3_series_subscription_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        oldest_date="01.01.2020",
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


@patch("src.ao3_utils.AO3")
def test_get_ao3_user_subscription_urls(mock_ao3):
    mock_ao3().user.user_subscription_ids.return_value = ["user1", "user2", "user3"]

    def mock_users_work_ids(username, max_count=0, oldest_date=None):
        return [username[-1] + "1", username[-1] + "2", username[-1] + "3"]

    mock_ao3().users_work_ids.side_effect = mock_users_work_ids

    urls = ao3_utils.get_ao3_user_subscription_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        oldest_date="01.01.2020",
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


@patch("src.ao3_utils.AO3")
def test_get_ao3_series_work_urls(mock_ao3):
    mock_ao3().series_work_ids.return_value = ["1", "2", "3"]

    urls = ao3_utils.get_ao3_series_work_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        series_id="123",
        oldest_date="01.01.2020",
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3")
def test_get_ao3_collection_work_urls(mock_ao3):
    mock_ao3().collection_work_ids.return_value = ["1", "2", "3"]

    urls = ao3_utils.get_ao3_collection_work_urls(
        cookie="cookie",
        max_count=10,
        user="testuser",
        collection_id="123",
        oldest_date="01.01.2020",
    )

    assert urls == {
        "https://archiveofourown.org/works/1",
        "https://archiveofourown.org/works/2",
        "https://archiveofourown.org/works/3",
    }


@patch("src.ao3_utils.AO3")
def test_get_ao3_subscribed_users_work_counts(mock_ao3):
    mock_ao3().user.user_subscription_ids.return_value = ["user1", "user2", "user3"]

    def mock_users_works_counts(username):
        return int(username[-1]) * 10

    mock_ao3().users_works_count.side_effect = mock_users_works_counts

    counts = ao3_utils.get_ao3_subscribed_users_work_counts(
        user="testuser", cookie="testcookie"
    )

    assert counts == {"user1": 10, "user2": 20, "user3": 30}


@patch("src.ao3_utils.AO3")
def test_get_ao3_subscribed_series_work_stats(mock_ao3):
    mock_ao3().user.series_subscription_ids.return_value = ["1", "2", "3"]

    def mock_series_infos(series):
        return {"Title": "Series " + series}

    mock_ao3().series_info.side_effect = mock_series_infos

    stats = ao3_utils.get_ao3_subscribed_series_work_stats(
        user="testuser", cookie="testcookie"
    )

    assert stats == {
        "1": {"Title": "Series 1"},
        "2": {"Title": "Series 2"},
        "3": {"Title": "Series 3"},
    }
