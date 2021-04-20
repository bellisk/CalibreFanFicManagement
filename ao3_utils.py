# encoding: utf-8

from ao3 import AO3


def get_ao3_bookmark_urls(cookie, expand_series, max_count, user):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = [
        "https://archiveofourown.org/works/%s" % work_id
        for work_id in api.user.bookmarks_ids(max_count, expand_series)
    ]
    return set(urls)


def get_ao3_bookmarked_works(cookie, expand_series, max_count, user):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    return api.user.bookmarks(max_count, expand_series)


def get_ao3_history_works(cookie, expand_series, max_count, user):
    api = AO3()
    api.login(user, cookie)
    history = api.user.reading_history()
    works = []
    n = 0
    while n < max_count:
        works.append(next(history))
        n += 1

    return works

