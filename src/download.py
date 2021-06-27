# encoding: utf-8
# Adapted from https://github.com/MrTyton/AutomatedFanfic

import json
import re
from datetime import datetime
from errno import ENOENT
from multiprocessing import Lock, Pool
from os import devnull, remove, rename
from shutil import rmtree
from subprocess import PIPE, STDOUT, CalledProcessError, call, check_output
from tempfile import mkdtemp

from .ao3_utils import get_ao3_bookmark_urls, get_ao3_marked_for_later_urls
from .calibre_utils import get_series_options, get_tags_options
from .exceptions import BadDataException, MoreChaptersLocallyException, StoryUpToDateException, TooManyRequestsException
from .utils import get_files, log, touch

story_name = re.compile("(.*)-.*")
story_url = re.compile("(https://archiveofourown.org/works/\d*).*")

# Responses from fanficfare that mean we won't update the story
equal_chapters = re.compile(".* already contains \d* chapters.")
bad_chapters = re.compile(
    ".* doesn't contain any recognizable chapters, probably from a different source.  Not updating."
)
no_url = re.compile("No story URL found in epub to update.")
too_many_requests = re.compile(
    "Failed to read epub for update: \(HTTP Error 429: Too Many Requests\)"
)
chapter_difference = re.compile(".* contains \d* chapters, more than source: \d*.")

