# encoding: utf-8
import locale
import re
from subprocess import PIPE, STDOUT, check_output

series_pattern = re.compile("(.*) \[(.*)\]")


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
        print(key, metadata[key])
        if len(metadata[key]) > 0 and metadata[key] != existing_series:
            m = series_pattern.match(metadata[key])
            result.append((key, m.group(0)))
            # result.append(("{}-index".format(key), m.group(2)))

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
