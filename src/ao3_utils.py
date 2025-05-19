# encoding: utf-8
from ao3 import AO3

AO3_SERIES_KEYS = ["series00", "series01", "series02", "series03"]


def get_ao3_bookmark_urls(
    cookie, expand_series, max_count, user, oldest_date, sort_by_updated
):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        _work_url_from_id(work_id)
        for work_id in api.user.bookmarks_ids(
            max_count, expand_series, oldest_date, sort_by_updated
        )
    ]
    return set(urls)


def get_ao3_users_work_urls(cookie, max_count, user, username, oldest_date):
    # user is the user to sign in as; username is the author to get work urls for.
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        _work_url_from_id(work_id)
        for work_id in api.author(username).work_ids(max_count, oldest_date)
    ]
    return set(urls)


def get_ao3_gift_urls(cookie, max_count, user, oldest_date):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        _work_url_from_id(work_id)
        for work_id in api.user.gift_ids(max_count, oldest_date)
    ]
    return set(urls)


def get_ao3_marked_for_later_urls(cookie, max_count, user, oldest_date):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        _work_url_from_id(work_id)
        for work_id in api.user.marked_for_later_ids(max_count, oldest_date)
    ]
    return set(urls)


def get_ao3_work_subscription_urls(cookie, max_count, user, oldest_date=None):
    """Get urls of works that the user is subscribed to.

    Using oldest_date is slow, because we have to load every work page and
    check its date to decide if we keep it.
    """

    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)

    if oldest_date:
        urls = []
        for work_id in api.user.work_subscription_ids(max_count):
            _append_work_id_if_newer_than_given_date(api, oldest_date, urls, work_id)

        return set(urls)

    urls = [
        _work_url_from_id(work_id)
        for work_id in api.user.work_subscription_ids(max_count)
    ]

    return set(urls)


def _append_work_id_if_newer_than_given_date(api, oldest_date, urls, work_id):
    work = api.work(work_id)
    if work.completed > oldest_date.date():
        urls.append(work.url)


def _work_url_from_id(work_id):
    return f"https://archiveofourown.org/works/{work_id}"


def get_ao3_series_subscription_urls(cookie, max_count, user, oldest_date=None):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    series_ids = api.user.series_subscription_ids(max_count)

    urls = []
    for s in series_ids:
        urls += [
            _work_url_from_id(work_id)
            for work_id in api.series(s).work_ids(max_count, oldest_date)
        ]

    return set(urls)


def get_ao3_user_subscription_urls(cookie, max_count, user, oldest_date=None):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    user_ids = api.user.user_subscription_ids(max_count)

    urls = []
    for u in user_ids:
        print(u)
        urls += [
            _work_url_from_id(work_id)
            for work_id in api.author(u).works_count(max_count, oldest_date)
        ]

    return set(urls)


def get_ao3_series_work_urls(cookie, max_count, user, series_id, oldest_date=None):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)

    urls = [
        _work_url_from_id(work_id)
        for work_id in api.series(series_id).work_ids(max_count, oldest_date)
    ]

    return set(urls)


def get_ao3_collection_work_urls(
    cookie, max_count, user, collection_id, oldest_date=None
):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)

    urls = [
        _work_url_from_id(work_id)
        for work_id in api.collection(collection_id).work_ids(max_count, oldest_date)
    ]

    return set(urls)


def get_ao3_subscribed_users_work_counts(user, cookie):
    api = AO3()
    api.login(user, cookie)
    user_ids = api.user.user_subscription_ids()

    counts = {}
    for username in user_ids:
        counts[username] = api.author(username).works_count()

    return counts


def get_ao3_subscribed_series_work_stats(user, cookie):
    api = AO3()
    api.login(user, cookie)
    series_ids = api.user.series_subscription_ids()

    stats = {}
    for s in series_ids:
        stats[s] = api.series(s).info()

    return stats
