# encoding: utf-8

from ao3 import AO3


def get_ao3_bookmark_urls(
    cookie, expand_series, max_count, user, oldest_date, sort_by_updated
):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        "https://archiveofourown.org/works/%s" % work_id
        for work_id in api.user.bookmarks_ids(
            max_count, expand_series, oldest_date, sort_by_updated
        )
    ]
    return set(urls)


def get_ao3_marked_for_later_urls(cookie, max_count, user, oldest_date):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        "https://archiveofourown.org/works/%s" % work_id
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
            work = api.work(work_id)
            if work.completed > oldest_date.date():
                urls.append(work.url)

        return set(urls)

    urls = [
        "https://archiveofourown.org/works/%s" % work_id
        for work_id in api.user.work_subscription_ids(max_count)
    ]

    return set(urls)


def get_ao3_series_subscription_urls(cookie, max_count, user, oldest_date=None):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    series_ids = api.user.series_subscription_ids(max_count)

    urls = []
    for s in series_ids:
        urls += [
            "https://archiveofourown.org/works/%s" % work_id
            for work_id in api.series_work_ids(s, oldest_date)
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
            "https://archiveofourown.org/works/%s" % work_id
            for work_id in api.users_work_ids(u, oldest_date)
        ]

    return set(urls)
