# encoding: utf-8
from configparser import ConfigParser
from optparse import OptionParser, OptionValueError

from .utils import touch

SOURCES = "sources"
SOURCE_FILE = "file"
SOURCE_BOOKMARKS = "bookmarks"
SOURCE_WORKS = "works"
SOURCE_GIFTS = "gifts"
SOURCE_LATER = "later"
SOURCE_STDIN = "stdin"
SOURCE_WORK_SUBSCRIPTIONS = "work_subscriptions"
SOURCE_SERIES_SUBSCRIPTIONS = "series_subscriptions"
SOURCE_USER_SUBSCRIPTIONS = "user_subscriptions"
SOURCE_ALL_SUBSCRIPTIONS = "all_subscriptions"
SOURCE_USERNAMES = "usernames"
SOURCE_SERIES = "series"
SOURCE_COLLECTIONS = "collections"

DEFAULT_SOURCES = [SOURCE_FILE, SOURCE_BOOKMARKS, SOURCE_LATER]
SUBSCRIPTION_SOURCES = [
    SOURCE_SERIES_SUBSCRIPTIONS,
    SOURCE_USER_SUBSCRIPTIONS,
    SOURCE_WORK_SUBSCRIPTIONS,
]
VALID_INPUT_SOURCES = [
    SOURCE_FILE,
    SOURCE_BOOKMARKS,
    SOURCE_WORKS,
    SOURCE_GIFTS,
    SOURCE_LATER,
    SOURCE_STDIN,
    SOURCE_WORK_SUBSCRIPTIONS,
    SOURCE_SERIES_SUBSCRIPTIONS,
    SOURCE_USER_SUBSCRIPTIONS,
    SOURCE_ALL_SUBSCRIPTIONS,
    SOURCE_USERNAMES,
    SOURCE_SERIES,
    SOURCE_COLLECTIONS,
]


def set_sources(option, opt_str, value, parser):
    if len(value) == 0:
        return DEFAULT_SOURCES

    sources = []
    if value == SOURCE_USERNAMES and parser.values.usernames is None:
        raise OptionValueError(
            "A list of usernames is required when source 'usernames' is given."
        )
    if value == SOURCE_SERIES and parser.values.series is None:
        raise OptionValueError(
            "A list of series ids is required when source 'series' is given."
        )
    if value == SOURCE_COLLECTIONS and parser.values.collections is None:
        raise OptionValueError(
            "A list of collection ids is required when source 'collections' is given."
        )

    if value == SOURCE_ALL_SUBSCRIPTIONS:
        sources.extend(SUBSCRIPTION_SOURCES)
    else:
        sources.append(value)

    parser.values.source = sources


