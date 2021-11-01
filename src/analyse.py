# encoding: utf-8

from .utils import log


def analyse(options):
    if not (options.user and options.cookie):
        log("User and Cookie are required for downloading from AO3", "FAIL")
        return
    # Get AO3 bookmarks
    # Return requested analysis
