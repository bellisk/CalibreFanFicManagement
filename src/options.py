# encoding: utf-8
import sys
from argparse import ArgumentParser, ArgumentTypeError
from configparser import ConfigParser
from datetime import datetime

from src.utils import AO3_DEFAULT_URL, DATE_FORMAT

COMMANDS = ["download", "analyse"]

SOURCES = "sources"
SOURCE_FILE = "file"
SOURCE_BOOKMARKS = "bookmarks"
SOURCE_WORKS = "works"
SOURCE_GIFTS = "gifts"
SOURCE_LATER = "later"
SOURCE_STDIN = "stdin"
SOURCE_IMAP = "imap"
SOURCE_WORK_SUBSCRIPTIONS = "work_subscriptions"
SOURCE_SERIES_SUBSCRIPTIONS = "series_subscriptions"
SOURCE_USER_SUBSCRIPTIONS = "user_subscriptions"
SOURCE_ALL_SUBSCRIPTIONS = "all_subscriptions"
SOURCE_USERNAMES = "usernames"
SOURCE_SERIES = "series"
SOURCE_COLLECTIONS = "collections"
INCOMPLETE = "incomplete_works"
DEFAULT_LAST_UPDATE_FILE = "last_update.json"

ANALYSIS_TYPES = [
    SOURCE_USER_SUBSCRIPTIONS,
    SOURCE_SERIES_SUBSCRIPTIONS,
    SOURCE_WORK_SUBSCRIPTIONS,
    INCOMPLETE,
]
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
    SOURCE_IMAP,
    SOURCE_WORK_SUBSCRIPTIONS,
    SOURCE_SERIES_SUBSCRIPTIONS,
    SOURCE_USER_SUBSCRIPTIONS,
    SOURCE_ALL_SUBSCRIPTIONS,
    SOURCE_USERNAMES,
    SOURCE_SERIES,
    SOURCE_COLLECTIONS,
]


def validate_sources(options):
    for s in options.sources:
        if s not in VALID_INPUT_SOURCES:
            raise ArgumentTypeError(
                f"Valid 'sources' options are {', '.join(VALID_INPUT_SOURCES)}, not {s}"
            )

    if SOURCE_USERNAMES in options.sources and options.usernames is None:
        raise ArgumentTypeError(
            "A list of usernames is required when source 'usernames' is given."
        )
    if SOURCE_SERIES in options.sources and options.series is None:
        raise ArgumentTypeError(
            "A list of series ids is required when source 'series' is given."
        )
    if SOURCE_COLLECTIONS in options.sources and options.collections is None:
        raise ArgumentTypeError(
            "A list of collection ids is required when source 'collections' is given."
        )

    options_dict = vars(options)
    required_email_options = [
        options_dict.get("email_server"),
        options_dict.get("email_user"),
        options_dict.get("email_password"),
        options_dict.get("email_folder"),
    ]
    if SOURCE_IMAP in options.sources and not all(required_email_options):
        raise ArgumentTypeError(
            """The following options are required when source 'imap' is given:
    --email-server
    --email-user
    --email-password
    --email-folder"""
        )

    if SOURCE_ALL_SUBSCRIPTIONS in options.sources:
        options.sources.extend(SUBSCRIPTION_SOURCES)


def validate_cookie(options):
    if not options.cookie and not options.use_browser_cookie:
        raise ArgumentTypeError(
            "It's required either to pass in a cookie with -c/--cookie or to use the "
            "--use-browser-cookie option."
        )


def validate_user(options):
    if not options.user:
        raise ArgumentTypeError("The argument user is required.")


def validate_since(options):
    if options.since:
        try:
            datetime.strptime(options.since, DATE_FORMAT)
        except ValueError:
            raise ArgumentTypeError("'since' option should have format DD.MM.YYYY")


def validate_analysis_type(options):
    for t in options.analysis_type:
        if t not in ANALYSIS_TYPES:
            raise ArgumentTypeError(
                f"Valid 'analysis_type' options are "
                f"{', '.join(ANALYSIS_TYPES)}, not {t}"
            )


def comma_separated_list(value):
    return value.split(",")