def set_up_options():
    usage = """usage: python %prog [command] [flags]
    
Commands available:
    
download    Download fics from AO3 and save to Calibre library
analyse     Analyse contents of Calibre library and AO3 data
    """
    option_parser = OptionParser(usage=usage)

    option_parser.add_option(
        "-u", "--user", action="store", dest="user", help="AO3 username. Required."
    )

    option_parser.add_option(
        "-c",
        "--cookie",
        action="store",
        dest="cookie",
        help="""Contents of _otwarchive_session cookie. Required (if
--use-browser-cookie is not set).""",
    )

    option_parser.add_option(
        "--use-browser-cookie",
        action="store_true",
        dest="use_browser_cookie",
        help="""Get the _otwarchive_session cookie from your browser instead of 
passing it in with the -c option.""",
    )

    option_parser.add_option(
        "-s",
        "--source",
        action="callback",
        callback=set_sources,
        type="choice",
        choices=VALID_INPUT_SOURCES,
        nargs=1,
        help=f"""Valid sources are: {', '.join(VALID_INPUT_SOURCES)}.
        
Specify each source separately, e.g.:

-s bookmarks -s later -s usernames --usernames janedoe,johndoe

Using '⁻s work_subscriptions' with --since or --since-last-update is slow!
'file': read AO3 urls from the file specified in --input.
'stdin': read AO3 urls from stdin.
'usernames': get all works from one or more users. Specify users with --usernames.
'series': get all works from one or more series. Specify series ids with --series.
'collections': get all works from one or more collections. Specify collection ids with
--collections.

Default: file,bookmarks,later""",
    )

    option_parser.add_option(
        "-m",
        "--max-count",
        action="store",
        dest="max_count",
        type="int",
        default=None,
        help="""Maximum number of fics to get from AO3. Default: no limit.""",
    )

    option_parser.add_option(
        "--usernames",
        action="store",
        dest="usernames",
        help="""One or more usernames to download all works from, comma separated.""",
    )

    option_parser.add_option(
        "--series",
        action="store",
        dest="series",
        help="""One or more series to download all works from.""",
    )

    option_parser.add_option(
        "--collections",
        action="store",
        dest="collections",
        help="""One or more collections to download all works from.""",
    )

    option_parser.add_option(
        "-S",
        "--since",
        action="store",
        dest="since",
        help="""DD.MM.YYYY. The date since which fics should be downloaded (date 
bookmarked or updated for bookmarks, date last visited for marked-for-later).
Using this with source=work_subscriptions is slow!""",
    )

    option_parser.add_option(
        "-L",
        "--since-last-update",
        action="store_true",
        dest="since_last_update",
        default=False,
        help="""Only fetch work ids from AO3 for works that have been changed since the
last update, as saved in the last_update_file. For bookmarked works, this fetches works 
that have been bookmarked or updated since the last update. For marked-for-later works, 
it fetches works that have been marked-for-later since the last update. For works from
subscriptions, it fetches works that have been posted or updated since the last update.
Lists of work urls (from the input file or from stdin) will be handled without checking 
any dates. This option overrides --since.""",
    )

    option_parser.add_option(
        "-e",
        "--expand-series",
        action="store_true",
        dest="expand_series",
        default=False,
        help="Whether to get all works from a bookmarked series.",
    )

    option_parser.add_option(
        "-f",
        "--force",
        action="store_true",
        dest="force",
        default=False,
        help="""Whether to force downloads of stories even when they have the same
number of chapters locally as online.""",
    )

    option_parser.add_option(
        "-i",
        "--input",
        action="store",
        dest="input",
        help="""Error file. Any urls that fail will be output here, and file will be
read to find any urls that failed previously. If file does not exist will create. File
is overwitten every time the program is run.""",
    )

    option_parser.add_option(
        "-l",
        "--library",
        action="store",
        dest="library",
        help="""calibre library db location. If none is passed, then this merely 
downloads stories into the current directory as epub files.""",
    )

    option_parser.add_option(
        "-d",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="Dry run: only fetch bookmark links from AO3, don't add them to calibre",
    )

    option_parser.add_option(
        "-C",
        "--config",
        action="store",
        dest="config",
        help="""Config file for inputs. Blank config file is provided.
Commandline options overrule config file.
Do not put any quotation marks in the options.""",
    )

    option_parser.add_option(
        "-F",
        "--fanficfare-config",
        action="store",
        dest="fanficfare_config",
        help="Config file for fanficfare.",
    )

    option_parser.add_option(
        "-o",
        "--output",
        action="store_true",
        dest="live",
        default=False,
        help="""Include this if you want all the output to be saved and posted live.
Useful when multithreading.""",
    )

    option_parser.add_option(
        "-U",
        "--last-update-file",
        action="store",
        dest="last_update_file",
        default="last_update.json",
        help="""Json file storing dates of last successful update from various sources.
Example: {"later": "01.01.2021", "bookmarks": "02.01.2021"}.
Will be created if it doesn't exist. Default: 'last_update.json'.""",
    )

    option_parser.add_option(
        "-a",
        "--analysis-dir",
        action="store",
        dest="analysis_dir",
        default="analysis",
        help="""Directory to save output of analysis in. Will be created if it doesn't
exist. Default: analysis/""",
    )

    option_parser.add_option(
        "--analysis-type",
        action="store",
        dest="analysis_type",
        default="user_subscriptions,series_subscriptions,incomplete_works",
        help="""Which source(s) should be analysed to see if all works are in Calibre?
Options: 'user_subscriptions', 'series_subscriptions', 'incomplete_works'. Default is
all of these.""",
    )

    option_parser.add_option(
        "--fix",
        action="store_true",
        dest="fix",
        default=False,
        help="""If missing works are discovered during analysis, download them.""",
    )

    (options, args) = option_parser.parse_args()

    if len(args) != 1:
        raise ValueError("Please input exactly one command, e.g. 'download'")

    command = args[0]

    if options.config:
        touch(options.config)
        config = ConfigParser(allow_no_value=True)
        config.read(options.config)

        def updater(option, newval):
            return newval if newval is not None else option

        for sect in config.sections():
            for opt in config.options(sect):
                config_file_option = config.get(sect, opt).strip()
                cli_option = getattr(options, opt)
                setattr(options, opt, updater(config_file_option, cli_option))

    options.usernames = (
        options.usernames.split(",") if len(options.usernames) > 0 else []
    )
    options.series = options.series.split(",") if len(options.series) > 0 else []
    options.collections = (
        options.collections.split(",") if len(options.collections) > 0 else []
    )
    options.analysis_type = (
        options.analysis_type.split(",") if len(options.analysis_type) > 0 else []
    )

    return command, options
