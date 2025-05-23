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


def clean_output(process_output):
    return process_output.replace("Initialized urlfixer\n", "")


def check_and_clean_output(command):
    """Runs a command as a subprocess, raising CalledProcessError if necessary,
    and removes the cruft calibredb adds to the output.
    """
    return clean_output(check_subprocess_output(command))


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
            self.check_or_create_words_column()
            self.check_or_create_extra_columns()
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

    def check_or_create_words_column(self):
        res = check_and_clean_output(
            f"calibredb custom_columns {self.library_access_string}"
        )
        columns = res.split("\n")
        for c in columns:
            if c.startswith("words ("):
                return

        log("Adding custom column 'words' to Calibre library")
        check_and_clean_output(
            f"calibredb add_custom_column {self.library_access_string} words Words int"
        )

    def check_or_create_extra_columns(self):
        res = check_and_clean_output(
            f"calibredb custom_columns {self.library_access_string}"
        )
        # Get rid of the number after each column name, e.g. "columnname (1)"
        columns = [c.split(" ")[0] for c in res.split("\n")]
        if set(columns).intersection(AO3_SERIES_KEYS) == set(AO3_SERIES_KEYS):
            log("Custom AO3 series columns are in Calibre Library")
        else:
            log("Adding custom AO3 series columns to Calibre library")
            for c in AO3_SERIES_KEYS:
                check_and_clean_output(
                    f"calibredb add_custom_column {self.library_access_string} "
                    f"{c} {c} series"
                )

            log("Adding grouped search term 'allseries' to Calibre Library")
            script = ADD_GROUPED_SEARCH_SCRIPT % self.path
            check_and_clean_output(
                f"calibre-debug -c '{script}'",
            )

        if set(columns).intersection(TAG_TYPES) == set(TAG_TYPES):
            log("Custom AO3 tag-type columns are in Calibre Library")
        else:
            log("Adding AO3 tag types as columns in Calibre library")
            for tag in TAG_TYPES:
                check_and_clean_output(
                    f"calibredb add_custom_column {self.library_access_string} "
                    f"{tag} {tag} text --is-multiple"
                )

    def search(self, authors=None, urls=None, series=None, book_formats=None):
        """Accepts lists of authors/urls/series/formats to search calibredb for.

        Returns a list of book ids that match the search.
        """
        search_terms = []

        if authors:
            # author:"=author or \(author\)"
            # This catches both exact use of the author name, or use of a pseud,
            # e.g. "MyPseud (MyUsername)"
            search_terms.extend(
                [f'author:"={author} or \\({author}\\)"' for author in authors]
            )
        if urls:
            search_terms.extend([f"Identifiers:url:={url}" for url in urls])
        if series:
            search_terms.extend([f'allseries:"=\\"{s}\\""' for s in series])
        if book_formats:
            search_terms.extend(
                [f"Format:={book_format.upper()}" for book_format in book_formats]
            )

        command = (
            f"calibredb search {' or '. join(search_terms)} "
            f"{self.library_access_string}"
        )
        log(command)

        try:
            result = check_and_clean_output(command)

            return result.split(",")
        except CalledProcessError as e:
            if "No books matching the search expression" in e.output:
                return []
            else:
                raise

    def get_author_works_count(self, author):
        log(f"Getting work count for {author} in calibre")
        result = self.search(authors=[author])

        return len(result)

    def get_series_works_count(self, series_title):
        log(f"Getting work count for {series_title} in calibre")
        # Calibre seems to escape only this character in series titles
        series_title = series_title.replace("&", "&amp;")
        result = self.search(series=[series_title])

        return len(result)

    def export(self, book_id, location):
        command = (
            f'calibredb export {book_id} --to-dir "{location}"'
            f"--dont-save-cover --dont-write-opf --single-dir "
            f"{self.library_access_string}"
        )

        try:
            check_and_clean_output(command)
        except CalledProcessError as e:
            raise CalibreException(e.output)

    def list_urls(self):
        pass

    def add(self, book_filepath, options):
        """Add a book to the Calibre library.

        options is a dictionary of option_name: option_value, which will be converted to
        CLI options.
        """
        options_strings = [f"--{k}={v}" for k, v in options.items()]

        command = (
            f'calibredb add -d "{book_filepath}" {" ".join(options_strings)} '
            f"{self.library_access_string}"
        )

        try:
            check_and_clean_output(command)
        except CalledProcessError as e:
            raise CalibreException(e.output)

    def remove(self):
        pass

    def set_metadata(self, book_id, options):
        """Set metadata fields on an existing book in the Calibre library.

        options is a dictionary of field: value, which will be converted to CLI options.
        NB: custom fields must be prefaced with a '#' character for Calibre to
        recognise them.
        NB: values with spaces in them must include quotation marks in the string.

        Example: {
            "series": '"My Series"',
            "#series00": '"My Other Series"',
            "tags": "tag1,tag2",
            "#characters": '"Jane Grey","Captain Scarlet"'
        }
        """
        options_strings = [f"--field={k}:{v}" for k, v in options.items()]

        command = (
            f"calibredb set_metadata {book_id} {' '.join(options_strings)}"
            f"{self.library_access_string}"
        )

        try:
            check_and_clean_output(command)
        except CalledProcessError as e:
            raise CalibreException(e.output)


def get_series_options(metadata):
    if len(metadata["series"]) == 0:
        return {}

    m = series_pattern.match(metadata["series"])
    return {"series": m.group(1), "series-index": f'"{m.group(2)}"'}


def get_extra_series_options(metadata):
    existing_series = metadata["series"]
    series_keys = ["series00", "series01", "series02", "series03"]
    opts = {}
    for key in series_keys:
        if len(metadata[key]) > 0 and metadata[key] != existing_series:
            m = series_pattern.match(metadata[key])
            opts[f"#{key}"] = f'"{m.group(0)}"'

    return opts


def get_tags_options(metadata):
    # FFF will save all fic tags to the tags column, but we want to separate them out,
    # so remove them from there.
    opts = {"tags": ""}
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
            opts[f"#{tag_type}"] = f"{','.join(tags)}"

    return opts


def get_word_count(metadata):
    if metadata.get("numWords", 0) == "":
        # A strange bug that seems to happen occasionally on AO3's side.
        # The wordcount of the affected work is not actually 0.
        # Returning an empty string here will set the wordcount in Calibre to None,
        # so it can be distinguised from works that actually have 0 words (e.g. art).
        return ""

    return locale.atoi(metadata.get("numWords", 0))


def get_author_work_urls(author, path):
    result = check_and_clean_output(
        f'calibredb list --search author:"={author} or \\({author}\\)" {path} '
        f"--fields *identifier --for-machine",
    )
    result_json = json.loads(result)
    return [r["*identifier"].replace("url:", "") for r in result_json]


def get_series_work_urls(series_title, path):
    # Calibre seems to escape only this character in series titles
    series_title = series_title.replace("&", "&amp;")
    result = check_and_clean_output(
        f'calibredb list --search allseries:"=\\"{series_title}\\"" {path} '
        f"--fields *identifier --for-machine",
    )
    result_json = json.loads(result)
    return [r["*identifier"].replace("url:", "") for r in result_json]


def get_incomplete_work_data(path):
    result = check_and_clean_output(
        f'calibredb list --search "#status:=In-Progress" {path} '
        f"--fields title,*identifier --for-machine",
    )
    result_json = json.loads(result)
    return [
        {"title": r["title"], "url": r["*identifier"].replace("url:", "")}
        for r in result_json
    ]
