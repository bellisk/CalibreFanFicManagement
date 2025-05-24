# encoding: utf-8
# Adapted from https://github.com/MrTyton/AutomatedFanfic

import json
import re
import time
from os import rename
from shutil import rmtree
from subprocess import CalledProcessError
from tempfile import mkdtemp

from .calibre import (
    CalibreException,
    CalibreHelper,
    get_all_metadata_options,
)
from .exceptions import (
    BadDataException,
    CloudflareWebsiteException,
    EmptyFanFicFareResponseException,
    InvalidConfig,
    MoreChaptersLocallyException,
    StoryUpToDateException,
    TempFileUpdatedMoreRecentlyException,
    TooManyRequestsException,
    UrlsCollectionException,
)
from .get_urls import get_urls, update_last_updated_file
from .utils import (
    Bcolors,
    check_subprocess_output,
    get_files,
    log,
    setup_login,
)

story_name = re.compile("(.*)-.*")
story_url = re.compile(r"(https://archiveofourown.org/works/\d*).*")
metadata_dict = re.compile(r"\{.*}", flags=re.DOTALL)

# Responses from fanficfare that mean we won't update the story (at least right now)
bad_chapters = re.compile(
    ".* doesn't contain any recognizable chapters, probably from a different source. "
    "{2}Not updating."
)
no_url = re.compile("No story URL found in epub to update.")
too_many_requests = re.compile("HTTP Error 429: Too Many Requests")
cloudflare_error = re.compile("525 Server Error")
chapter_difference = re.compile(r".* contains \d* chapters, more than source: \d*.")
nonexistent_story = re.compile("Story does not exist: ")
hidden_story = re.compile(
    "This work is part of an ongoing challenge and will be revealed soon!"
)

# Response from fanficfare that mean we should force-update the story if force is True.
# We might have the same number of chapters but know that there have been
# updates we want to get
equal_chapters = re.compile(r".* already contains \d* chapters.")

# Response from fanficfare that means we should update the story, even if
# force is set to False.
# Our tmp epub was just created, so if this is the only reason not to update,
# we should ignore it and do the update
updated_more_recently = re.compile(
    r".*File\(.*\.epub\) Updated\(.*\) more recently than Story\(.*\) - Skipping"
)


def check_fff_output(output, command=""):
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
    if hidden_story.search(output):
        raise BadDataException("The story at this url has been hidden.")
    if too_many_requests.search(output):
        raise TooManyRequestsException()
    if cloudflare_error.search(output):
        raise CloudflareWebsiteException()
    if chapter_difference.search(output):
        raise MoreChaptersLocallyException()
    if updated_more_recently.search(output):
        raise TempFileUpdatedMoreRecentlyException


def get_metadata(output):
    """Get a fic metadata dictionary from the output of an FFF command.
    If the output doesn't contain a metadata dictionary, raise a RuntimeError: something
    has gone wrong that we didn't catch before, by checking the output for errors that
    we know about.
    """
    metadata_json = metadata_dict.search(output)
    if metadata_json:
        return json.loads(metadata_json.group(0))
    raise RuntimeError(f"Got unexpected response from FanFicFare: {output}")


def get_url_without_chapter(url):
    url = url.replace("http://", "https://")
    m = story_url.match(url)
    if m:
        return m.group(1)
    raise BadDataException(f"Malformed url: '{url}'")


