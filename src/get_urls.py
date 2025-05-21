import json
import os.path
import sys
from datetime import datetime
from json import JSONDecodeError

from fanficfare.geturls import get_urls_from_imap

from src.ao3_utils import (
    get_ao3_bookmark_urls,
    get_ao3_collection_work_urls,
    get_ao3_gift_urls,
    get_ao3_marked_for_later_urls,
    get_ao3_series_subscription_urls,
    get_ao3_series_work_urls,
    get_ao3_user_subscription_urls,
    get_ao3_users_work_urls,
    get_ao3_work_subscription_urls,
)
from src.exceptions import InvalidConfig, UrlsCollectionException
from src.options import (
    SOURCE_BOOKMARKS,
    SOURCE_COLLECTIONS,
    SOURCE_FILE,
    SOURCE_GIFTS,
    SOURCE_IMAP,
    SOURCE_LATER,
    SOURCE_SERIES,
    SOURCE_SERIES_SUBSCRIPTIONS,
    SOURCE_STDIN,
    SOURCE_USER_SUBSCRIPTIONS,
    SOURCE_USERNAMES,
    SOURCE_WORK_SUBSCRIPTIONS,
    SOURCE_WORKS,
    SOURCES,
)
from src.utils import AO3_DEFAULT_URL, Bcolors, log

LAST_UPDATE_KEYS = [SOURCES, SOURCE_USERNAMES, SOURCE_COLLECTIONS, SOURCE_SERIES]

DATE_FORMAT = "%d.%m.%Y"


def get_all_sources_for_last_updated_file(options):
    return {
        SOURCES: options.sources,
        SOURCE_USERNAMES: options.usernames,
        SOURCE_SERIES: options.series,
        SOURCE_COLLECTIONS: options.collections,
    }


def get_oldest_date(options):
    all_sources = get_all_sources_for_last_updated_file(options)
    if not (options.since or options.since_last_update):
        dates = {}
        for key in LAST_UPDATE_KEYS:
            dates[key] = {}
            for s in all_sources[key]:
                dates[key][s] = None
        return dates

    oldest_date_per_source = {key: {} for key in LAST_UPDATE_KEYS}

    if options.since_last_update:
        last_updates = {}
        try:
            if os.path.isfile(options.last_update_file):
                with open(options.last_update_file, "r") as f:
                    last_updates_text = f.read()
                if last_updates_text:
                    last_updates = json.loads(last_updates_text)
        except JSONDecodeError:
            raise InvalidConfig(f"{options.last_update_file} should contain valid json")

        for key in LAST_UPDATE_KEYS:
            oldest_date_per_source[key] = {
                s: datetime.strptime(last_updates[key].get(s), DATE_FORMAT)
                for s in all_sources[key]
                if last_updates.get(key, {}).get(s)
            }

    since = None
    if options.since:
        try:
            since = datetime.strptime(options.since, DATE_FORMAT)
        except ValueError:
            raise InvalidConfig("'since' option should have format 'DD.MM.YYYY'")

    for key in LAST_UPDATE_KEYS:
        for s in all_sources[key]:
            if not oldest_date_per_source[key].get(s):
                oldest_date_per_source[key][s] = since

    log("Dates of last update per source:", Bcolors.OKBLUE)
    log(oldest_date_per_source, Bcolors.OKBLUE)

    return oldest_date_per_source


def update_last_updated_file(options):
    all_sources = get_all_sources_for_last_updated_file(options)
    today = datetime.now().strftime(DATE_FORMAT)
    last_updates = {}

    if os.path.isfile(options.last_update_file):
        with open(options.last_update_file, "r") as f:
            last_updates_text = f.read()
        if last_updates_text:
            last_updates = json.loads(last_updates_text)

    for key, value in all_sources.items():
        if not last_updates.get(key):
            last_updates[key] = {}
        for s in value:
            last_updates[key][s] = today

    data = json.dumps(last_updates)

    log(
        f"Updating file {options.last_update_file} with dates {data}",
        Bcolors.OKBLUE,
    )

    with open(options.last_update_file, "w") as f:
        f.write(data)