def set_up_options():
    usage = """usage: python %(prog)s [command] [flags]

Commands available:

download    Download fics from AO3 and save to Calibre library
analyse     Analyse contents of Calibre library and AO3 data
    """

    arg_parser = ArgumentParser(usage=usage)

    arg_parser.add_argument("command", action="store", choices=COMMANDS)

    arg_parser.add_argument(
        "-u",
        "--user",
        action="store",
        dest="user",
        help="AO3 username. Required.",
    )

    arg_parser.add_argument(
        "-c",
        "--cookie",
        action="store",
        dest="cookie",
        help="""Contents of _otwarchive_session cookie. Required (if
--use-browser-cookie is not set).""",
    )

    arg_parser.add_argument(
        "--use-browser-cookie",
        action="store_true",
        dest="use_browser_cookie",
        help="""Get the _otwarchive_session cookie from your browser instead of
passing it in with the -c option.""",
    )

    arg_parser.add_argument(
        "-s",
        "--sources",
        action="store",
        dest="sources",
        type=comma_separated_list,
        default=DEFAULT_SOURCES,
        help=f"""A comma-separated list of sources to get AO3 urls from.

Valid sources: {", ".join(VALID_INPUT_SOURCES)}

If using 'file', --input is required.
If using 'usernames' --usernames is required.
If using 'series', --series is required.
If using 'collections', --collections is required.
If using 'imap', the following options are required:
    --email-server
    --email-user
    --email-password
    --email-folder

Default: {DEFAULT_SOURCES}""",
    )

    arg_parser.add_argument(
        "-m",
        "--max-count",
        action="store",
        dest="max_count",
        type=int,
        default=None,
        help="""Maximum number of fics to get from AO3. Default: no limit.""",
    )

    arg_parser.add_argument(
        "--usernames",
        action="store",
        dest="usernames",
        type=comma_separated_list,
        default=[],
        help="""One or more usernames to download all works from, comma separated.""",
    )

    arg_parser.add_argument(
        "--series",
        action="store",
        dest="series",
        type=comma_separated_list,
        default=[],
        help="""One or more series to download all works from.""",
    )

    arg_parser.add_argument(
        "--collections",
        action="store",
        dest="collections",
        type=comma_separated_list,
        default=[],
        help="""One or more collections to download all works from.""",
    )

    arg_parser.add_argument(
        "-S",
        "--since",
        action="store",
        dest="since",
        help="""DD.MM.YYYY. The date since which fics should be downloaded (date
bookmarked or updated for bookmarks, date last visited for marked-for-later).
Using this with --sources=work_subscriptions is slow!
When getting urls from an email account with --sources=imap, this option is not
respected: the script will check all unread emails in the specified folder for fic urls,
no matter what date they have.""",
    )

    arg_parser.add_argument(
        "-L",
        "--since-last-update",
        action="store_true",
        dest="since_last_update",
        help="""Only fetch work ids from AO3 for works that have been changed since the
last update, as saved in the last_update_file. For bookmarked works, this fetches works
that have been bookmarked or updated since the last update. For marked-for-later works,
it fetches works that have been marked-for-later since the last update. For works from
subscriptions, it fetches works that have been posted or updated since the last update.
Lists of work urls (from the input file or from stdin) will be handled without checking
any dates. This option overrides --since.""",
    )

    arg_parser.add_argument(
        "-e",
        "--expand-series",
        action="store_true",
        dest="expand_series",
        help="Whether to get all works from a bookmarked series.",
    )

    arg_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        dest="force",
        help="""Whether to force downloads of stories even when they have the same
number of chapters locally as online.""",
    )

    arg_parser.add_argument(
        "-i",
        "--input",
        action="store",
        dest="input",
        default="fanfiction.txt",
        help="""Error file. Any urls that fail will be output here, and file will be
read to find any urls that failed previously. The file is overwitten every time the
program is run. Default: fanfiction.txt.""",
    )

    arg_parser.add_argument(
        "-l",
        "--library",
        action="store",
        dest="library",
        help="""Calibre library db location. If none is passed, then this merely
downloads stories into the current directory as epub files.
Examples: \"/home/myuser/Calibre Library\", \"http://localhost:8080/#calibre-library\"""",
    )

    arg_parser.add_argument(
        "--calibre-user",
        action="store",
        dest="calibre_user",
        help="""The user for your Calibre library. Only needed if the library is running
on a calibre-server and requires user/password to access it.""",
    )

    arg_parser.add_argument(
        "--calibre-password",
        action="store",
        dest="calibre_password",
        help="""The password for your Calibre library. Only needed if the library is
running on a calibre-server and requires user/password to access it.""",
    )

    arg_parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="""Dry run: only fetch bookmark links from AO3, don't download works or
add them to Calibre""",
    )

    arg_parser.add_argument(
        "-C",
        "--config",
        action="store",
        dest="config",
        help="""Config file (.ini). Commandline options overrule config file.
Do not put any quotation marks in the options.""",
    )

    arg_parser.add_argument(
        "-F",
        "--fanficfare-config",
        action="store",
        dest="fanficfare_config",
        help="Config file for fanficfare.",
    )

    arg_parser.add_argument(
        "--email-server",
        action="store",
        dest="email_server",
        default=None,
        help="""An IMAP email server. Needed when using --source imap.

Example if using Gmail: imap.gmail.com""",
    )

    arg_parser.add_argument(
        "--email-user",
        action="store",
        dest="email_user",
        default=None,
        help="""An email user. Needed when using --source imap.

Example if using Gmail: myuser, not myuser@gmail.com

Consider using a dedicated email account for getting fic updates, rather than your usual
account, for improved security.""",
    )

    arg_parser.add_argument(
        "--email-password",
        action="store",
        dest="email_password",
        default=None,
        help="""The password for an email account. Needed when using --source imap.

If you are using Gmail, consider using an app password instead of your usual email
password (https://support.google.com/accounts/answer/185833).""",
    )

    arg_parser.add_argument(
        "--email-folder",
        action="store",
        dest="email_folder",
        default=None,
        help="""The folder of an email account to check for fic urls. Needed when using
--source imap.

In Gmail, this is called a label, not a folder. Examples: INBOX, \"My AO3 Label\"""",
    )

    arg_parser.add_argument(
        "--email-leave-unread",
        action="store_true",
        dest="email_leave_unread",
        help="""When getting urls from an email account (with --source imap), don't mark
emails that contained fic urls as read.

The default behaviour is to mark emails as read after finding valid fic urls in them.
Only unread emails are checked for fic urls, and they are only marked as read if valid
fic urls are found in them. If you set this option, emails that contain fic urls will be
left unread and will be checked again the next time this command is run.""",
    )

    arg_parser.add_argument(
        "-U",
        "--last-update-file",
        action="store",
        dest="last_update_file",
        default=DEFAULT_LAST_UPDATE_FILE,
        help=f"""Json file storing dates of last successful update from various sources.
Example file content: {{"later": "01.01.2021", "bookmarks": "02.01.2021"}}.
Will be created if it doesn't exist. Default: '{DEFAULT_LAST_UPDATE_FILE}'.""",
    )

    arg_parser.add_argument(
        "-M",
        "--mirror",
        action="store",
        dest="mirror",
        default=AO3_DEFAULT_URL,
        help=f"""The AO3 mirror site to use, if any. This can be useful when the
official AO3 site is having problems (e.g. Cloudflare errors).

WARNING: Passing your username/password/cookie into an unofficial AO3 mirror is a
security risk!!

If using this option, use an official mirror such as
- https://archive.transformativeworks.org/
- https://archiveofourown.gay

Default: '{AO3_DEFAULT_URL}'.""",
    )

    arg_parser.add_argument(
        "-a",
        "--analysis-dir",
        action="store",
        dest="analysis_dir",
        default="analysis",
        help="""Directory to save output of analysis in. Will be created if it doesn't
exist. Default: analysis/""",
    )

    arg_parser.add_argument(
        "--analysis-type",
        action="store",
        dest="analysis_type",
        type=comma_separated_list,
        default=ANALYSIS_TYPES,
        help=f"""Which source(s) should be analysed to see if all works are in Calibre?

Valid analysis types: {", ".join(ANALYSIS_TYPES)}
Default: all.""",
    )

    arg_parser.add_argument(
        "--fix",
        action="store_true",
        dest="fix",
        default=False,
        help="""If missing works are discovered during analysis, download them.""",
    )

    # First, parse the args from the CLI.
    cli_args = arg_parser.parse_args()

    if cli_args.config:
        # Add the cli arguments to the config-file arguments, at the end so they
        # override them. We don't want to add the argv[0] (the script filename) or the
        # command to the list.
        total_args = get_config_file_arguments(cli_args) + [
            a for a in sys.argv[1:] if a != cli_args.command
        ]
        parsed_args = arg_parser.parse_args(total_args)
    else:
        parsed_args = cli_args

    # Validate options and set default values
    validate_user(parsed_args)
    validate_cookie(parsed_args)
    validate_sources(parsed_args)
    validate_since(parsed_args)
    validate_analysis_type(parsed_args)

    return parsed_args.command, parsed_args


def get_config_file_arguments(cli_args):
    """If we have a config file, get the options from there, and then parse them
    using the arg_parser. This ensures values are converted into the right types.
    """
    config_parser = ConfigParser(allow_no_value=True)
    config_parser.read(cli_args.config)
    config_file_args = [cli_args.command]
    for sect in config_parser.sections():
        for opt in config_parser.options(sect):
            value = config_parser.get(sect, opt).strip()
            if value == "":
                # Ignore config options that don't have values in config.ini.
                continue

            try:
                # Boolean arguments are all defined using "store_true", so when we
                # pass them into the arg_parser, they don't take a value
                # afterwards. If a value can be got from config.ini as a
                # bool and it's True, we only need to add the argument name to
                # config_file_args. If it's False, we don't want to add it
                # at all, because that's the default for our boolean arguments.
                if config_parser.getboolean(sect, opt):
                    config_file_args.append("--" + opt)
            except ValueError:
                # If we got an error trying to get the value as a bool, then we
                # need to add both the argument and its value to config_file_args.
                config_file_args.append("--" + opt)
                config_file_args.append(value)

    return config_file_args
