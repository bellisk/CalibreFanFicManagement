# encoding: utf-8
import locale
import re

series_pattern = re.compile("(.*) \[(.*)\]")


def get_series_options(metadata):
    series_keys = ["series", "series00", "series01", "series02", "series03"]
    opts = ""
    for key in series_keys:
        if len(metadata[key]) > 0:
            m = series_pattern.match(metadata[key])
            opts += '--series="{}" --series-index={} '.format(m.group(1), m.group(2))

    return opts


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
