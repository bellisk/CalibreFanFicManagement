# encoding: utf-8

from ao3 import AO3


def get_ao3_bookmark_urls(cookie, expand_series, max_count, user, oldest_date):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        "https://archiveofourown.org/works/%s" % work_id
        for work_id in api.user.bookmarks_ids(max_count, expand_series, oldest_date)
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
