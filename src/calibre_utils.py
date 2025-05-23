# encoding: utf-8
import json
import locale
import os.path
import re
from errno import ENOENT
from os import devnull
from subprocess import CalledProcessError, call
from urllib.parse import urlparse

from .ao3_utils import AO3_SERIES_KEYS
from .utils import Bcolors, check_subprocess_output, log

TAG_TYPES = [
    "ao3categories",
    "characters",
    "fandoms",
    "freeformtags",
    "rating",
    "ships",
    "status",
    "warnings",
]
ADD_GROUPED_SEARCH_SCRIPT = """from calibre.library import db

db = db("%s").new_api
db.set_pref("grouped_search_terms", {"allseries": ["series", "#series00", "#series01", "#series02", "#series03"]})
print(db.pref("grouped_search_terms"))
"""
series_pattern = re.compile(r"(.*) \[(.*)]")


class CalibreException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def check_or_create_words_column(path):
    res = check_subprocess_output(f"calibredb custom_columns {path}")
    columns = res.split("\n")
    for c in columns:
        if c.startswith("words ("):
            return

    log("Adding custom column 'words' to Calibre library")
    check_subprocess_output(f"calibredb add_custom_column {path} words Words int")


def check_or_create_extra_columns(path):
    res = check_subprocess_output(f"calibredb custom_columns {path}")
    # Get rid of the number after each column name, e.g. "columnname (1)"
    columns = [c.split(" ")[0] for c in res.split("\n")]
    if set(columns).intersection(AO3_SERIES_KEYS) == set(AO3_SERIES_KEYS):
        log("Custom AO3 series columns are in Calibre Library")
    else:
        log("Adding custom AO3 series columns to Calibre library")
        for c in AO3_SERIES_KEYS:
            check_subprocess_output(
                f"calibredb add_custom_column {path} {c} {c} series"
            )

        log("Adding grouped search term 'allseries' to Calibre Library")
        _add_grouped_search_terms(path)

    if set(columns).intersection(TAG_TYPES) == set(TAG_TYPES):
        log("Custom AO3 tag-type columns are in Calibre Library")
    else:
        log("Adding AO3 tag types as columns in Calibre library")
        for tag in TAG_TYPES:
            check_subprocess_output(
                f"calibredb add_custom_column {path} {tag} {tag} text --is-multiple"
            )


def _add_grouped_search_terms(path):
    # The path that we usually use is constructed out of several parts,
    # including '--with-path' option and potentially username and password.
    # Here we just want the path to the library.
    just_library_path = path.split('"')[1]
    # Add a new grouped search term "allseries" so that Calibre can search across all
    # the series columns.
    script = ADD_GROUPED_SEARCH_SCRIPT % just_library_path
    res = check_subprocess_output(
        f"calibre-debug -c '{script}'",
    )
    log(res)


def clean_output(process_output):
    return process_output.replace("Initialized urlfixer\n", "")


class CalibreHelper(object):
    """Calls calibredb CLI commands."""

    def __init__(self, library_path, user=None, password=None):
        self.path = library_path
        self.user = user
        self.password = password

        self.library_access_string = f'--with-library="{self.path}" '
        if user:
            self.library_access_string += f'--user="{self.user}" '
        if password:
            self.library_access_string += f'--password="{self.password}" '

    def check_library(self):
        # First, check if we have calibredb locally
        try:
            with open(devnull, "w") as nullout:
                call(["calibredb"], stdout=nullout, stderr=nullout)
        except OSError as e:
            if e.errno == ENOENT:
                raise CalibreException(
                    "Calibredb is not installed on this system. Cannot search the "
                    "Calibre library or update it.",
                )

        parsed_path = urlparse(self.path)
        path_is_url = parsed_path.scheme and parsed_path.netloc
        path_is_dir = os.path.isdir(self.path)

        if not (path_is_url or path_is_dir):
            log(
                f"There is no Calibre library at the path '{self.path}', "
                f"so Calibre will create one",
                Bcolors.WARNING,
            )

        try:
            # Check that our custom columns are set up, and set them up if not.
            check_or_create_words_column(self.library_access_string)
            check_or_create_extra_columns(self.library_access_string)
        except CalledProcessError as e:
            output = clean_output(e.output)

            if "urllib.error.URLError" in output:
                # The path is a url and it's wrong
                message = f"Error connecting to the url {self.path}"
            elif "Not Found" in output:
                # The path is the url to a Calibre server, but the library name is wrong
                message = f"No Calibre library found at the url {self.path}"
            else:
                # If the username or password is wrong, calibredb gives us a nice error
                # message, so we can just output that.
                # If there's a new kind of error not already handled, we get a stack
                # trace. Just output it and deal with it then.
                message = output

            raise CalibreException(
                f"Error while making sure custom columns exist in Calibre library: "
                f"{message}",
            )

    def search(self, author=None, urls=None, series=None, book_format=None):
        if urls is None:
            urls = []
        command = "calibredb search "

        if author:
            command += f'author:"={author} or \\({author}\\)" '
        if urls:
            command += " or ".join([f"Identifiers:url:={url}" for url in urls]) + " "
        if series:
            command += f'allseries:"=\\"{series}\\"" '
        if book_format:
            command += f"Format:={book_format.upper()} "

        command += self.library_access_string
        log(command)


