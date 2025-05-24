import re

from src.exceptions import (
    BadDataException,
    CloudflareWebsiteException,
    EmptyFanFicFareResponseException,
    MoreChaptersLocallyException,
    StoryUpToDateException,
    TempFileUpdatedMoreRecentlyException,
    TooManyRequestsException,
)
from src.utils import check_subprocess_output, get_files

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


class FanFicFareHelper(object):
    """Calls fanficfare CLI commands."""

    def __init__(self, config_path):
        self.config_path = config_path

    def download(
        self,
        url,
        location,
        update_epub=True,
        update_cover=True,
        return_metadata=False,
        force=False,
    ):
        options = []
        if self.config_path:
            options.append(f"--config={self.config_path}")
        if update_epub:
            options.append("--update-epub")
        if update_cover:
            options.append("--update-cover")
        if return_metadata:
            options.append("--json-meta")
        if force:
            options.append("--force")

        command = f'cd "{location}" && fanficfare {" ".join(options)} "{url}"'
        result = check_subprocess_output(command)

        # Throws exceptions if needed
        check_fff_output(result)

        # Return path to newly-downloaded epub file, metadata if any
        filepath = get_files(location, ".epub", True)[0]

        return filepath, {}