def get_urls(options):
    oldest_dates_per_source = get_oldest_date(options)

    urls = set([])
    url_count = 0

    try:
        if SOURCE_FILE in options.sources:
            with open(options.input, "r") as fp:
                urls = set([x.replace("\n", "") for x in fp.readlines()])

            url_count = len(urls)
            log(f"{url_count} URLs from file", Bcolors.OKGREEN)

            with open(options.input, "w") as fp:
                fp.write("")

        if SOURCE_LATER in options.sources:
            log("Getting URLs from Marked for Later", Bcolors.HEADER)
            urls |= get_ao3_marked_for_later_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates_per_source[SOURCES][SOURCE_LATER],
                ao3_url=options.mirror,
            )
            log(
                f"{len(urls) - url_count} URLs from Marked for Later",
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_BOOKMARKS in options.sources:
            log(
                "Getting URLs from Bookmarks (sorted by bookmarking date)",
                Bcolors.HEADER,
            )
            urls |= get_ao3_bookmark_urls(
                options.cookie,
                options.expand_series,
                options.max_count,
                options.user,
                oldest_dates_per_source[SOURCES][SOURCE_BOOKMARKS],
                sort_by_updated=False,
                ao3_url=options.mirror,
            )
            # If we're getting bookmarks back to oldest_date, this should
            # include works that have been updated since that date, as well as
            # works bookmarked since that date.
            if oldest_dates_per_source[SOURCES][SOURCE_BOOKMARKS]:
                log(
                    "Getting URLs from Bookmarks (sorted by updated date)",
                    Bcolors.HEADER,
                )
                urls |= get_ao3_bookmark_urls(
                    options.cookie,
                    options.expand_series,
                    options.max_count,
                    options.user,
                    oldest_dates_per_source[SOURCES][SOURCE_BOOKMARKS],
                    sort_by_updated=True,
                    ao3_url=options.mirror,
                )
            log(f"{len(urls) - url_count} URLs from bookmarks", Bcolors.OKGREEN)
            url_count = len(urls)

        if SOURCE_WORKS in options.sources:
            log("Getting URLs from User's Works", Bcolors.HEADER)
            urls |= get_ao3_users_work_urls(
                options.cookie,
                options.max_count,
                options.user,
                options.user,
                oldest_dates_per_source[SOURCES][SOURCE_WORKS],
                ao3_url=options.mirror,
            )
            log(
                f"{len(urls) - url_count} URLs from User's Works",
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_GIFTS in options.sources:
            log("Getting URLs from User's Gifts", Bcolors.HEADER)
            urls |= get_ao3_gift_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates_per_source[SOURCES][SOURCE_GIFTS],
                ao3_url=options.mirror,
            )
            log(
                f"{len(urls) - url_count} URLs from User's Gifts",
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_WORK_SUBSCRIPTIONS in options.sources:
            log("Getting URLs from Subscribed Works", Bcolors.HEADER)
            urls |= get_ao3_work_subscription_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates_per_source[SOURCES][SOURCE_WORK_SUBSCRIPTIONS],
                ao3_url=options.mirror,
            )
            log(
                f"{len(urls) - url_count} URLs from work subscriptions",
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_SERIES_SUBSCRIPTIONS in options.sources:
            log("Getting URLs from Subscribed Series", Bcolors.HEADER)
            urls |= get_ao3_series_subscription_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates_per_source[SOURCES][SOURCE_SERIES_SUBSCRIPTIONS],
                ao3_url=options.mirror,
            )
            log(
                f"{len(urls) - url_count} URLs from series subscriptions",
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_USER_SUBSCRIPTIONS in options.sources:
            log("Getting URLs from Subscribed Users", Bcolors.HEADER)
            urls |= get_ao3_user_subscription_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates_per_source[SOURCES][SOURCE_USER_SUBSCRIPTIONS],
                ao3_url=options.mirror,
            )
            log(
                f"{len(urls) - url_count} URLs from user subscriptions",
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_USERNAMES in options.sources:
            log(
                f"Getting URLs from following users' works: "
                f"{','.join(options.usernames)}"
            )
            for u in options.usernames:
                urls |= get_ao3_users_work_urls(
                    options.cookie,
                    options.max_count,
                    options.user,
                    u,
                    oldest_dates_per_source[SOURCE_USERNAMES][u],
                    ao3_url=options.mirror,
                )
            log(f"{len(urls) - url_count} URLs from usernames", Bcolors.OKGREEN)
            url_count = len(urls)

        if SOURCE_SERIES in options.sources:
            log(f"Getting URLs from following series: {','.join(options.series)}")
            for s in options.series:
                urls |= get_ao3_series_work_urls(
                    options.cookie,
                    options.max_count,
                    options.user,
                    s,
                    oldest_dates_per_source[SOURCE_SERIES][s],
                    ao3_url=options.mirror,
                )
            log(f"{len(urls) - url_count} URLs from series", Bcolors.OKGREEN)
            url_count = len(urls)

        if SOURCE_COLLECTIONS in options.sources:
            log(
                f"Getting URLs from following collections: "
                f"{','.join(options.collections)}"
            )
            for c in options.collections:
                urls |= get_ao3_collection_work_urls(
                    options.cookie,
                    options.max_count,
                    options.user,
                    c,
                    oldest_dates_per_source[SOURCE_COLLECTIONS][c],
                    ao3_url=options.mirror,
                )
            log(
                f"{len(urls) - url_count} URLs from collections",
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_STDIN in options.sources:
            stdin_urls = set()
            for line in sys.stdin:
                stdin_urls.add(line.rstrip())
            urls |= stdin_urls
            log(f"{len(urls) - url_count} URLs from STDIN", Bcolors.OKGREEN)
            url_count = len(urls)

        if SOURCE_IMAP in options.sources:
            mark_read = not options.email_leave_unread
            imap_urls = get_urls_from_imap(
                srv=options.email_server,
                user=options.email_user,
                passwd=options.email_password,
                folder=options.email_folder,
                markread=mark_read,
                normalize_urls=True,
            )
            urls |= imap_urls
            log(f"{len(urls) - url_count} URLs from IMAP", Bcolors.OKGREEN)
    except Exception as e:
        with open(options.input, "w") as fp:
            for cur in urls:
                fp.write(f"{cur}\n")
        raise UrlsCollectionException(e)

    # Convert urls to use default AO3 url, even if we're using a mirror.
    # This makes checking that they're correctly formed, and passing them to FanFicFare,
    # easier.
    urls = set(url.replace(options.mirror, AO3_DEFAULT_URL) for url in urls)

    return urls