def export():
    pass


def add():
    pass


def set_custom():
    pass


def set_metadata():
    pass


def get_series_options(metadata):
    if len(metadata["series"]) > 0:
        m = series_pattern.match(metadata["series"])
        return f'--series="{m.group(1)}" --series-index={m.group(2)} '
    return ""


def get_extra_series_options(metadata):
    # The command to set custom column data is:
    # 'calibredb set_custom [options] column id value'
    # Here we return a list of (column, value) tuples for each additional series
    # field that contains data, plus its index.
    existing_series = metadata["series"]
    series_keys = ["series00", "series01", "series02", "series03"]
    opts = ""
    for key in series_keys:
        if len(metadata[key]) > 0 and metadata[key] != existing_series:
            m = series_pattern.match(metadata[key])
            opts += f'--field=#{key}:"{m.group(0)}" '

    return opts


def get_tags_options(metadata):
    # FFF will save all fic tags to the tags column, but we want to separate them out,
    # so remove them from there.
    opts = "--field=tags:'' "
    for tag_type in TAG_TYPES:
        if len(metadata[tag_type]) > 0:
            tags = metadata[tag_type].split(", ")
            # Replace characters that give Calibre trouble in tags.
            tags = [
                '"'
                + tag.replace('"', "'")
                .replace("...", "…")
                .replace(".", "．")
                .replace("&amp;", "&")
                + '"'
                for tag in tags
            ]
            opts += f"--field=#{tag_type}:{','.join(tags)} "

    return opts


def get_word_count(metadata):
    if metadata.get("numWords", 0) == "":
        # A strange bug that seems to happen occasionally on AO3's side.
        # The wordcount of the affected work is not actually 0.
        # Returning an empty string here will set the wordcount in Calibre to None,
        # so it can be distinguised from works that actually have 0 words (e.g. art).
        return ""

    return locale.atoi(metadata.get("numWords", 0))


def get_author_works_count(author, path):
    # author:"=author or \(author\)"
    # This catches both exact use of the author name, or use of a pseud,
    # e.g. "MyPseud (MyUsername)"
    log(f"getting work count for {author} in calibre")
    try:
        result = check_subprocess_output(
            f'calibredb search author:"={author} or \\({author}\\)" {path}',
        )
    except CalledProcessError:
        return 0
    return len(str(result).split(","))


def get_author_work_urls(author, path):
    result = check_subprocess_output(
        f'calibredb list --search author:"={author} or \\({author}\\)" {path} '
        f"--fields *identifier --for-machine",
    )
    result_json = json.loads(result.decode("utf-8"))
    return [r["*identifier"].replace("url:", "") for r in result_json]


def get_series_works_count(series_title, path):
    # Calibre seems to escape only this character in series titles
    series_title = series_title.replace("&", "&amp;")
    try:
        result = check_subprocess_output(
            f'calibredb search allseries:"=\\"{series_title}\\"" {path}',
        )
    except CalledProcessError:
        return 0
    return len(str(result).split(","))


def get_series_work_urls(series_title, path):
    # Calibre seems to escape only this character in series titles
    series_title = series_title.replace("&", "&amp;")
    result = check_subprocess_output(
        f'calibredb list --search allseries:"=\\"{series_title}\\"" {path} '
        f"--fields *identifier --for-machine",
    )
    result_json = json.loads(result.decode("utf-8"))
    return [r["*identifier"].replace("url:", "") for r in result_json]


def get_incomplete_work_data(path):
    result = check_subprocess_output(
        f'calibredb list --search "#status:=In-Progress" {path} '
        f"--fields title,*identifier --for-machine",
    )
    result_json = json.loads(result.decode("utf-8"))
    return [
        {"title": r["title"], "url": r["*identifier"].replace("url:", "")}
        for r in result_json
    ]
