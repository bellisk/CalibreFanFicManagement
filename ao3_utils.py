# encoding: utf-8

from ao3 import AO3


def get_ao3_bookmark_urls(cookie, expand_series, max_count, user):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = ['https://archiveofourown.org/works/%s'
            % work_id for work_id in
            api.user.bookmarks_ids(max_count, expand_series)]
    return set(urls)
