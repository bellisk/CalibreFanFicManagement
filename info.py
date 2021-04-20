# encoding: utf-8

from ao3_utils import get_ao3_bookmark_urls, get_ao3_history
from utils import log, touch


def bookmarks(options):
    if not (options.user and options.cookie):
        raise ValueError("User and Cookie are required for getting info from AO3")

    inout_file = options.input
    touch(inout_file)

    try:
        urls = get_ao3_bookmark_urls(
            options.cookie, options.expand_series, options.max_count, options.user
        )
    except BaseException:
        with open(inout_file, "w") as fp:
            for cur in urls:
                fp.write("{}\n".format(cur))
        return

    if not urls:
        return
    log("Bookmark URLs found ({}):".format(len(urls)), "HEADER")
    for url in urls:
        log("\t{}".format(url), "BLUE")


def history(options):
    if not (options.user and options.cookie):
        raise ValueError("User and Cookie are required for getting info from AO3")

    inout_file = options.input
    touch(inout_file)

    try:
        urls = get_ao3_history(
            options.cookie, options.expand_series, options.max_count, options.user
        )
    except BaseException as e:
        with open(inout_file, "w") as fp:
            for cur in urls:
                fp.write("{}\n".format(cur))
        return

    if not urls:
        return
    log("URLs to parse ({}):".format(len(urls)), "HEADER")
    for url in urls:
        print(url)
        # log("\t{}".format(str(url)), "BLUE")
