# encoding: utf-8
import locale
import re
from subprocess import PIPE, STDOUT, check_output

from .ao3_utils import AO3_SERIES_KEYS
from .utils import log

ADD_GROUPED_SEARCH_SCRIPT = """from calibre.library import db

db = db("%s").new_api
db.set_pref("grouped_search_terms", {"allseries": ["series", "series00", "series01", "series02", "series03"]})
print(db.pref("grouped_search_terms"))
"""
series_pattern = re.compile("(.*) \[(.*)\]")


def check_or_create_words_column(path):
    res = check_output(
        "calibredb custom_columns {}".format(path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    columns = res.decode("utf-8").split("\n")
    for c in columns:
        if c.startswith("words ("):
            return

    log("Adding custom column 'words' to Calibre library")
    check_output(
        "calibredb add_custom_column {} words Words int".format(path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )


def check_or_create_extra_series_columns(path):
    res = check_output(
        "calibredb custom_columns {}".format(path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    # Get rid of the number after each column name, e.g. "columnname (1)"
    columns = [c.split(" ")[0] for c in res.decode("utf-8").split("\n")]
    if set(columns).intersection(AO3_SERIES_KEYS) == set(AO3_SERIES_KEYS):
        log("Custom AO3 series columns are in Calibre Library")
    else:
        log("Adding custom AO3 series columns to Calibre library")
        for c in AO3_SERIES_KEYS:
            check_output(
                "calibredb add_custom_column {} {} {} series".format(path, c, c),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )
        log("Adding grouped search term 'allseries' to Calibre Library")
        _add_grouped_search_terms(path)


def _add_grouped_search_terms(path):
    # The path that we usually use is constructed out of several parts,
    # including '--with-path' option and potentially username and password.
    # Here we just want the path to the library.
    just_library_path = path.split('"')[1]
    # Add a new grouped search term "allseries" so that Calibre can search across all
    # the series columns.
    script = ADD_GROUPED_SEARCH_SCRIPT % just_library_path
    res = check_output(
        "calibre-debug -c '{}'".format(script),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    log(res)


def get_series_options(metadata):
    if len(metadata["series"]) > 0:
        m = series_pattern.match(metadata["series"])
        return '--series="{}" --series-index={} '.format(m.group(1), m.group(2))
    return ""


def get_extra_series_data(story_id, metadata):
    # The command to set custom column data is:
    # 'calibredb set_custom [options] column id value'
    # Here we return a list of (column, value) tuples for each additional series
    # field that contains data, plus its index.
    existing_series = metadata["series"]
    series_keys = ["series00", "series01", "series02", "series03"]
    result = []
    for key in series_keys:
        if len(metadata[key]) > 0 and metadata[key] != existing_series:
            m = series_pattern.match(metadata[key])
            result.append((key, m.group(0)))

    return result


def get_tags_options(metadata):
    tag_keys = [
        "ao3categories",
        "characters",
        "fandoms",
        "freeformtags",
        "rating",
        "ships",
        "status",
        "warnings",
    ]
    opts = "--tags="
    for key in tag_keys:
        if len(metadata[key]) > 0:
            tags = metadata[key].split(", ")
            for tag in tags:
                # Replace characters that give Calibre trouble in tags.
                tag = tag.replace('"', "'").replace("...", "…").replace(".", "．")
                opts += '"{}",'.format("fanfic." + key + "." + tag)

    return opts


def get_word_count(metadata):
    return locale.atoi(metadata.get("numWords", 0))


def get_author_works_count(author, path):
    result = check_output(
        "calibredb search author:{} {}".format(author, path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    return len(str(result).split(","))


def get_series_works_count(series_title, path):
    # Calibre seems to escape only this character in series titles
    series_title = series_title.replace("&", "&amp;")
    result = check_output(
        'calibredb search series:"=\\"{}\\"" {}'.format(series_title, path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    return len(str(result).split(","))
