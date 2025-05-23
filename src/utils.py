# encoding: utf-8
import copy
import logging
import re
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

    sensitive_options = ["cookie", "email_password"]
    for o in sensitive_options:
        if options_dict.get(o):
            options_dict[o] = "****"

    # If the Calibre library we're talking to is running on calibreserver, the library
    # option might be something like this:
    # 'http://localhost:8080/#calibre_library" --username=myuser --password="mypassword'
    # Probably we should make this nicer and not abuse the library option for this. ;)
    # In the meantime, redact the password from our output.
    options_dict["library"] = re.sub(
        r"(.*--password(?:=| ))\S+( |$)", r"\1****\2", options_dict["library"]
    )
    return pformat(
        {k: v for k, v in options_dict.items() if k != "command"}, sort_dicts=False
    )
