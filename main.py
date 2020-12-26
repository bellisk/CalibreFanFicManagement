# coding: utf-8

from ao3 import AO3
from optparse import OptionParser

api = AO3()


def login(username, cookie):
    api.login(username, cookie)


def fetch_bookmarks(max_count, expand_series):
    bookmark_ids = api.user.bookmarks(max_count, expand_series)
    return bookmark_ids


if __name__ == '__main__':
    option_parser = OptionParser(usage="usage: %prog [flags]")

    option_parser.add_option(
        '-u',
        '--user',
        action='store',
        dest='user',
        help='AO3 username. Required.'
    )

    option_parser.add_option(
        '-c',
        '--cookie',
        action='store',
        dest='cookie',
        help='Contents of _otwarchive_session cookie. Required.'
    )

    option_parser.add_option(
        '-m',
        '--max-count',
        action='store',
        dest='max_count',
        default=20,
        help='Maximum number of bookmarks to get from AO3. Default = 20 (one page of bookmarks).'
    )

    option_parser.add_option(
        '-e',
        '--expand-series',
        action='store',
        dest='expand_series',
        default=False,
        help='Whether to get all works from a bookmarked series. Default = false.'
    )

    (options, args) = option_parser.parse_args()

    if not (options.user or options.cookie):
        raise ValueError("User or Cookie not given")

    login(options.user, options.cookie)
    print(fetch_bookmarks(options.max_count, options.expand_series))
