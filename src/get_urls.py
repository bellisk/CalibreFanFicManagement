import json
import os.path
import sys
from datetime import datetime
from json import JSONDecodeError

from fanficfare.geturls import get_urls_from_imap

from ao3 import AO3
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
    normalise_urls,
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
from src.utils import DATE_FORMAT, Bcolors, log

LAST_UPDATE_KEYS = [SOURCES, SOURCE_USERNAMES, SOURCE_COLLECTIONS, SOURCE_SERIES]


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
        since = datetime.strptime(options.since, DATE_FORMAT)

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

    for source in options.sources:
        try:
            source_urls = get_urls_for_source(source, options, oldest_dates_per_source)
            log(f"{len(source_urls)} from source '{source}'")
            urls |= source_urls
        except Exception as e:
            with open(options.input, "w") as fp:
                for cur in urls:
                    fp.write(f"{cur}\n")
            raise UrlsCollectionException(source, e)

    return normalise_urls(urls, options.mirror)


def get_urls_for_source(source, options, oldest_dates_per_source):
    # Sources for which we don't need the AO3 client
    if source == SOURCE_FILE:
        with open(options.input, "r") as fp:
            urls = set([x.replace("\n", "") for x in fp.readlines()])

        with open(options.input, "w") as fp:
            fp.write("")

        return urls

    if source == SOURCE_STDIN:
        urls = set()
        for line in sys.stdin:
            urls.add(line.rstrip())
        return urls

    if source == SOURCE_IMAP:
        mark_read = not options.email_leave_unread
        return get_urls_from_imap(
            srv=options.email_server,
            user=options.email_user,
            passwd=options.email_password,
            folder=options.email_folder,
            markread=mark_read,
            normalize_urls=True,
        )

    # Sources for which we need the AO3 client
    if options.max_count == 0:
        return set()

    api = AO3(
        ao3_url=options.mirror,
        use_flaresolverr=options.use_flaresolverr,
        flaresolverr_url=options.flaresolverr_url,
    )
    api.login(options.user, options.cookie)
    urls = set()

    if source == SOURCE_LATER:
        urls = get_ao3_marked_for_later_urls(
            api,
            options.max_count,
            oldest_dates_per_source[SOURCES][SOURCE_LATER],
        )

    if source == SOURCE_BOOKMARKS:
        urls = get_ao3_bookmark_urls(
            api,
            options.expand_series,
            options.max_count,
            oldest_dates_per_source[SOURCES][SOURCE_BOOKMARKS],
            sort_by_updated=False,
        )
        # If we're getting bookmarks back to oldest_date, this should
        # include works that have been updated since that date, as well as
        # works bookmarked since that date.
        if oldest_dates_per_source[SOURCES][SOURCE_BOOKMARKS]:
            urls |= get_ao3_bookmark_urls(
                api,
                options.expand_series,
                options.max_count,
                oldest_dates_per_source[SOURCES][SOURCE_BOOKMARKS],
                sort_by_updated=True,
            )

    if source == SOURCE_WORKS:
        urls = get_ao3_users_work_urls(
            api,
            options.user,
            options.max_count,
            oldest_dates_per_source[SOURCES][SOURCE_WORKS],
        )

    if source == SOURCE_GIFTS:
        urls = get_ao3_gift_urls(
            api,
            options.max_count,
            oldest_dates_per_source[SOURCES][SOURCE_GIFTS],
        )

    if source == SOURCE_WORK_SUBSCRIPTIONS:
        urls = get_ao3_work_subscription_urls(
            api,
            options.max_count,
            oldest_dates_per_source[SOURCES][SOURCE_WORK_SUBSCRIPTIONS],
        )

    if source == SOURCE_SERIES_SUBSCRIPTIONS:
        urls = get_ao3_series_subscription_urls(
            api,
            options.max_count,
            oldest_dates_per_source[SOURCES][SOURCE_SERIES_SUBSCRIPTIONS],
        )

    if source == SOURCE_USER_SUBSCRIPTIONS:
        urls = get_ao3_user_subscription_urls(
            api,
            options.max_count,
            oldest_dates_per_source[SOURCES][SOURCE_USER_SUBSCRIPTIONS],
        )

    if source == SOURCE_USERNAMES:
        log(f"Getting URLs from following users' works: {','.join(options.usernames)}")
        urls = set()
        for username in options.usernames:
            urls |= get_ao3_users_work_urls(
                api,
                username,
                options.max_count,
                oldest_dates_per_source[SOURCE_USERNAMES][username],
            )

    if source == SOURCE_SERIES:
        log(f"Getting URLs from following series: {','.join(options.series)}")
        urls = set()
        for series_id in options.series:
            urls |= get_ao3_series_work_urls(
                api,
                options.max_count,
                series_id,
                oldest_dates_per_source[SOURCE_SERIES][series_id],
            )

    if source == SOURCE_COLLECTIONS:
        log(f"Getting URLs from following collections: {','.join(options.collections)}")
        urls = set()
        for coll_name in options.collections:
            urls |= get_ao3_collection_work_urls(
                api,
                options.max_count,
                coll_name,
                oldest_dates_per_source[SOURCE_COLLECTIONS][coll_name],
            )

    # Clear cookie and end sessions for AO3 client
    api.logout()

    return urls
