# encoding: utf-8
import logging
from configparser import ConfigParser
from optparse import OptionParser
from os import listdir, utime
from os.path import isfile, join
from time import strftime, localtime

logging.getLogger("fanficfare").setLevel(logging.ERROR)


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def log(msg, color=None, output=True):
    if color:
        col = Bcolors.HEADER
        if color == 'BLUE':
            col = Bcolors.OKBLUE
        elif color == 'GREEN':
            col = Bcolors.OKGREEN
        elif color == 'WARNING':
            col = Bcolors.WARNING
        elif color == 'FAIL':
            col = Bcolors.FAIL
        elif color == 'BOLD':
            col = Bcolors.BOLD
        elif color == 'UNDERLINE':
            col = Bcolors.UNDERLINE
        line = '{}{}{}: \t {}{}{}'.format(
            Bcolors.BOLD,
            strftime(
                '%m/%d/%Y %H:%M:%S',
                localtime()),
            Bcolors.ENDC,
            col,
            msg,
            Bcolors.ENDC)
    else:
        line = '{}{}{}: \t {}'.format(
            Bcolors.BOLD,
            strftime(
                '%m/%d/%Y %H:%M:%S',
                localtime()),
            Bcolors.ENDC,
            msg)
    if output:
        print(line)
        return ""
    else:
        return line + "\n"


def touch(fname, times=None):
    with open(fname, 'a'):
        utime(fname, times)


def get_files(mypath, filetype=None, fullpath=False):
    ans = []
    if filetype:
        ans = [f for f in listdir(mypath) if isfile(
            join(mypath, f)) and f.endswith(filetype)]
    else:
        ans = [f for f in listdir(mypath) if isfile(join(mypath, f))]
    if fullpath:
        return [join(mypath, f) for f in ans]
    else:
        return ans


def set_up_options():
    option_parser = OptionParser(usage="usage: %prog [flags]")

    option_parser.add_option(
        '-u',
        '--user',
        action='store',
        dest='user',
        help='AO3 username. Required.'
    )

    option_parser.add_option(
        '-c',
        '--cookie',
        action='store',
        dest='cookie',
        help='Contents of _otwarchive_session cookie. Required.'
    )

    option_parser.add_option(
        '-m',
        '--max-count',
        action='store',
        dest='max_count',
        default=20,
        help='Maximum number of bookmarks to get from AO3. Default = 20 (one page of bookmarks). Enter \'none\' (or any string) to get all bookmarks.'
    )

    option_parser.add_option(
        '-e',
        '--expand-series',
        action='store',
        dest='expand_series',
        default=False,
        help='Whether to get all works from a bookmarked series. Default = false.'
    )

    option_parser.add_option(
        '-f',
        '--force',
        action='store',
        dest='force',
        default=False,
        help='Whether to force downloads of stories even when they have the same number of chapters locally as online.')

    option_parser.add_option(
        '-i',
        '--input',
        action='store',
        dest='input',
        default="./fanfiction.txt",
        help="Error file. Any urls that fail will be output here, and file will be read to find any urls that failed previously. If file does not exist will create. File is overwitten every time the program is run.")

    option_parser.add_option(
        '-l',
        '--library',
        action='store',
        dest='library',
        help="calibre library db location. If none is passed, then this merely scrapes the AO3 bookmarks and error file for new stories and downloads them into the current directory.")

    option_parser.add_option(
        '-d',
        '--dry-run',
        action='store',
        dest='dry_run',
        help='Dry run: only fetch bookmark links from AO3, don\'t add them to calibre'
    )

    option_parser.add_option(
        '-C',
        '--config',
        action='store',
        dest='config',
        help='Config file for inputs. Blank config file is provided. No default. If an option is present in whatever config file is passed it, the option will overwrite whatever is passed in through command line arguments unless the option is blank. Do not put any quotation marks in the options.')

    option_parser.add_option(
        '-o',
        '--output',
        action='store_true',
        dest='live',
        help='Include this if you want all the output to be saved and posted live. Useful when multithreading.')

    (options, args) = option_parser.parse_args()

    if options.config:
        touch(options.config)
        config = ConfigParser(allow_no_value=True)
        config.read(options.config)


        def updater(option, newval):
            return newval if newval != "" else option


        options.user = updater(
            options.user, config.get(
                'login', 'user').strip())
        options.cookie = updater(
            options.user, config.get(
                'login', 'cookie').strip())
        options.max_count = updater(
            options.max_count, config.get(
                'import', 'max_count'))
        try:
            options.max_count = int(options.max_count)
        except ValueError as e:
            options.max_count = None

        options.expand_series = updater(
            options.expand_series, config.getboolean(
                'import', 'expand_series'))
        options.force = updater(
            options.force, config.getboolean(
                'import', 'force'))
        options.dry_run = updater(
            options.dry_run, config.getboolean(
                'import', 'dry_run'))
        options.input = updater(
            options.input, config.get(
                'locations', 'input').strip())
        options.library = updater(
            options.library, config.get(
                'locations', 'library').strip())
        options.live = updater(
            options.live, config.getboolean(
                'output', 'live'))

    if not (options.user or options.cookie):
        raise ValueError("User or Cookie not given")

    return options