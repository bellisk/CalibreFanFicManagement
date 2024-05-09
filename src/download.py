# encoding: utf-8
# Adapted from https://github.com/MrTyton/AutomatedFanfic

import json
import re
import sys
from datetime import datetime
from json.decoder import JSONDecodeError
from multiprocessing import Lock, Pool
from os import rename
from shutil import rmtree
from subprocess import PIPE, STDOUT, CalledProcessError, check_output
from tempfile import mkdtemp

from .ao3_utils import (
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
from .calibre_utils import (
    check_library_and_get_path,
    get_extra_series_options,
    get_series_options,
    get_tags_options,
    get_word_count,
)
from .exceptions import (
    BadDataException,
    InvalidConfig,
    MoreChaptersLocallyException,
    StoryUpToDateException,
    TempFileUpdatedMoreRecentlyException,
    TooManyRequestsException,
    UrlsCollectionException,
)
from .options import (
    SOURCE_BOOKMARKS,
    SOURCE_COLLECTIONS,
    SOURCE_FILE,
    SOURCE_GIFTS,
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
from .utils import Bcolors, get_files, log, setup_login

LAST_UPDATE_KEYS = [SOURCES, SOURCE_USERNAMES, SOURCE_COLLECTIONS, SOURCE_SERIES]

DATE_FORMAT = "%d.%m.%Y"

story_name = re.compile("(.*)-.*")
story_url = re.compile(r"(https://archiveofourown.org/works/\d*).*")

# Responses from fanficfare that mean we won't update the story
bad_chapters = re.compile(
    ".* doesn't contain any recognizable chapters, probably from a different source. {2}Not updating."
)
no_url = re.compile("No story URL found in epub to update.")
too_many_requests = re.compile("HTTP Error 429: Too Many Requests")
chapter_difference = re.compile(r".* contains \d* chapters, more than source: \d*.")
nonexistent_story = re.compile("Story does not exist: ")

# Response from fanficfare that mean we should force-update the story
# We might have the same number of chapters but know that there have been
# updates we want to get
equal_chapters = re.compile(r".* already contains \d* chapters.")

# Response from fanficfare that means we should update the story, even if
# force is set to false
# Our tmp epub was just created, so if this is the only reason not to update,
# we should ignore it and do the update
updated_more_recently = re.compile(
    r".*File\(.*\.epub\) Updated\(.*\) more recently than Story\(.*\) - Skipping"
)


def check_fff_output(output):
    output = output.decode("utf-8")
    if equal_chapters.search(output):
        raise StoryUpToDateException()
    if bad_chapters.search(output):
        raise BadDataException(
            "Something is messed up with the site or the epub. No chapters found."
        )
    if no_url.search(output):
        raise BadDataException("No URL in epub to update from. Fix the metadata.")
    if nonexistent_story.search(output):
        raise BadDataException(
            "No story found at this url. It might have been deleted."
        )
    if too_many_requests.search(output):
        raise TooManyRequestsException()
    if chapter_difference.search(output):
        raise MoreChaptersLocallyException()
    if updated_more_recently.search(output):
        raise TempFileUpdatedMoreRecentlyException


def get_metadata(output):
    """
    When we download an epub and get the json metadata from fanficfare, we get all the
    output from the command, including lines that are useless to us. Here we get rid of
    those, so we can load the metadata as json.
    """
    output = output.split(b"\n")
    n = 0
    line = output[n]
    while line != b"{":
        n += 1
        line = output[n]

    output = b"\n".join(output[n:])
    return json.loads(output)


def get_url_without_chapter(url):
    url = url.replace("http://", "https://")
    m = story_url.match(url)
    if m:
        return m.group(1)
    raise BadDataException("Malformed url: '{}'".format(url))


def get_new_story_id(bytestring):
    # We get something like b'123,124,125' and want the last id as a string
    return bytestring.decode("utf-8").split(",")[-1]


def downloader(args):
    url, inout_file, fanficfare_config, path, force, live = args
    output = ""
    output += log("Working with url {}".format(url), Bcolors.HEADER, live)

    try:
        url = get_url_without_chapter(url)
    except BadDataException as e:
        output += log("\tException: {}".format(e), Bcolors.FAIL, live)
        if not live:
            print(output.strip())
        return

    loc = mkdtemp()
    story_id = None

    try:
        if path:
            try:
                lock.acquire()
                story_id = check_output(
                    'calibredb search "Identifiers:url:={}" {}'.format(url, path),
                    shell=True,
                    stderr=STDOUT,
                    stdin=PIPE,
                )
                lock.release()
            except CalledProcessError:
                # story is not in Calibre
                lock.release()
                cur = url

            if story_id is not None:
                story_id = story_id.decode("utf-8")
                output += log(
                    "\tStory is in Calibre with id {}".format(story_id),
                    Bcolors.OKBLUE,
                    live,
                )
                output += log("\tExporting file", Bcolors.OKBLUE, live)
                output += log(
                    '\tcalibredb export {} --dont-save-cover --dont-write-opf --single-dir --to-dir "{}" {}'.format(
                        story_id, loc, path
                    ),
                    Bcolors.OKBLUE,
                    live,
                )
                lock.acquire()
                res = check_output(
                    'calibredb export {} --dont-save-cover --dont-write-opf --single-dir --to-dir "{}" {}'.format(
                        story_id, loc, path
                    ),
                    shell=True,
                    stdin=PIPE,
                    stderr=STDOUT,
                )
                lock.release()

                try:
                    cur = get_files(loc, ".epub", True)[0]
                    output += log(
                        '\tDownloading with fanficfare, updating file "{}"'.format(cur),
                        Bcolors.OKGREEN,
                        live,
                    )
                except IndexError:
                    # Calibre doesn't have this story in epub format.
                    # the ebook-convert and ebook-meta CLIs can't save an epub
                    # with a source url in the way fanficfare expects, so
                    # we'll download a new copy as if we didn't have it at all
                    cur = url
                    output += log(
                        '\tNo epub for story id "{}" in Calibre'.format(story_id),
                        Bcolors.OKBLUE,
                        live,
                    )

            check_output(
                "cp {} {}/personal.ini".format(fanficfare_config, loc),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )

            output += log(
                '\tRunning: cd "{}" && fanficfare -j -u "{}" --update-cover'.format(
                    loc, cur
                ),
                Bcolors.OKBLUE,
                live,
            )
            try:
                res = check_output(
                    'cd "{}" && fanficfare -j -u "{}" --update-cover'.format(loc, cur),
                    shell=True,
                    stderr=STDOUT,
                    stdin=PIPE,
                )
            except CalledProcessError as e:
                if (
                    "AttributeError: 'NoneType' object has no attribute 'get_text'"
                    in e.output.decode("utf-8")
                ):
                    # This is an uncaught error fanficfare returns when it can't make the expected
                    # BeautifulSoup out of the story page, e.g. when a story has been added to a hidden
                    # AO3 collection.
                    raise BadDataException(
                        "No story found at this url. It might have been hidden."
                    )

            try:
                # Throws an exception if we couldn't/shouldn't update the epub
                check_fff_output(res)
            except Exception as e:
                if type(e) == TempFileUpdatedMoreRecentlyException or (
                    force and type(e) == StoryUpToDateException
                ):
                    output += log(
                        "\tForcing download update. FanFicFare error message:",
                        Bcolors.WARNING,
                        live,
                    )
                    for line in res.split(b"\n"):
                        if line == b"{":
                            break
                        output += log("\t\t{}".format(str(line)), Bcolors.WARNING, live)
                    res = check_output(
                        'cd "{}" && fanficfare -u -j "{}" --force --update-cover'.format(
                            loc, cur
                        ),
                        shell=True,
                        stderr=STDOUT,
                        stdin=PIPE,
                    )
                    check_fff_output(res)
                else:
                    raise e

            metadata = get_metadata(res)
            series_options = get_series_options(metadata)
            word_count = get_word_count(metadata)
            cur = get_files(loc, ".epub", True)[0]

            output += log("\tAdding {} to library".format(cur), Bcolors.OKBLUE, live)
            try:
                lock.acquire()
                check_output(
                    'calibredb add -d {} "{}" {}'.format(path, cur, series_options),
                    shell=True,
                    stderr=STDOUT,
                    stdin=PIPE,
                )
                lock.release()
            except Exception as e:
                lock.release()
                output += log(e)
                if not live:
                    print(output.strip())
                raise
            try:
                lock.acquire()
                res = check_output(
                    'calibredb search "Identifiers:url:={}" {}'.format(url, path),
                    shell=True,
                    stderr=STDOUT,
                    stdin=PIPE,
                )
                lock.release()
                output += log(
                    "\tAdded {} to library with id {}".format(cur, res),
                    Bcolors.OKGREEN,
                    live,
                )
                new_story_id = get_new_story_id(res)
            except CalledProcessError as e:
                lock.release()
                output += log(
                    "\tIt's been added to library, but not sure what the ID is.",
                    Bcolors.WARNING,
                    live,
                )
                output += log(
                    "\tAdded /Story-file to library with id 0", Bcolors.OKGREEN, live
                )
                output += log("\t{}".format(e.output))
                raise

            if new_story_id:
                output += log(
                    "\tSetting word count of {} on story {}".format(
                        word_count, new_story_id
                    ),
                    Bcolors.OKBLUE,
                    live,
                )
                try:
                    lock.acquire()
                    check_output(
                        "calibredb set_custom {} words {} '{}'".format(
                            path, new_story_id, word_count
                        ),
                        shell=True,
                        stderr=STDOUT,
                        stdin=PIPE,
                    )
                    lock.release()
                except CalledProcessError as e:
                    lock.release()
                    output += log(
                        "\tError setting word count.",
                        Bcolors.WARNING,
                        live,
                    )
                    output += log("\t{}".format(e.output))

                extra_series_options = get_extra_series_options(metadata)
                tags_options = get_tags_options(metadata)
                try:
                    lock.acquire()
                    output += log(
                        "\tSetting custom fields on story {}".format(new_story_id),
                        Bcolors.OKBLUE,
                        live,
                    )
                    update_command = f"calibredb set_metadata {str(new_story_id)} {path} {tags_options} {extra_series_options}"
                    output += log(update_command, Bcolors.OKBLUE, live)
                    check_output(
                        update_command,
                        shell=True,
                        stderr=STDOUT,
                        stdin=PIPE,
                    )
                    lock.release()
                except CalledProcessError as e:
                    lock.release()
                    output += log(
                        "\tError setting series data.",
                        Bcolors.WARNING,
                        live,
                    )
                    output += log("\t{}".format(e.output))

            if story_id:
                output += log(
                    "\tRemoving {} from library".format(story_id), Bcolors.OKBLUE, live
                )
                try:
                    lock.acquire()
                    check_output(
                        "calibredb remove {} {}".format(path, story_id),
                        shell=True,
                        stderr=STDOUT,
                        stdin=PIPE,
                    )
                    lock.release()
                except BaseException:
                    lock.release()
                    if not live:
                        print(output.strip())
                    raise
        else:
            # We have no path to a Calibre library, so just download the story.
            res = check_output(
                'cd "{}" && fanficfare -u "{}" --update-cover'.format(loc, url),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )
            check_fff_output(res)
            cur = get_files(loc, ".epub", True)[0]
            name = get_files(loc, ".epub", False)[0]
            rename(cur, name)
            output += log(
                "\tDownloaded story {} to {}".format(
                    story_name.search(name).group(1), name
                ),
                Bcolors.OKGREEN,
                live,
            )

        if not live:
            print(output.strip())
        rmtree(loc)
    except Exception as e:
        output += log("\tException: {}".format(e), Bcolors.FAIL, live)
        if type(e) == CalledProcessError:
            output += log("\t{}".format(e.output.decode("utf-8")), Bcolors.FAIL, live)
        if not live:
            print(output.strip())
        rmtree(loc, ignore_errors=True)
        if type(e) != StoryUpToDateException:
            with open(inout_file, "a") as fp:
                fp.write("{}\n".format(url))


def get_urls(inout_file, options, oldest_dates):
    urls = set([])
    url_count = 0

    try:
        if SOURCE_FILE in options.sources:
            with open(inout_file, "r") as fp:
                urls = set([x.replace("\n", "") for x in fp.readlines()])

            url_count = len(urls)
            log("{} URLs from file".format(url_count), Bcolors.OKGREEN)

            with open(inout_file, "w") as fp:
                fp.write("")

        if SOURCE_LATER in options.sources:
            log("Getting URLs from Marked for Later", Bcolors.HEADER)
            urls |= get_ao3_marked_for_later_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates[SOURCES][SOURCE_LATER],
            )
            log(
                "{} URLs from Marked for Later".format(len(urls) - url_count),
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
                oldest_dates[SOURCES][SOURCE_BOOKMARKS],
                sort_by_updated=False,
            )
            # If we're getting bookmarks back to oldest_date, this should
            # include works that have been updated since that date, as well as
            # works bookmarked since that date.
            if oldest_dates[SOURCES][SOURCE_BOOKMARKS]:
                log(
                    "Getting URLs from Bookmarks (sorted by updated date)",
                    Bcolors.HEADER,
                )
                urls |= get_ao3_bookmark_urls(
                    options.cookie,
                    options.expand_series,
                    options.max_count,
                    options.user,
                    oldest_dates[SOURCES][SOURCE_BOOKMARKS],
                    sort_by_updated=True,
                )
            log("{} URLs from bookmarks".format(len(urls) - url_count), Bcolors.OKGREEN)
            url_count = len(urls)

        if SOURCE_WORKS in options.sources:
            log("Getting URLs from User's Works", Bcolors.HEADER)
            urls |= get_ao3_users_work_urls(
                options.cookie,
                options.max_count,
                options.user,
                options.user,
                oldest_dates[SOURCES][SOURCE_WORKS],
            )
            log(
                "{} URLs from User's Works".format(len(urls) - url_count),
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_GIFTS in options.sources:
            log("Getting URLs from User's Gifts", Bcolors.HEADER)
            urls |= get_ao3_gift_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates[SOURCES][SOURCE_GIFTS],
            )
            log(
                "{} URLs from User's Gifts".format(len(urls) - url_count),
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_WORK_SUBSCRIPTIONS in options.sources:
            log("Getting URLs from Subscribed Works", Bcolors.HEADER)
            urls |= get_ao3_work_subscription_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates[SOURCES][SOURCE_WORK_SUBSCRIPTIONS],
            )
            log(
                "{} URLs from work subscriptions".format(len(urls) - url_count),
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_SERIES_SUBSCRIPTIONS in options.sources:
            log("Getting URLs from Subscribed Series", Bcolors.HEADER)
            urls |= get_ao3_series_subscription_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates[SOURCES][SOURCE_SERIES_SUBSCRIPTIONS],
            )
            log(
                "{} URLs from series subscriptions".format(len(urls) - url_count),
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_USER_SUBSCRIPTIONS in options.sources:
            log("Getting URLs from Subscribed Users", Bcolors.HEADER)
            urls |= get_ao3_user_subscription_urls(
                options.cookie,
                options.max_count,
                options.user,
                oldest_dates[SOURCES][SOURCE_USER_SUBSCRIPTIONS],
            )
            log(
                "{} URLs from user subscriptions".format(len(urls) - url_count),
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_USERNAMES in options.sources:
            log(
                "Getting URLs from following users' works: {}".format(
                    ",".join(options.usernames)
                )
            )
            for u in options.usernames:
                urls |= get_ao3_users_work_urls(
                    options.cookie,
                    options.max_count,
                    options.user,
                    u,
                    oldest_dates[SOURCE_USERNAMES][u],
                )
            log("{} URLs from usernames".format(len(urls) - url_count), Bcolors.OKGREEN)
            url_count = len(urls)

        if SOURCE_SERIES in options.sources:
            log(
                "Getting URLs from following series: {}".format(
                    ",".join(options.series)
                )
            )
            for s in options.series:
                urls |= get_ao3_series_work_urls(
                    options.cookie,
                    options.max_count,
                    options.user,
                    s,
                    oldest_dates[SOURCE_SERIES][s],
                )
            log("{} URLs from series".format(len(urls) - url_count), Bcolors.OKGREEN)
            url_count = len(urls)

        if SOURCE_COLLECTIONS in options.sources:
            log(
                "Getting URLs from following collections: {}".format(
                    ",".join(options.collections)
                )
            )
            for c in options.collections:
                urls |= get_ao3_collection_work_urls(
                    options.cookie,
                    options.max_count,
                    options.user,
                    c,
                    oldest_dates[SOURCE_COLLECTIONS][c],
                )
            log(
                "{} URLs from collections".format(len(urls) - url_count),
                Bcolors.OKGREEN,
            )
            url_count = len(urls)

        if SOURCE_STDIN in options.sources:
            stdin_urls = set()
            for line in sys.stdin:
                stdin_urls.add(line.rstrip())
            urls |= stdin_urls
            log("{} URLs from STDIN".format(len(urls) - url_count), Bcolors.OKGREEN)
    except Exception as e:
        with open(inout_file, "w") as fp:
            for cur in urls:
                fp.write("{}\n".format(cur))
        raise UrlsCollectionException(e)

    return urls


def get_all_sources_for_last_updated_file(options):
    return {
        SOURCES: options.sources,
        SOURCE_USERNAMES: options.usernames,
        SOURCE_SERIES: options.series,
        SOURCE_COLLECTIONS: options.collections,
    }


def update_last_updated_file(options):
    all_sources = get_all_sources_for_last_updated_file(options)
    today = datetime.now().strftime(DATE_FORMAT)

    with open(options.last_update_file, "r") as f:
        last_updates_text = f.read()
    last_updates = json.loads(last_updates_text) if last_updates_text else {}

    for key, value in all_sources.items():
        if not last_updates.get(key):
            last_updates[key] = {}
        for s in value:
            last_updates[key][s] = today

    data = json.dumps(last_updates)

    log(
        "Updating file {} with dates {}".format(options.last_update_file, data),
        Bcolors.OKBLUE,
    )

    with open(options.last_update_file, "w") as f:
        f.write(data)


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
            with open(options.last_update_file, "r") as f:
                last_updates_text = f.read()
            if last_updates_text:
                last_updates = json.loads(last_updates_text)
        except JSONDecodeError:
            raise InvalidConfig(
                "{} should be valid json".format(options.last_update_file)
            )

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


global lock


def init(lo):
    global lock
    lock = lo


def download(options):
    setup_login(options)
    try:
        path = check_library_and_get_path(options.library)
    except RuntimeError as e:
        log(str(e), Bcolors.FAIL)
        return

    inout_file = options.input

    try:
        oldest_dates_per_source = get_oldest_date(options)
    except InvalidConfig as e:
        log(e.message, Bcolors.FAIL)
        return

    try:
        urls = get_urls(inout_file, options, oldest_dates_per_source)
    except UrlsCollectionException as e:
        log("Error getting urls: {}".format(e))

        return

    if not urls:
        return

    log("Unique URLs to fetch ({}):".format(len(urls)), Bcolors.HEADER)
    for url in urls:
        log("\t{}".format(url), Bcolors.OKBLUE)

    if options.dry_run:
        log(
            "Not adding any stories to Calibre because dry-run is set to True",
            Bcolors.HEADER,
        )
        return
    else:
        lo = Lock()
        p = Pool(1, initializer=init, initargs=(lo,))
        p.map(
            downloader,
            [
                [
                    url,
                    inout_file,
                    options.fanficfare_config,
                    path,
                    options.force,
                    options.live,
                ]
                for url in urls
            ],
        )

    update_last_updated_file(options)
