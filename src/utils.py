# encoding: utf-8
import logging
from os import listdir
from os.path import isfile, join
from time import localtime, strftime

import browser_cookie3

from src.exceptions import InvalidConfig

logging.getLogger("fanficfare").setLevel(logging.ERROR)


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
        cookie_jar = browser_cookie3.load(domain_name="archiveofourown.org")
        for cookie in cookie_jar:
            if cookie.name == "_otwarchive_session":
                options.cookie = cookie.value
                found_cookie = True
                break

        if found_cookie:
            log("Found _otwarchive_session cookie from the browser")
            return

        log(
            "Tried to get the _otwarchive_session cookie from your browser, "
            "but couldn't find it. Are you logged in to AO3?"
        )
        if options.cookie:
            log("Falling back to the cookie value you passed in")
            return

        raise InvalidConfig(
            "Tried to get the _otwarchive_session cookie from your browser, "
            "but couldn't find it. Are you logged in to AO3?"
        )

    log("Using the cookie value you passed in")
