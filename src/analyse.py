# encoding: utf-8
import locale
from csv import DictWriter
from datetime import datetime
from os import getcwd, mkdir
from os.path import isdir, join

from .ao3_utils import (
    get_ao3_subscribed_series_work_stats,
    get_ao3_subscribed_users_work_counts,
)
from .calibre_utils import get_author_works_count, get_series_works_count
from .download import download
from .exceptions import InvalidConfig
from .utils import log

ANALYSIS_TYPES = ["user_subscriptions", "series_subscriptions"]


def _compare_user_subscriptions(username, cookie, path, output_file):
    """Compares the number of fics downloaded for each user subscribed to with the
    number posted to AO3.
    :return:
    """
    log("Comparing user subscriptions on AO3 to Calibre library", "HEADER")

    ao3_user_work_counts = get_ao3_subscribed_users_work_counts(username, cookie)
    calibre_user_work_counts = {
        u: get_author_works_count(u, path) for u in ao3_user_work_counts.keys()
    }

    users_missing_works = []

    with open(output_file, "a") as f:
        writer = DictWriter(f, ["author", "works on AO3", "works on Calibre"])
        writer.writeheader()
        for u in ao3_user_work_counts:
            if ao3_user_work_counts[u] > calibre_user_work_counts[u]:
                users_missing_works.append(u)

            line = {
                "author": u,
                "works on AO3": ao3_user_work_counts[u],
                "works on Calibre": calibre_user_work_counts[u],
            }
            writer.writerow(line)

    if len(users_missing_works) > 0:
        log("Subscribed users who have fewer works on Calibre than on AO3:", "HEADER")
        for user in users_missing_works:
            log("\t{}".format(user), "BLUE")
    else:
        log(
            "All subscribed users have as many or more works on Calibre than on AO3.",
            "GREEN",
        )

    return users_missing_works


def _compare_series_subscriptions(username, cookie, path, output_file):
    """Compares the number of fics downloaded for each series subscribed to with the
    number posted to AO3.
    :return:
    """
    log("Comparing series subscriptions on AO3 to Calibre library", "HEADER")

    ao3_series_work_stats = get_ao3_subscribed_series_work_stats(username, cookie)
    calibre_series_work_counts = {
        u["Title"]: get_series_works_count(u["Title"], path)
        for u in ao3_series_work_stats.values()
    }

    series_missing_works = {}

    with open(output_file, "a") as f:
        writer = DictWriter(f, ["id", "title", "works on AO3", "works on Calibre"])
        writer.writeheader()
        for series_id, stats in ao3_series_work_stats.items():
            ao3_count = locale.atoi(stats["Works"])
            if ao3_count > calibre_series_work_counts[stats["Title"]]:
                series_missing_works[series_id] = stats["Title"]

            line = {
                "id": series_id,
                "title": stats["Title"],
                "works on AO3": ao3_count,
                "works on Calibre": calibre_series_work_counts[stats["Title"]],
            }
            writer.writerow(line)

    if len(series_missing_works) > 0:
        log("Subscribed series that have fewer works on Calibre than on AO3:", "HEADER")
        for series in series_missing_works.values():
            log("\t{}".format(series), "BLUE")
    else:
        log(
            "All subscribed series have as many or more works on Calibre than on AO3.",
            "GREEN",
        )

    return list(series_missing_works.keys())


def get_analysis_type(analysis_types):
    if len(analysis_types) == 0:
        return ANALYSIS_TYPES

    for t in analysis_types:
        if t not in ANALYSIS_TYPES:
            raise InvalidConfig(
                "Valid 'analysis_type' options are {}, not {}".format(
                    ", ".join(ANALYSIS_TYPES), t
                )
            )

    return analysis_types


def analyse(options):
    if not (options.user and options.cookie):
        log("User and Cookie are required for downloading from AO3", "FAIL")
        return

    path = options.library
    if path:
        path = '--with-library "{}"'.format(path)
        # todo: abstract checking that the library is OK from download and do that here too

    analysis_types = get_analysis_type(options.analysis_type)

    analysis_dir = (
        options.analysis_dir if options.analysis_dir else join(getcwd(), "analysis")
    )

    if not isdir(analysis_dir):
        mkdir(analysis_dir)

    missing_works = {}

    for analysis_type in analysis_types:
        filename = "{}_{}.csv".format(
            analysis_type, datetime.strftime(datetime.now(), "%Y%m%d_%H%M%S")
        )
        output_file = join(analysis_dir, filename)

        if analysis_type == "user_subscriptions":
            missing_works["users"] = _compare_user_subscriptions(
                options.user, options.cookie, path, output_file
            )
        elif analysis_type == "series_subscriptions":
            missing_works["series"] = _compare_series_subscriptions(
                options.user, options.cookie, path, output_file
            )

    if options.fix:
        log("Sending missing works to be downloaded", "HEADER")
        options.source = []
        for key, value in missing_works.items():
            options.source.append(key)

        options.usernames = missing_works.get("usernames", [])
        options.series = missing_works.get("series", [])

        options.since_last_update = False
        options.since = None

        download(options)
