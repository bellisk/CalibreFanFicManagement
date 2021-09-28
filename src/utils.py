# encoding: utf-8
import logging
from configparser import ConfigParser
from optparse import OptionParser
from os import listdir, utime
from os.path import isfile, join
from time import localtime, strftime

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
        col = Bcolors.HEADER
        if color == "BLUE":
            col = Bcolors.OKBLUE
        elif color == "GREEN":
            col = Bcolors.OKGREEN
        elif color == "WARNING":
            col = Bcolors.WARNING
        elif color == "FAIL":
            col = Bcolors.FAIL
        elif color == "BOLD":
            col = Bcolors.BOLD
        elif color == "UNDERLINE":
            col = Bcolors.UNDERLINE
        line = "{}{}{}: \t {}{}{}".format(
            Bcolors.BOLD,
            strftime("%m/%d/%Y %H:%M:%S", localtime()),
            Bcolors.ENDC,
            col,
            msg,
            Bcolors.ENDC,
        )
    else:
        line = "{}{}{}: \t {}".format(
            Bcolors.BOLD, strftime("%m/%d/%Y %H:%M:%S", localtime()), Bcolors.ENDC, msg
        )
    if output:
        print(line)
        return ""
    else:
        return line + "\n"


def touch(fname, times=None):
    with open(fname, "a"):
        utime(fname, times)


def get_files(mypath, filetype=None, fullpath=False):
    ans = []
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


def set_up_options():
    usage = """usage: python %prog [command] [flags]
    
Commands available:
    
download    Download fics from AO3 and save to Calibre library
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
        help="Contents of _otwarchive_session cookie. Required.",
    )

    option_parser.add_option(
        "-s",
        "--source",
        action="store",
        dest="source",
        help="""Comma-separated.
'file': the file specified in --input.
'bookmarks': user's bookmarks. 'later': works marked for later.
'work_subscriptions': all works subscribed to. Using this with --since or
--since-last-update is slow!
'series_subscriptions': all works from all series subscribed to.
'user_subscriptions': all works from all users subscribed to.
'all_subscriptions': all works from all works, series and users subscribed to.
'stdin': read AO3 urls from stdin.
Default: 'file,bookmarks,later'.""",
    )

    option_parser.add_option(
        "-m",
        "--max-count",
        action="store",
        dest="max_count",
        help="""Maximum number of fics to get from AO3. Enter 'none' (or any string) to
get all bookmarks.""",
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
        help="Whether to get all works from a bookmarked series.",
    )

    option_parser.add_option(
        "-f",
        "--force",
        action="store_true",
        dest="force",
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
        help="Dry run: only fetch bookmark links from AO3, don't add them to calibre",
    )

    option_parser.add_option(
        "-C",
        "--config",
        action="store",
        dest="config",
        help="""Config file for inputs. Blank config file is provided. No default.
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
        help="""Include this if you want all the output to be saved and posted live.
Useful when multithreading.""",
    )

    option_parser.add_option(
        "-U",
        "--last-update-file",
        action="store",
        dest="last_update_file",
        help="""Json file storing dates of last successful update from various sources.
Example: {"later": "01.01.2021", "bookmarks": "02.01.2021"}.
Will be created if it doesn't exist. Default: 'last_update.json'.""",
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

        options.user = updater(config.get("login", "user").strip(), options.user)
        options.cookie = updater(config.get("login", "cookie").strip(), options.cookie)
        options.max_count = updater(
            config.get("import", "max_count"), options.max_count
        )
        try:
            options.max_count = int(options.max_count)
        except ValueError:
            options.max_count = None

        options.expand_series = updater(
            config.getboolean("import", "expand_series"), options.expand_series
        )
        options.force = updater(config.getboolean("import", "force"), options.force)
        options.dry_run = updater(
            config.getboolean("import", "dry_run"), options.dry_run
        )
        options.source = updater(config.get("import", "source").strip(), options.source)
        options.source = options.source.split(",")
        options.since = updater(config.get("import", "since").strip(), options.since)
        options.since_last_update = updater(
            config.getboolean("import", "since_last_update"),
            options.since_last_update,
        )

        options.library = updater(
            config.get("locations", "library").strip(), options.library
        )
        options.input = updater(config.get("locations", "input").strip(), options.input)
        options.fanficfare_config = updater(
            config.get("locations", "fanficfare_config").strip(),
            options.fanficfare_config,
        )
        options.last_update_file = updater(
            config.get("locations", "last_update_file").strip(),
            options.last_update_file,
        )

        options.live = updater(config.getboolean("output", "live"), options.live)

    return command, options
