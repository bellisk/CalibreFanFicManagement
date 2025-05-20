# encoding: utf-8
# Adapted from https://github.com/MrTyton/AutomatedFanfic

import json
import re
import time
from os import rename
from shutil import rmtree
from subprocess import CalledProcessError
from tempfile import mkdtemp

from .calibre_utils import (
    check_library_and_get_path,
    get_extra_series_options,
    get_series_options,
    get_tags_options,
    get_word_count,
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
from .get_urls import get_oldest_date, get_urls, update_last_updated_file
from .utils import (
    Bcolors,
    check_subprocess_output,
    get_files,
    log,
    setup_login,
)

story_name = re.compile("(.*)-.*")
story_url = re.compile(r"(https://archiveofourown.org/works/\d*).*")
metadata = re.compile(r"\{.*}", flags=re.DOTALL)

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
    output = output.decode("utf-8")
    metadata_json = metadata.search(output)
    if metadata_json:
        return json.loads(metadata_json.group(0))
    raise RuntimeError(f"Got unexpected response from FanFicFare: {output}")


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

    cur = url
    try:
        result = check_subprocess_output(
            f'calibredb search "Identifiers:url:={url}" "Format:=EPUB" {path}'
        )
        story_id = result.decode("utf-8").replace("Initialized urlfixer\n", "")
    except CalledProcessError:
        # story is not in Calibre
        story_id = None

    if story_id is not None:
        # Story is in Calibre
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
        check_subprocess_output(
            f"calibredb export {story_id} --dont-save-cover --dont-write-opf "
            f'--single-dir --to-dir "{loc}" {path}',
        )

        cur = get_files(loc, ".epub", True)[0]
        output += log(
            f'\tDownloading with fanficfare, updating file "{cur}"',
            Bcolors.OKGREEN,
            live,
        )

    check_subprocess_output(f'cp "{fanficfare_config}" {loc}/personal.ini')

    command = f'cd "{loc}" && fanficfare -j -u "{cur}" --update-cover'
    output += log(
        f"\tRunning: {command}",
        Bcolors.OKBLUE,
        live,
    )
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

            output += log(
                f"\tRunning: {command}",
                Bcolors.OKBLUE,
                live,
            )
            try:
                fff_update_result = check_subprocess_output(command)
            except CalledProcessError as e:
                fff_update_result = e.output
            check_fff_output(fff_update_result, command)
        else:
            raise e

    metadata = get_metadata(fff_update_result)
    series_options = get_series_options(metadata)
    word_count = get_word_count(metadata)
    cur = get_files(loc, ".epub", True)[0]

    output += log(f"\tAdding {cur} to library", Bcolors.OKBLUE, live)
    try:
        check_subprocess_output(f'calibredb add -d {path} "{cur}" {series_options}')
    except CalledProcessError as e:
        output += log(e)
        if not live:
            print(output.strip())
        raise
    try:
        calibre_search_result = check_subprocess_output(
            f'calibredb search "Identifiers:url:={url}" {path}'
        )
        new_story_id = get_new_story_id(calibre_search_result)
        output += log(
            f"\tAdded {cur} to library with id {new_story_id}",
            Bcolors.OKGREEN,
            live,
        )
    except CalledProcessError as e:
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
            check_subprocess_output(
                f"calibredb set_custom {path} words {new_story_id} '{word_count}'"
            )
        except CalledProcessError as e:
            output += log(
                "\tError setting word count.",
                Bcolors.WARNING,
                live,
            )
            output += log(f"\t{e.output}")

        extra_series_options = get_extra_series_options(metadata)
        tags_options = get_tags_options(metadata)
        try:
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
        except CalledProcessError as e:
            output += log(
                "\tError setting custom data.",
                Bcolors.WARNING,
                live,
            )
            output += log(f"\t{e.output}")

    if story_id:
        output += log(f"\tRemoving {story_id} from library", Bcolors.OKBLUE, live)
        try:
            check_subprocess_output(f"calibredb remove {path} {story_id}")
        except CalledProcessError:
            if not live:
                print(output.strip())
            raise

    if not live:
        print(output.strip())
    rmtree(loc)


def downloader(url, inout_file, fanficfare_config, path, force, live):
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
        if isinstance(e, CloudflareWebsiteException):
            # Let the outer loop know that we need to pause before downloading the next
            # fic
            raise


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

    for url in urls:
        try:
            downloader(
                url,
                inout_file,
                options.fanficfare_config,
                path,
                options.force,
                options.live,
            )
        except CloudflareWebsiteException:
            pause = 30
            log(
                f"Waiting {pause} seconds to (hopefully) allow AO3 to recover from "
                f"Cloudflare error",
                Bcolors.WARNING,
            )
            time.sleep(pause)

    update_last_updated_file(options)
