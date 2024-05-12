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
from subprocess import CalledProcessError
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
    EmptyFanFicFareResponseException,
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
from .utils import Bcolors, check_subprocess_output, get_files, log, setup_login

LAST_UPDATE_KEYS = [SOURCES, SOURCE_USERNAMES, SOURCE_COLLECTIONS, SOURCE_SERIES]

DATE_FORMAT = "%d.%m.%Y"

story_name = re.compile("(.*)-.*")
story_url = re.compile(r"(https://archiveofourown.org/works/\d*).*")

# Responses from fanficfare that mean we won't update the story
bad_chapters = re.compile(
    ".* doesn't contain any recognizable chapters, probably from a different source. "
    "{2}Not updating."
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


def check_fff_output(output, command=""):
    if isinstance(output, bytes):
        output = output.decode("utf-8")
    if len(output) == 0:
        raise EmptyFanFicFareResponseException(command)
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
    raise BadDataException(f"Malformed url: '{url}'")


def get_new_story_id(bytestring):
    # We get something like b'123,124,125' and want the last id as a string
    return (
        bytestring.decode("utf-8").replace("Initialized urlfixer\n", "").split(",")[-1]
    )


def do_download(path, loc, url, fanficfare_config, output, force, live):
    if not path:
        # We have no path to a Calibre library, so just download the story.
        command = f'cd "{loc}" && fanficfare -u "{url}" --update-cover'
        fff_update_result = check_subprocess_output(command)
        check_fff_output(fff_update_result, command)
        cur = get_files(loc, ".epub", True)[0]
        name = get_files(loc, ".epub", False)[0]
        rename(cur, name)
        output += log(
            f"\tDownloaded story {story_name.search(name).group(1)} to {name}",
            Bcolors.OKGREEN,
            live,
        )

        return

    story_id = None
    cur = url
    try:
        lock.acquire()
        story_id = check_subprocess_output(
            f'calibredb search "Identifiers:url:={url}" {path}'
        )
        lock.release()
    except CalledProcessError:
        # story is not in Calibre
        lock.release()

    if story_id is not None:
        # Story is in Calibre
        story_id = story_id.decode("utf-8").replace("Initialized urlfixer\n", "")
        output += log(
            f"\tStory is in Calibre with id {story_id}",
            Bcolors.OKBLUE,
            live,
        )
        output += log("\tExporting file", Bcolors.OKBLUE, live)
        output += log(
            f"\tcalibredb export {story_id} --dont-save-cover --dont-write-opf "
            f'--single-dir --to-dir "{loc}" {path}',
            Bcolors.OKBLUE,
            live,
        )
        lock.acquire()
        check_subprocess_output(
            f"calibredb export {story_id} --dont-save-cover --dont-write-opf "
            f'--single-dir --to-dir "{loc}" {path}',
        )
        lock.release()

        try:
            cur = get_files(loc, ".epub", True)[0]
            output += log(
                f'\tDownloading with fanficfare, updating file "{cur}"',
                Bcolors.OKGREEN,
                live,
            )
        except IndexError:
            # Calibre doesn't have this story in epub format.
            # The ebook-convert and ebook-meta CLIs can't save an epub with a source
            # url in the way fanficfare expects, so we'll download a new copy as if we
            # didn't have it at all
            output += log(
                f'\tNo epub for story id "{story_id}" in Calibre',
                Bcolors.OKBLUE,
                live,
            )

    check_subprocess_output(f'cp "{fanficfare_config}" {loc}/personal.ini')

    command = f'cd "{loc}" && fanficfare -j -u "{cur}" --update-cover'
    output += log(
        f"\tRunning: {command}",
        Bcolors.OKBLUE,
        live,
    )
    fff_update_result = ""
    try:
        fff_update_result = check_subprocess_output(command)
    except CalledProcessError as e:
        if (
            "AttributeError: 'NoneType' object has no attribute 'get_text'"
            in e.output.decode("utf-8")
        ):
            # This is an uncaught error fanficfare returns when it can't make
            # the expected BeautifulSoup out of the story page, e.g. when a
            # story has been added to a hidden AO3 collection.
            raise BadDataException(
                "No story found at this url. It might have been hidden."
            )

    try:
        # Throws an exception if we couldn't/shouldn't update the epub
        check_fff_output(fff_update_result, command)
    except Exception as e:
        if isinstance(e, TempFileUpdatedMoreRecentlyException) or (
            force and isinstance(e, StoryUpToDateException)
        ):
            output += log(
                "\tForcing download update. FanFicFare error message:",
                Bcolors.WARNING,
                live,
            )
            for line in fff_update_result.split(b"\n"):
                if line == b"{":
                    break
                output += log(f"\t\t{str(line)}", Bcolors.WARNING, live)
            command += " --force"
            fff_update_result = check_subprocess_output(command)
            check_fff_output(fff_update_result, command)
        else:
            raise e

    metadata = get_metadata(fff_update_result)
    series_options = get_series_options(metadata)
    word_count = get_word_count(metadata)
    cur = get_files(loc, ".epub", True)[0]

    output += log(f"\tAdding {cur} to library", Bcolors.OKBLUE, live)
    try:
        lock.acquire()
        check_subprocess_output(f'calibredb add -d {path} "{cur}" {series_options}')
        lock.release()
    except Exception as e:
        lock.release()
        output += log(e)
        if not live:
            print(output.strip())
        raise
    try:
        lock.acquire()
        calibre_search_result = check_subprocess_output(
            f'calibredb search "Identifiers:url:={url}" {path}'
        )
        lock.release()
        new_story_id = get_new_story_id(calibre_search_result)
        output += log(
            f"\tAdded {cur} to library with id {new_story_id}",
            Bcolors.OKGREEN,
            live,
        )
    except CalledProcessError as e:
        lock.release()
        output += log(
            "\tIt's been added to library, but not sure what the ID is.",
            Bcolors.WARNING,
            live,
        )
        output += log("\tAdded /Story-file to library with id 0", Bcolors.OKGREEN, live)
        output += log(f"\t{e.output}")
        raise

    if new_story_id:
        output += log(
            f"\tSetting word count of {word_count} on story {new_story_id}",
            Bcolors.OKBLUE,
            live,
        )
        try:
            lock.acquire()
            check_subprocess_output(
                f"calibredb set_custom {path} words {new_story_id} '{word_count}'"
            )
            lock.release()
        except CalledProcessError as e:
            lock.release()
            output += log(
                "\tError setting word count.",
                Bcolors.WARNING,
                live,
            )
            output += log(f"\t{e.output}")

        extra_series_options = get_extra_series_options(metadata)
        tags_options = get_tags_options(metadata)
        try:
            lock.acquire()
            output += log(
                f"\tSetting custom fields on story {new_story_id}",
                Bcolors.OKBLUE,
                live,
            )
            update_command = (
                f"calibredb set_metadata {str(new_story_id)} "
                f"{path} {tags_options} {extra_series_options}"
            )
            output += log(update_command, Bcolors.OKBLUE, live)
            check_subprocess_output(update_command)
            lock.release()
        except CalledProcessError as e:
            lock.release()
            output += log(
                "\tError setting custom data.",
                Bcolors.WARNING,
                live,
            )
            output += log(f"\t{e.output}")

    if story_id:
        output += log(f"\tRemoving {story_id} from library", Bcolors.OKBLUE, live)
        try:
            lock.acquire()
            check_subprocess_output(f"calibredb remove {path} {story_id}")
            lock.release()
        except BaseException:
            lock.release()
            if not live:
                print(output.strip())
            raise

    if not live:
        print(output.strip())
    rmtree(loc)


def downloader(args):
    url, inout_file, fanficfare_config, path, force, live = args
    output = ""
    output += log(f"Working with url {url}", Bcolors.HEADER, live)

    try:
        url = get_url_without_chapter(url)
    except BadDataException as e:
        output += log(f"\tException: {e}", Bcolors.FAIL, live)
        if not live:
            print(output.strip())
        return

    loc = mkdtemp()
    story_id = None

    try:
        do_download(path, loc, url, fanficfare_config, output, force, live)
    except Exception as e:
        output += log(f"\tException: {e}", Bcolors.FAIL, live)
        if isinstance(e, CalledProcessError):
            output += log(f"\t{e.output.decode('utf-8')}", Bcolors.FAIL, live)
        if not live:
            print(output.strip())
        rmtree(loc, ignore_errors=True)
        if not isinstance(e, StoryUpToDateException):
            with open(inout_file, "a") as fp:
                fp.write(f"{url}\n")


def get_urls(inout_file, options, oldest_dates):
    urls = set([])
    url_count = 0

    try:
        if SOURCE_FILE in options.sources:
            with open(inout_file, "r") as fp:
                urls = set([x.replace("\n", "") for x in fp.readlines()])

            url_count = len(urls)
            log(f"{url_count} URLs from file", Bcolors.OKGREEN)

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
            log(f"{len(urls) - url_count} URLs from bookmarks", Bcolors.OKGREEN)
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
                oldest_dates[SOURCES][SOURCE_GIFTS],
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
                oldest_dates[SOURCES][SOURCE_WORK_SUBSCRIPTIONS],
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
                oldest_dates[SOURCES][SOURCE_SERIES_SUBSCRIPTIONS],
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
                oldest_dates[SOURCES][SOURCE_USER_SUBSCRIPTIONS],
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
                    oldest_dates[SOURCE_USERNAMES][u],
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
                    oldest_dates[SOURCE_SERIES][s],
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
                    oldest_dates[SOURCE_COLLECTIONS][c],
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
    except Exception as e:
        with open(inout_file, "w") as fp:
            for cur in urls:
                fp.write(f"{cur}\n")
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
        f"Updating file {options.last_update_file} with dates {data}",
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
            raise InvalidConfig(f"{options.last_update_file} should be valid json")

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
        log(f"Error getting urls: {e}")

        return

    if not urls:
        return

    log(f"Unique URLs to fetch ({len(urls)}):", Bcolors.HEADER)
    for url in urls:
        log(f"\t{url}", Bcolors.OKBLUE)

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