# Responses from fanficfare that mean we should force-update the story
# Our tmp epub was just created, so if this is the only reason not to update,
# we should ignore it and do the update
more_chapters = re.compile(
    ".*File\(.*\.epub\) Updated\(.*\) more recently than Story\(.*\) - Skipping"
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
    if too_many_requests.search(output):
        raise TooManyRequestsException()
    if chapter_difference.search(output):
        raise MoreChaptersLocallyException()


def should_force_download(force, output):
    output = output.decode("utf-8")
    return force and more_chapters.search(output)


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
    m = story_url.match(url)
    return m.group(1)


def downloader(args):
    url, inout_file, fanficfare_config, path, force, live = args
    loc = mkdtemp()
    output = ""
    output += log("Working with url {}".format(url), "HEADER", live)
    story_id = None
    try:
        if path:
            try:
                lock.acquire()
                story_id = check_output(
                    'calibredb search "Identifiers:url:{}" {}'.format(url, path),
                    shell=True,
                    stderr=STDOUT,
                    stdin=PIPE,
                )
                lock.release()
            except CalledProcessError:
                # story is not in calibre
                lock.release()
                cur = url

            if story_id is not None:
                story_id = story_id.decode("utf-8")
                output += log(
                    "\tStory is in calibre with id {}".format(story_id), "BLUE", live
                )
                output += log("\tExporting file", "BLUE", live)
                output += log(
                    'calibredb export {} --dont-save-cover --dont-write-opf --single-dir --to-dir "{}" {}'.format(
                        story_id, loc, path
                    ),
                    "BLUE",
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
                        "GREEN",
                        live,
                    )
                except IndexError:
                    # calibre doesn't have this story in epub format.
                    # the ebook-convert and ebook-meta CLIs can't save an epub
                    # with a source url in the way fanficfare expects, so
                    # we'll download a new copy as if we didn't have it at all
                    cur = url
                    output += log(
                        '\tNo epub for story id "{}" in calibre'.format(story_id),
                        "BLUE",
                        live,
                    )

            res = check_output(
                "cp {} {}/personal.ini".format(fanficfare_config, loc),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )

            output += log(
                '\tRunning: cd "{}" && fanficfare -j -u "{}" --update-cover'.format(
                    loc, cur
                ),
                "BLUE",
                live,
            )
            res = check_output(
                'cd "{}" && fanficfare -j -u "{}" --update-cover'.format(loc, cur),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )
            check_fff_output(res)
            metadata = get_metadata(res)
            series_options = get_series_options(metadata)
            tags_options = get_tags_options(metadata)

            if should_force_download(force, res):
                output += log("\tForcing download update. FanFicFare error message:", "WARNING", live)
                for line in res.split(b"\n"):
                    if line == b"{":
                        break
                    output += log("\t\t{}".format(str(line)), "WARNING", live)
                res = check_output(
                    'cd "{}" && fanficfare -u "{}" --force --update-cover'.format(loc, cur),
                    shell=True,
                    stderr=STDOUT,
                    stdin=PIPE,
                )
                check_fff_output(res)
            cur = get_files(loc, ".epub", True)[0]

            output += log("\tAdding {} to library".format(cur), "BLUE", live)
            try:
                lock.acquire()
                res = check_output(
                    'calibredb add -d {} "{}" {} {}'.format(
                        path, cur, series_options, tags_options
                    ),
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
                    'calibredb search "Identifiers:url:{}" {}'.format(
                        get_url_without_chapter(url), path
                    ),
                    shell=True,
                    stderr=STDOUT,
                    stdin=PIPE,
                )
                lock.release()
                output += log(
                    "\tAdded {} to library with id {}".format(cur, res), "GREEN", live
                )
            except CalledProcessError as e:
                lock.release()
                output += log(
                    "It's been added to library, but not sure what the ID is.",
                    "WARNING",
                    live,
                )
                output += log("Added /Story-file to library with id 0", "GREEN", live)
                output += log(e.output)

            if story_id:
                output += log(
                    "\tRemoving {} from library".format(story_id), "BLUE", live
                )
                try:
                    lock.acquire()
                    res = check_output(
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
            # We have no path to a calibre library, so just download the story.
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
                "Downloaded story {} to {}".format(
                    story_name.search(name).group(1), name
                ),
                "GREEN",
                live,
            )

        if not live:
            print(output.strip())
        rmtree(loc)
    except Exception as e:
        output += log("Exception: {}".format(e), "FAIL", live)
        if type(e) == CalledProcessError:
            output += log(e.output.decode("utf-8"), "FAIL", live)
        if not live:
            print(output.strip())
        try:
            rmtree(loc)
        except BaseException:
            pass
        if type(e) != StoryUpToDateException:
            with open(inout_file, "a") as fp:
                fp.write("{}\n".format(url))


def init(l):
    global lock
    lock = l


def download(options):
    if not (options.user and options.cookie):
        raise ValueError("User and Cookie are required for downloading from AO3")

    path = options.library
    if path:
        path = '--with-library "{}"'.format(path)
        try:
            with open(devnull, "w") as nullout:
                call(["calibredb"], stdout=nullout, stderr=nullout)
        except OSError as e:
            if e.errno == ENOENT:
                log(
                    "Calibredb is not installed on this system. Cannot search the calibre library or update it.",
                    "FAIL",
                )
                return

    source = options.source
    for s in source:
        if s not in ["bookmarks", "later"]:
            log("Valid 'source' options are 'bookmarks' or 'later', not {}"
                .format(s))
            return

    oldest_date = None
    if options.since:
        try:
            oldest_date = datetime.strptime(options.since, '%d.%m.%Y')
        except ValueError:
            log("'since' option should have format 'DD.MM.YYYY'")
            return

    inout_file = options.input
    touch(inout_file)

    with open(inout_file, "r") as fp:
        urls = set([x.replace("\n", "") for x in fp.readlines()])

    url_count = len(urls)
    log("{} URLs from file".format(url_count), "GREEN")

    with open(inout_file, "w") as fp:
        fp.write("")

    try:
        if "later" in source:
            log("Getting URLs from Marked for Later", "HEADER")
            urls |= get_ao3_marked_for_later_urls(
                options.cookie, options.max_count, options.user, oldest_date
            )
            url_count = len(urls) - url_count
            log("{} URLs from Marked for Later".format(url_count), "GREEN")

        if "bookmarks" in source:
            log("Getting URLs from Bookmarks", "HEADER")
            urls |= get_ao3_bookmark_urls(
                options.cookie, options.expand_series, options.max_count, options.user, oldest_date
            )
            url_count = len(urls) - url_count
            log("{} URLs from bookmarks".format(url_count), "GREEN")
    except BaseException:
        with open(inout_file, "w") as fp:
            for cur in urls:
                fp.write("{}\n".format(cur))
        return

    if not urls:
        return
    log("URLs to parse ({}):".format(len(urls)), "HEADER")
    for url in urls:
        log("\t{}".format(url), "BLUE")

    if options.dry_run:
        log(
            "Not adding any stories to calibre because dry-run is set to True", "HEADER"
        )

        return
    else:
        l = Lock()
        p = Pool(1, initializer=init, initargs=(l,))
        p.map(
            downloader,
            [[url, inout_file, options.fanficfare_config, path, options.force, options.live] for url in urls],
        )
