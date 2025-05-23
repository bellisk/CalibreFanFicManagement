# encoding: utf-8
import locale
from csv import DictWriter
from datetime import datetime
from os import mkdir
from os.path import isdir, join

from .ao3_utils import (
    get_ao3_series_work_urls,
    get_ao3_subscribed_series_work_stats,
    get_ao3_subscribed_users_work_counts,
    get_ao3_users_work_urls,
)
from .calibre_utils import (
    CalibreException,
    CalibreHelper,
    get_author_work_urls,
    get_author_works_count,
    get_incomplete_work_data,
    get_series_work_urls,
    get_series_works_count,
)
from .download import download
from .options import INCOMPLETE, SOURCE_SERIES_SUBSCRIPTIONS, SOURCE_USER_SUBSCRIPTIONS
from .utils import AO3_DEFAULT_URL, Bcolors, log, setup_login


def _compare_user_subscriptions(
    username, cookie, path, output_file, ao3_url=AO3_DEFAULT_URL
):
    """Compares the number of fics downloaded for each user subscribed to with the
    number posted to AO3.
    :return:
    """
    log("Comparing user subscriptions on AO3 to Calibre library", Bcolors.HEADER)

    ao3_user_work_counts = get_ao3_subscribed_users_work_counts(
        username, cookie, ao3_url=ao3_url
    )
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
        log(
            "Subscribed users who have fewer works on Calibre than on AO3:",
            Bcolors.HEADER,
        )
        for user in users_missing_works:
            log(f"\t{user}", Bcolors.OKBLUE)
    else:
        log(
            "All subscribed users have as many or more works on Calibre than on AO3.",
            Bcolors.OKGREEN,
        )

    return users_missing_works


def _compare_series_subscriptions(
    username, cookie, path, output_file, ao3_url=AO3_DEFAULT_URL
):
    """Compares the number of fics downloaded for each series subscribed to with the
    number posted to AO3.
    :return:
    """
    log("Comparing series subscriptions on AO3 to Calibre library", Bcolors.HEADER)

    ao3_series_work_stats = get_ao3_subscribed_series_work_stats(
        username, cookie, ao3_url=ao3_url
    )
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
        log(
            "Subscribed series that have fewer works on Calibre than on AO3:",
            Bcolors.HEADER,
        )
        for series in series_missing_works.values():
            log(f"\t{series}", Bcolors.OKBLUE)
    else:
        log(
            "All subscribed series have as many or more works on Calibre than on AO3.",
            Bcolors.OKGREEN,
        )

    return series_missing_works


def _get_missing_work_urls_from_users(
    users_missing_works, username, cookie, path, ao3_url=AO3_DEFAULT_URL
):
    log("Getting urls for works missing from subscribed users.")
    missing_work_urls = []
    for u in users_missing_works:
        log(u)
        ao3_urls = get_ao3_users_work_urls(
            user=username,
            cookie=cookie,
            username=u,
            max_count=None,
            oldest_date=None,
            ao3_url=ao3_url,
        )
        calibre_urls = get_author_work_urls(u, path)
        missing_work_urls.extend(set(ao3_urls) - set(calibre_urls))

    log(f"Found {len(missing_work_urls)} urls to import")
    return missing_work_urls


def _get_missing_work_urls_from_series(
    series_missing_works, username, cookie, path, ao3_url=AO3_DEFAULT_URL
):
    log("Getting urls for works missing from subscribed series.")
    missing_work_urls = []
    for series_id, series_title in series_missing_works.items():
        log(series_title, series_id)
        ao3_urls = get_ao3_series_work_urls(
            user=username,
            cookie=cookie,
            max_count=None,
            series_id=series_id,
            ao3_url=ao3_url,
        )
        calibre_urls = get_series_work_urls(series_title, path)
        missing_work_urls.extend(set(ao3_urls) - set(calibre_urls))

    log(f"Found {len(missing_work_urls)} urls to import.")
    return missing_work_urls


def _collect_incomplete_works(path, output_file):
    log("Getting urls for all works in Calibre library that are marked In Progress.")
    results = get_incomplete_work_data(path)

    with open(output_file, "a") as f:
        writer = DictWriter(f, ["title", "url"])
        writer.writeheader()
        for work_data in results:
            writer.writerow(work_data)

    log(f"Found {len(results)} incomplete works.")

    return [work_data["url"] for work_data in results]


def analyse(options):
    setup_login(options)
    calibre = CalibreHelper(library_path=options.path, user=None, password=None)

    try:
        calibre.check_library()
    except CalibreException as e:
        log(str(e), Bcolors.FAIL)
        return

    if not isdir(options.analysis_dir):
        mkdir(options.analysis_dir)

    missing_works = []

    try:
        for analysis_type in options.analysis_type:
            filename = f"{analysis_type}_{datetime.strftime(datetime.now(), '%Y%m%d_%H%M%S')}.csv"
            output_file = join(options.analysis_dir, filename)

            if analysis_type == SOURCE_USER_SUBSCRIPTIONS:
                users_missing_works = _compare_user_subscriptions(
                    options.user, options.cookie, path, output_file, options.mirror
                )
                missing_works.extend(
                    _get_missing_work_urls_from_users(
                        users_missing_works,
                        options.user,
                        options.cookie,
                        path,
                        options.mirror,
                    )
                )
            elif analysis_type == SOURCE_SERIES_SUBSCRIPTIONS:
                series_missing_works = _compare_series_subscriptions(
                    options.user, options.cookie, path, output_file, options.mirror
                )
                missing_works.extend(
                    _get_missing_work_urls_from_series(
                        series_missing_works,
                        options.user,
                        options.cookie,
                        path,
                        options.mirror,
                    )
                )
            elif analysis_type == INCOMPLETE:
                missing_works.extend(_collect_incomplete_works(path, output_file))
    except Exception as e:
        # Save work urls to file (add to existing content, don't overwrite)
        with open(options.input, "a") as fp:
            for url in missing_works:
                fp.write(url + "\n")

        log(f"Error running analysis: {e}", Bcolors.FAIL)
        log(
            f"All work urls gathered so far have been saved in the file {options.input}"
        )

    if options.fix:
        log("Sending missing/incomplete works to be downloaded", Bcolors.HEADER)

        # Save work urls to file (add to existing content, don't overwrite)
        with open(options.input, "a") as fp:
            for url in missing_works:
                fp.write(url + "\n")

        options.sources = ["file"]
        options.since_last_update = False
        options.since = None

        download(options)
