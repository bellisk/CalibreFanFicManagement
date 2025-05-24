# encoding: utf-8
import json
import os.path
from errno import ENOENT
from os import devnull
from subprocess import CalledProcessError, call
from urllib.parse import urlparse

from .ao3_utils import AO3_SERIES_KEYS
from .utils import TAG_TYPES, Bcolors, check_subprocess_output, log

ADD_GROUPED_SEARCH_SCRIPT = """from calibre.library import db

db = db("%s").new_api
db.set_pref("grouped_search_terms", {"allseries": ["series", "#series00", "#series01", "#series02", "#series03"]})
print(db.pref("grouped_search_terms"))
"""


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


def collate_search_terms(
    authors=None, book_formats=None, series=None, urls=None, incomplete=False
):
    """Turn lists of search terms of different kinds into a search query for calibredb.

    All search terms of the same kind are joined with OR; each set of search terms
    is joined with AND. This is because this matches the current use cases I have
    for this method, and may well come back to bite me.
    """
    search_term_sets = []
    if authors:
        # author:"=author or \(author\)"
        # This catches both exact use of the author name and use of a pseud,
        # e.g. "MyPseud (MyUsername)"
        search_term_sets.append(
            " OR ".join([f'author:"={author} or \\({author}\\)"' for author in authors])
        )
    if urls:
        search_term_sets.append(f'Identifiers:url:"={" OR ".join(urls)}"')
    if series:
        # Calibre seems to escape only the character & in series titles
        search_term_sets.append(
            f'allseries:"=\\"{" OR ".join([s.replace("&", "&amp;") for s in series])}\\""'
        )
    if book_formats:
        search_term_sets.append(
            f'Format:"={" OR ".join([book_format.upper() for book_format in book_formats])}"'
        )
    if incomplete:
        search_term_sets.append("#status:=In-Progress")

    return " AND ".join(search_term_sets)


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

    def search(
        self, authors=None, urls=None, series=None, book_formats=None, incomplete=False
    ):
        """Accepts lists of authors/urls/series/formats to search calibredb for.

        All search terms of the same kind are joined with OR; each set of search terms
        is joined with AND. This is because this matches the current use cases I have
        for this method, and may well come back to bite me.

        Returns a list of book ids that match the search.
        """
        search_terms = collate_search_terms(
            authors, book_formats, series, urls, incomplete
        )

        command = f"calibredb search {search_terms} {self.library_access_string}"

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
        result = self.search(series=[series_title])

        return len(result)

    def export(self, book_id, location):
        command = (
            f'calibredb export {book_id} --to-dir "{location}" '
            f"--dont-save-cover --dont-write-opf --single-dir "
            f"{self.library_access_string}"
        )

        try:
            check_and_clean_output(command)
        except CalledProcessError as e:
            raise CalibreException(e.output)

    def list_titles_and_urls(
        self, authors=None, urls=None, series=None, book_formats=None, incomplete=False
    ):
        search_terms = collate_search_terms(
            authors, book_formats, series, urls, incomplete
        )

        command = (
            f"calibredb list --search {search_terms} {self.library_access_string} "
            f"--fields title,*identifier --for-machine"
        )

        try:
            result = check_and_clean_output(command)

            result_json = json.loads(result)
        except CalledProcessError as e:
            if "No books matching the search expression" in e.output:
                return []
            else:
                raise

        return [
            {"title": r["title"], "url": r["*identifier"].replace("url:", "")}
            for r in result_json
        ]

    def add(self, book_filepath, options=None):
        """Add a book to the Calibre library.

        options is a dictionary of option_name: option_value, which will be converted to
        CLI options.
        """
        if options is None:
            options = {}
        options_strings = [f'--{k}="{v}"' for k, v in options.items()]

        command = (
            f'calibredb add -d "{book_filepath}" {" ".join(options_strings)} '
            f"{self.library_access_string}"
        )

        try:
            check_and_clean_output(command)
        except CalledProcessError as e:
            raise CalibreException(e.output)

    def remove(self, book_id):
        command = f"calibredb remove {book_id} {self.library_access_string}"

        try:
            check_and_clean_output(command)
        except CalledProcessError as e:
            raise CalibreException(e.output)

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
        options_strings = [f'--field={k}:"{v}"' for k, v in options.items()]

        command = (
            f"calibredb set_metadata {book_id} {' '.join(options_strings)} "
            f"{self.library_access_string}"
        )

        try:
            check_and_clean_output(command)
        except CalledProcessError as e:
            raise CalibreException(e.output)
