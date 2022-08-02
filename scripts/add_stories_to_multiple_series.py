import json
import re
from os import listdir
from os.path import isfile, join
from subprocess import PIPE, STDOUT, check_output
from sys import argv
from tempfile import mkdtemp

from ebooklib import epub

# The AO3 metadata that we get from FanficFare includes these series keys as well as
# "series". Since "series" is a default Calibre field, we can ignore it here.
AO3_SERIES_KEYS = ["series00", "series01", "series02", "series03"]
PATH = '"/home/rae/Calibre Fanfic Library"'
ADD_GROUPED_SEARCH_SCRIPT = """from calibre.library import db

db = db(%s).new_api
db.set_pref("grouped_search_terms", {"allseries": ["series", "series00", "series01", "series02", "series03"]})
print(db.pref("grouped_search_terms"))
"""
series_link_pattern = re.compile(
    '<a class="serieslink" href="https://archiveofourown\.org/series/([\d]+)">(.+) \[[\d]*]</a>'
)


def check_or_create_extra_series_columns(path):
    res = check_output(
        "calibredb custom_columns --with-library {}".format(path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    # Get rid of the number after each column name, e.g. "columnname (1)"
    columns = [c.split(" ")[0] for c in res.decode("utf-8").split("\n")]
    if set(columns).intersection(AO3_SERIES_KEYS) == set(AO3_SERIES_KEYS):
        print("Custom AO3 series columns are in Calibre Library")
    else:
        print("Adding custom AO3 series columns to Calibre library")
        for c in AO3_SERIES_KEYS:
            check_output(
                "calibredb add_custom_column --with-library {} {} {} series".format(
                    path, c, c
                ),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )

    print("Adding grouped search term 'allseries' to Calibre Library")
    _add_grouped_search_terms(path)


def _add_grouped_search_terms(path):
    # Add a new grouped search term "allseries" so that Calibre can search across all
    # the series columns.
    script = ADD_GROUPED_SEARCH_SCRIPT % path
    res = check_output(
        "calibre-debug -c '{}'".format(script),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    print(res)


def find_books_in_series(path):
    res = check_output(
        "calibredb list --with-library {} --search series:true --fields id,series,series_index --for-machine".format(
            path
        ),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    book_data = json.loads(res.decode("utf-8"))
    print("Found data about {} books that belong to series".format(len(book_data)))
    return book_data


def filter_books_in_multiple_series(path, book_data):
    n = 0
    series_ids_to_import = []
    for book in book_data:
        if n % 10 == 0:
            print("Processed {} books".format(str(n)))

        series_1 = book["series"]
        loc = mkdtemp()
        check_output(
            'calibredb export --dont-save-cover --dont-write-opf --single-dir --to-dir "{}" --with-library {} {}'.format(
                loc, path, book["id"]
            ),
            shell=True,
            stdin=PIPE,
            stderr=STDOUT,
        )
        story_file = _get_files(loc, ".epub", True)[0]
        book = epub.read_epub(story_file)
        title_page = book.get_item_with_id("title_page")
        html = str(title_page.get_body_content())

        m2 = series_link_pattern.search(html)
        if m2:
            series_2 = m2.group(2).replace("\\'", "'")
            series_2_id = m2.group(1)
            if series_1 != series_2:
                series_ids_to_import.append(series_2_id)
                print(
                    "{} (series saved in Calibre) does not match {} ({}) (series in epub title page)".format(
                        series_1, series_2, series_2_id
                    )
                )
        else:
            print("No series title found!")

        n += 1

    return series_ids_to_import


def _get_files(mypath, filetype=None, fullpath=False):
    if filetype:
        ans = [
            f
            for f in listdir(mypath)
            if isfile(join(mypath, f)) and f.endswith(filetype)
        ]
    else:
        ans = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    if fullpath:
        return [join(mypath, f) for f in ans]
    else:
        return ans


if __name__ == "__main__":
    path = PATH
    if len(argv) > 1:
        path = argv[1]

    check_or_create_extra_series_columns(path)

    # Next: export all fics from calibre that are in a series.
    # It looks like, if a fic is in more than one series, we save it into a different
    # series than is added to the epub front page by fanficfare.
    # So, look for all fics that have more than one series according to that measure.

    books_in_series = find_books_in_series(path)
    series_to_reimport = filter_books_in_multiple_series(path, books_in_series)

    # Then get the metadata from AO3, and add multiple series to the ebook metadata,
    # and save.
