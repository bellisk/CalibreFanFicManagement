# encoding: utf-8
from csv import DictWriter
from datetime import datetime
from os import getcwd, mkdir
from os.path import isdir, join

from .ao3_utils import (
    get_ao3_subscribed_series_work_counts,
    get_ao3_subscribed_users_work_counts,
)
from .calibre_utils import get_author_works_count, get_series_works_count
from .utils import log

ANALYSIS_TYPES = ["user_subscriptions", "series_subscriptions"]


def _compare_user_subscriptions(username, cookie, path, output_file):
    """Compares the number of fics downloaded for each user subscribed to with the
    number posted to AO3.
    :return:
    """
    print("Comparing user subscriptions on AO3 to Calibre library")

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
        print("Subscribed users who have fewer works on Calibre than on AO3:")
        print(",".join(users_missing_works))
    else:
        print("All subscribed users have as many or more works on Calibre than on AO3.")


def _compare_series_subscriptions(username, cookie, path, output_file):
    """Compares the number of fics downloaded for each series subscribed to with the
    number posted to AO3.
    :return:
    """
    print("Comparing series subscriptions on AO3 to Calibre library")

    ao3_series_work_counts = get_ao3_subscribed_series_work_counts(username, cookie)
    calibre_series_work_counts = {
        u: get_series_works_count(u, path) for u in ao3_series_work_counts.keys()
    }

    series_missing_works = []

    with open(output_file, "a") as f:
        writer = DictWriter(f, ["series", "works on AO3", "works on Calibre"])
        writer.writeheader()
        for s in ao3_series_work_counts:
            if ao3_series_work_counts[s] > calibre_series_work_counts[s]:
                series_missing_works.append(s)

            line = {
                "series": s,
                "works on AO3": ao3_series_work_counts[s],
                "works on Calibre": calibre_series_work_counts[s],
            }
            writer.writerow(line)

    if len(series_missing_works) > 0:
        print("Subscribed series that have fewer works on Calibre than on AO3:")
        print(",".join(series_missing_works))
    else:
        print(
            "All subscribed series have as many or more works on Calibre than on AO3."
        )


def analyse(options):
    if not (options.user and options.cookie):
        log("User and Cookie are required for downloading from AO3", "FAIL")
        return

    path = options.library
    if path:
        path = '--with-library "{}"'.format(path)
        # todo: abstract checking that the library is OK from download and do that here too

    analysis_dir = (
        options.analysis_dir if options.analysis_dir else join(getcwd(), "analysis")
    )

    if not isdir(analysis_dir):
        mkdir(analysis_dir)

    for type in ANALYSIS_TYPES:
        filename = "{}_{}.csv".format(
            type, datetime.strftime(datetime.now(), "%Y%m%d_%H%M%S")
        )
        output_file = join(analysis_dir, filename)

        if type == "user_subscriptions":
            _compare_user_subscriptions(options.user, options.cookie, path, output_file)
        elif type == "series_subscriptions":
            _compare_series_subscriptions(
                options.user, options.cookie, path, output_file
            )