def do_download(loc, url, fanficfare_config, calibre, force):
    if not calibre:
        # We have no Calibre library, so just download the story.
        command = f'cd "{loc}" && fanficfare -u "{url}" --update-cover'
        fff_update_result = check_subprocess_output(command)
        check_fff_output(fff_update_result, command)
        cur = get_files(loc, ".epub", True)[0]
        name = get_files(loc, ".epub", False)[0]
        rename(cur, name)
        log(
            f"\tDownloaded story {story_name.search(name).group(1)} to {name}",
            Bcolors.OKGREEN,
        )

        return

    cur = url
    story_id = None
    result = calibre.search(urls=[url], book_formats=["EPUB"])
    if len(result) > 0:
        story_id = result[0]

    if story_id is not None:
        # Story is in Calibre
        log(f"\tStory is in Calibre with id {story_id}", Bcolors.OKBLUE)
        log("\tExporting file", Bcolors.OKBLUE)
        calibre.export(book_id=story_id, location=loc)

        cur = get_files(loc, ".epub", True)[0]
        log(
            f'\tDownloading with fanficfare, updating file "{cur}"',
            Bcolors.OKGREEN,
        )

    check_subprocess_output(f'cp "{fanficfare_config}" {loc}/personal.ini')

    command = f'cd "{loc}" && fanficfare -j -u "{cur}" --update-cover'
    log(f"\tRunning: {command}", Bcolors.OKBLUE)
    try:
        fff_update_result = check_subprocess_output(command)
    except CalledProcessError as e:
        fff_update_result = e.output

    try:
        # Throws an exception if we couldn't/shouldn't update the epub
        check_fff_output(fff_update_result, command)
    except Exception as e:
        if isinstance(e, TempFileUpdatedMoreRecentlyException) or (
            force and isinstance(e, StoryUpToDateException)
        ):
            log("\tForcing download update. FanFicFare error message:", Bcolors.WARNING)
            for line in fff_update_result.split("\n"):
                if line == "{":
                    break
                log(f"\t\t{str(line)}", Bcolors.WARNING)
            command += " --force"

            log(f"\tRunning: {command}", Bcolors.OKBLUE)
            try:
                fff_update_result = check_subprocess_output(command)
            except CalledProcessError as e:
                fff_update_result = e.output
            check_fff_output(fff_update_result, command)
        else:
            raise e

    cur = get_files(loc, ".epub", True)[0]

    log(f"\tAdding {cur} to library", Bcolors.OKBLUE)
    calibre.add(book_filepath=cur)

    # The search returns a list of story ids in numerical order. The story we just
    # added has the highest id number and is at the end of the list.
    result = calibre.search(urls=[url])
    new_story_id = result[-1]
    log(f"\tAdded {cur} to library with id {new_story_id}", Bcolors.OKGREEN)

    metadata = get_metadata(fff_update_result)
    options = get_all_metadata_options(metadata)
    log(f"\tSetting custom fields on story {new_story_id}", Bcolors.OKBLUE)
    try:
        calibre.set_metadata(book_id=new_story_id, options=options)
    except CalibreException as e:
        log("\tError setting custom data.", Bcolors.WARNING)
        log(f"\t{e.message}", Bcolors.WARNING)

    if story_id:
        log(f"\tRemoving {story_id} from library", Bcolors.OKBLUE)
        calibre.remove(story_id)


def downloader(url, inout_file, fanficfare_config, calibre, force):
    log(f"Working with url {url}", Bcolors.HEADER)

    try:
        url = get_url_without_chapter(url)
    except BadDataException as e:
        log(f"\tException: {e}", Bcolors.FAIL)
        return

    loc = mkdtemp()

    try:
        do_download(loc, url, fanficfare_config, calibre, force)
    except Exception as e:
        log(f"\tException: {e}", Bcolors.FAIL)
        if isinstance(e, CalledProcessError):
            log(f"\t{e.output}", Bcolors.FAIL)
        if not isinstance(e, StoryUpToDateException):
            with open(inout_file, "a") as fp:
                fp.write(f"{url}\n")
        if isinstance(e, CloudflareWebsiteException):
            # Let the outer loop know that we need to pause before downloading the next
            # fic
            raise
    finally:
        rmtree(loc, ignore_errors=True)


def download(options):
    calibre = None
    if options.library:
        calibre = CalibreHelper(
            library_path=options.library,
            user=options.calibre_user,
            password=options.calibre_password,
        )
        try:
            calibre.check_library()
        except CalibreException as e:
            log(str(e), Bcolors.FAIL)
            return

    try:
        setup_login(options)
        urls = get_urls(options)
    except InvalidConfig as e:
        log(e.message, Bcolors.FAIL)
        return
    except UrlsCollectionException as e:
        log(f"Error getting urls: {e}")

        return

    if not urls:
        log("No new urls to fetch. Finished!", Bcolors.OKGREEN)
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

    for url in urls:
        try:
            downloader(
                url,
                options.input,
                options.fanficfare_config,
                calibre,
                options.force,
            )
        except CloudflareWebsiteException:
            pause = 30
            log(
                f"Waiting {pause} seconds to (hopefully) allow AO3 to recover from Cloudflare error",
                Bcolors.WARNING,
            )
            time.sleep(pause)

    update_last_updated_file(options)
