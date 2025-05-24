# encoding: utf-8
import copy
import locale
import logging
from os import listdir
from os.path import isfile, join
from pprint import pformat
from subprocess import PIPE, STDOUT, check_output
from time import localtime, strftime
from urllib.parse import urlparse

import browser_cookie3

from src.exceptions import InvalidConfig

AO3_DEFAULT_URL = "https://archiveofourown.org"
DATE_FORMAT = "%d.%m.%Y"
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

# Set threshold levels for fanficfare's loggers, so we don't get spammed with logs
logging.getLogger("fanficfare").setLevel(logging.ERROR)
logging.getLogger("fanficfare.configurable").setLevel(logging.ERROR)


class Bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def log(msg, color=None, output=True):
    if color:
        line = (
            f"{Bcolors.BOLD}{strftime('%m/%d/%Y %H:%M:%S', localtime())}"
            f"{Bcolors.ENDC}: \t {color}{msg}{Bcolors.ENDC}"
        )
    else:
        line = (
            f"{Bcolors.BOLD}{strftime('%m/%d/%Y %H:%M:%S', localtime())}"
            f"{Bcolors.ENDC}: \t {msg}"
        )
    if output:
        print(line)
        return ""
    else:
        return line + "\n"


def get_files(mypath, filetype=None, fullpath=False):
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


def setup_login(options):
    # We have already validated in setup_options that we have at least one of
    # options.cookie and options.use_browser_cookie.
    if options.use_browser_cookie:
        found_cookie = False
        ao3_domain = urlparse(options.mirror).netloc
        cookie_jar = browser_cookie3.firefox(domain_name=ao3_domain)
        for cookie in cookie_jar:
            if cookie.name == "_otwarchive_session":
                options.cookie = cookie.value
                found_cookie = True
                break

        if found_cookie:
            log("Found _otwarchive_session cookie from the browser")
            return

        log(
            f"Tried to get the _otwarchive_session cookie from your browser, "
            f"but couldn't find it. Are you logged in to {options.mirror}?"
        )
        if options.cookie:
            log("Falling back to the cookie value you passed in")
            return

        raise InvalidConfig(
            f"Tried to get the _otwarchive_session cookie from your browser, "
            f"but couldn't find it. Are you logged in to {options.mirror}?"
        )

    log("Using the cookie value you passed in")


def check_subprocess_output(command):
    return check_output(command, shell=True, stderr=STDOUT, stdin=PIPE, text=True)


def get_options_for_display(options):
    options_copy = copy.copy(options)
    options_dict = vars(options_copy)

    sensitive_options = ["calibre_password", "cookie", "email_password"]
    for o in sensitive_options:
        if options_dict.get(o):
            options_dict[o] = "****"

    return pformat(
        {k: v for k, v in options_dict.items() if k != "command"}, sort_dicts=False
    )


def get_series_options(metadata):
    if len(metadata["series"]) == 0:
        return {}

    return {"series": metadata["series"]}


def get_extra_series_options(metadata):
    existing_series = metadata["series"]
    series_keys = ["series00", "series01", "series02", "series03"]
    opts = {}
    for key in series_keys:
        if len(metadata[key]) > 0 and metadata[key] != existing_series:
            opts[f"#{key}"] = metadata[key]

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
                tag.replace('"', "'")
                .replace("...", "…")
                .replace(".", "．")
                .replace("&amp;", "&")
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


def get_all_metadata_options(metadata):
    options = {"#words": get_word_count(metadata)}
    options.update(get_series_options(metadata))
    options.update(get_extra_series_options(metadata))
    options.update(get_tags_options(metadata))

    return options
