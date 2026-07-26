import re

AO3_DEFAULT_URL = "https://archiveofourown.org"
AO3_SERIES_KEYS = ["series00", "series01", "series02", "series03"]
story_url = re.compile(r"(https://archiveofourown.org/works/\d*).*")


def get_ao3_bookmark_urls(
    api,
    expand_series,
    max_count,
    oldest_date,
    sort_by_updated,
):
    urls = [
        api.work_url_from_id(work_id)
        for work_id in api.user.bookmarks_ids(
            max_count, expand_series, oldest_date, sort_by_updated
        )
    ]
    return set(urls)


def get_ao3_users_work_urls(api, username, max_count, oldest_date):
    urls = [
        api.work_url_from_id(work_id)
        for work_id in api.author(username).work_ids(max_count, oldest_date)
    ]
    return set(urls)


def get_ao3_gift_urls(api, max_count, oldest_date):
    urls = [
        api.work_url_from_id(work_id)
        for work_id in api.user.gift_ids(max_count, oldest_date)
    ]
    return set(urls)


def get_ao3_marked_for_later_urls(api, max_count, oldest_date):
    urls = [
        api.work_url_from_id(work_id)
        for work_id in api.user.marked_for_later_ids(max_count, oldest_date)
    ]
    return set(urls)


def get_ao3_work_subscription_urls(api, max_count, oldest_date=None):
    """Get urls of works that the user is subscribed to.

    Using oldest_date is slow, because we have to load every work page and
    check its date to decide if we keep it.
    """
    if oldest_date:
        urls = []
        for work_id in api.user.work_subscription_ids(max_count):
            _append_work_id_if_newer_than_given_date(api, oldest_date, urls, work_id)

        return set(urls)

    urls = [
        api.work_url_from_id(work_id)
        for work_id in api.user.work_subscription_ids(max_count)
    ]

    return set(urls)


def _append_work_id_if_newer_than_given_date(api, oldest_date, urls, work_id):
    work = api.work(work_id)
    if work.completed > oldest_date.date():
        urls.append(work.url)


def get_ao3_series_subscription_urls(api, max_count, oldest_date=None):
    series_ids = api.user.series_subscription_ids(max_count)

    urls = []
    for s in series_ids:
        urls += [
            api.work_url_from_id(work_id)
            for work_id in api.series(s).work_ids(max_count, oldest_date)
        ]

    return set(urls)


def get_ao3_user_subscription_urls(api, max_count, oldest_date=None):
    user_ids = api.user.user_subscription_ids(max_count)

    urls = []
    for u in user_ids:
        print(u)
        urls += [
            api.work_url_from_id(work_id)
            for work_id in api.author(u).work_ids(max_count, oldest_date)
        ]

    return set(urls)


def get_ao3_series_work_urls(api, max_count, series_id, oldest_date=None):
    urls = [
        api.work_url_from_id(work_id)
        for work_id in api.series(series_id).work_ids(max_count, oldest_date)
    ]

    return set(urls)


def get_ao3_collection_work_urls(api, max_count, collection_id, oldest_date=None):
    urls = [
        api.work_url_from_id(work_id)
        for work_id in api.collection(collection_id).work_ids(max_count, oldest_date)
    ]

    return set(urls)


def get_ao3_subscribed_users_work_counts(api):
    user_ids = api.user.user_subscription_ids()

    counts = {}
    for username in user_ids:
        counts[username] = api.author(username).works_count()

    return counts


def get_ao3_subscribed_series_work_stats(api):
    series_ids = api.user.series_subscription_ids()

    stats = {}
    for s in series_ids:
        stats[s] = api.series(s).info()

    return stats


def normalise_urls(urls, base_url=None):
    def normalise(url):
        url = url.replace("http://", "https://")
        if base_url:
            url = url.replace(base_url, AO3_DEFAULT_URL)
        m = story_url.match(url)
        if m:
            return m.group(1)
        raise RuntimeError(
            f"Malformed url: '{url}'. If you're using an AO3 mirror site, "
            f"please pass the url into the command with the option --mirror"
        )

    urls = set(urls)

    return {normalise(url) for url in urls}
