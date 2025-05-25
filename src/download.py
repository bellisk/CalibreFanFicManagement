# encoding: utf-8
# Adapted from https://github.com/MrTyton/AutomatedFanfic

import os.path
import re
from os import rename
from shutil import rmtree
from subprocess import CalledProcessError
from tempfile import mkdtemp

from .calibre import (
    CalibreException,
    CalibreHelper,
)
from .exceptions import (
    BadDataException,
    InvalidConfig,
    StoryUpToDateException,
    TempFileUpdatedMoreRecentlyException,
    UrlsCollectionException,
)
from .fanficfare_helper import FanFicFareHelper
from .get_urls import get_urls, update_last_updated_file
from .utils import (
    Bcolors,
    get_all_metadata_options,
    log,
    setup_login,
)

story_name = re.compile("(.*)-.*")
story_url = re.compile(r"(https://archiveofourown.org/works/\d*).*")


def get_url_without_chapter(url):
    url = url.replace("http://", "https://")
    m = story_url.match(url)
    if m:
        return m.group(1)
    raise BadDataException(f"Malformed url: '{url}'")


def do_download(loc, url, fff_helper, calibre, force):
    if not calibre:
        # We have no Calibre library, so just download the story.
        filepath, metadata = fff_helper.download(url, loc, update_epub=False)
        name = os.path.basename(filepath)
        rename(filepath, name)
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
        cur = calibre.export(book_id=story_id, location=loc)

        log(
            f'\tDownloading with fanficfare, updating file "{cur}"',
            Bcolors.OKGREEN,
        )

    try:
        # Throws an exception if we couldn't/shouldn't update the epub
        filepath, metadata = fff_helper.download(cur, loc, return_metadata=True)
    except Exception as e:
        if isinstance(e, TempFileUpdatedMoreRecentlyException) or (
            force and isinstance(e, StoryUpToDateException)
        ):
            log("\tForcing download update. FanFicFare error message:", Bcolors.WARNING)
            log(f"\t\t{str(e.message)}", Bcolors.WARNING)

            filepath, metadata = fff_helper.download(
                url, loc, return_metadata=True, force=True
            )
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


def downloader(url, inout_file, fff_helper, calibre, force):
    log(f"Working with url {url}", Bcolors.HEADER)

    try:
        url = get_url_without_chapter(url)
    except BadDataException as e:
        log(f"\tException: {e}", Bcolors.FAIL)
        return

    loc = mkdtemp()

    try:
        do_download(loc, url, fff_helper, calibre, force)
    except Exception as e:
        log(f"\tException: {e}", Bcolors.FAIL)
        if isinstance(e, CalledProcessError):
            log(f"\t{e.output}", Bcolors.FAIL)
        if not isinstance(e, StoryUpToDateException):
            with open(inout_file, "a") as fp:
                fp.write(f"{url}\n")
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

    fff_helper = FanFicFareHelper(config_path=options.fanficfare_config)

    for url in urls:
        downloader(
            url,
            options.input,
            fff_helper,
            calibre,
            options.force,
        )

    update_last_updated_file(options)
