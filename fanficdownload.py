# Adapted from https://github.com/MrTyton/AutomatedFanfic

from ao3 import AO3
from os import listdir, remove, rename, utime, devnull
from os.path import isfile, join
from subprocess import check_output, STDOUT, call, PIPE, CalledProcessError
import json
import logging
from optparse import OptionParser
import re
from configparser import ConfigParser
from tempfile import mkdtemp
from shutil import rmtree
from time import strftime, localtime
from errno import ENOENT

from multiprocessing import Lock, Pool

logging.getLogger("fanficfare").setLevel(logging.ERROR)


class bcolors:
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
        col = bcolors.HEADER
        if color == 'BLUE':
            col = bcolors.OKBLUE
        elif color == 'GREEN':
            col = bcolors.OKGREEN
        elif color == 'WARNING':
            col = bcolors.WARNING
        elif color == 'FAIL':
            col = bcolors.FAIL
        elif color == 'BOLD':
            col = bcolors.BOLD
        elif color == 'UNDERLINE':
            col = bcolors.UNDERLINE
        line = '{}{}{}: \t {}{}{}'.format(
            bcolors.BOLD,
            strftime(
                '%m/%d/%Y %H:%M:%S',
                localtime()),
            bcolors.ENDC,
            col,
            msg,
            bcolors.ENDC)
    else:
        line = '{}{}{}: \t {}'.format(
            bcolors.BOLD,
            strftime(
                '%m/%d/%Y %H:%M:%S',
                localtime()),
            bcolors.ENDC,
            msg)
    if output:
        print(line)
        return ""
    else:
        return line + "\n"


def touch(fname, times=None):
    with open(fname, 'a'):
        utime(fname, times)


story_name = re.compile('(.*)-.*')
series_pattern = re.compile('(.*) \[(.*)\]')

# Responses from fanficfare that mean we won't update the story
equal_chapters = re.compile('.* already contains \d* chapters.')
bad_chapters = re.compile(
    ".* doesn't contain any recognizable chapters, probably from a different source.  Not updating.")
no_url = re.compile('No story URL found in epub to update.')
too_many_requests = re.compile('Failed to read epub for update: \(HTTP Error 429: Too Many Requests\)')

# Responses from fanficfare that mean we should force-update the story
chapter_difference = re.compile(
    '.* contains \d* chapters, more than source: \d*.')
# Our tmp epub was just created, so if this is the only reason not to update,
# we should ignore it and do the update
more_chapters = re.compile(
    ".*File\(.*\.epub\) Updated\(.*\) more recently than Story\(.*\) - Skipping")


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


def check_fff_output(force, output):
    output = output.decode('utf-8')
    if not force and equal_chapters.search(output):
        raise ValueError(
            "Downloaded story already contains as many chapters as on the website.")
    if bad_chapters.search(output):
        raise ValueError(
            "Something is messed up with the site or the epub. No chapters found.")
    if no_url.search(output):
        raise ValueError("No URL in epub to update from. Fix the metadata.")
    if too_many_requests.search(output):
        raise ValueError("Too many requests for now.")


def should_force_download(force, output):
    output = output.decode('utf-8')
    return force and (chapter_difference.search(output) or more_chapters.search(output))


def get_series_options(metadata):
    series_keys = ['series', 'series00', 'series01', 'series02', 'series03']
    opts = ''
    for key in series_keys:
        if len(metadata[key]) > 0:
            m = series_pattern.match(metadata[key])
            opts += '--series="{}" --series-index={} '.format(m.group(1), m.group(2))

    return opts


def get_tags_options(metadata):
    tag_keys = [
        "ao3categories",
        'characters',
        'fandoms',
        'freeformtags',
        'ships',
        'status',
        'warnings',
    ]
    opts = '--tags='
    for key in tag_keys:
        if len(metadata[key]) > 0:
            tags = metadata[key].split(', ')
            for tag in tags:
                # Replace characters that give Calibre trouble in tags.
                tag = tag.replace('"', '\'').replace('...', '…').replace('.', '．')
                opts += '"{}",'.format('fanfic.' + key + '.' + tag)

    return opts


def downloader(args):
    url, inout_file, path, force, live = args
    loc = mkdtemp()
    output = ""
    output += log("Working with url {}".format(url), 'HEADER', live)
    story_id = None
    try:
        if path:
            try:
                lock.acquire()
                story_id = check_output(
                    'calibredb search "Identifiers:url:{}" {}'.format(
                        url, path), shell=True, stderr=STDOUT, stdin=PIPE, )
                lock.release()
            except CalledProcessError:
                # story is not in calibre
                lock.release()
                cur = url

            if story_id is not None:
                story_id = story_id.decode('utf-8')
                output += log("\tStory is in calibre with id {}".format(story_id), 'BLUE', live)
                output += log("\tExporting file", 'BLUE', live)
                output += log('calibredb export {} --dont-save-cover --dont-write-opf --single-dir --to-dir "{}" {}'.format(
                        story_id, loc, path), 'BLUE', live)
                lock.acquire()
                res = check_output(
                    'calibredb export {} --dont-save-cover --dont-write-opf --single-dir --to-dir "{}" {}'.format(
                        story_id, loc, path), shell=True, stdin=PIPE, stderr=STDOUT)
                lock.release()

                try:
                    cur = get_files(loc, ".epub", True)[0]
                    output += log(
                        '\tDownloading with fanficfare, updating file "{}"'.format(cur),
                        'GREEN',
                        live)
                except IndexError:
                    # calibre doesn't have this story in epub format.
                    # the ebook-convert and ebook-meta CLIs can't save an epub
                    # with a source url in the way fanficfare expects, so
                    # we'll download a new copy as if we didn't have it at all
                    cur = url
                    output += log(
                        '\tNo epub for story id "{}" in calibre'.format(story_id),
                        'BLUE',
                        live)

            res = check_output(
                'cp personal.ini {}/personal.ini'.format(loc),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )

            output += log('\tRunning: cd "{}" && fanficfare -j "{}"'.format(
                loc, url), 'BLUE', live)
            res = check_output('cd "{}" && fanficfare -j "{}"'.format(
                loc, url), shell=True, stderr=STDOUT, stdin=PIPE)
            metadata = json.loads(res)
            series_options = get_series_options(metadata)
            tags_options = get_tags_options(metadata)

            output += log('\tRunning: cd "{}" && fanficfare -u "{}" --update-cover'.format(
                loc, cur), 'BLUE', live)
            res = check_output('cd "{}" && fanficfare -u "{}" --update-cover'.format(
                loc, cur), shell=True, stderr=STDOUT, stdin=PIPE)
            check_fff_output(force, res)
            if should_force_download(force, res):
                output += log("\tForcing download update due to:",
                              'WARNING', live)
                if force:
                    output += log("\t\tForce option set to true", 'WARNING', live)
                else:
                    for line in res.split(b"\n"):
                        if line:
                            output += log("\t\t{}".format(str(line)), 'WARNING', live)
                res = check_output(
                    'fanficfare -u "{}" --force --update-cover'.format(
                        cur), shell=True, stderr=STDOUT, stdin=PIPE)
                check_fff_output(force, res)
            cur = get_files(loc, '.epub', True)[0]

            if story_id:
                output += log("\tRemoving {} from library".format(story_id),
                              'BLUE', live)
                try:
                    lock.acquire()
                    res = check_output(
                        'calibredb remove {} {}'.format(
                            path,
                            story_id),
                        shell=True,
                        stderr=STDOUT,
                        stdin=PIPE,
                    )
                    lock.release()
                except BaseException:
                    lock.release()
                    if not live:
                        print(output.strip())
                    raise

            output += log("\tAdding {} to library".format(cur), 'BLUE', live)
            try:
                lock.acquire()
                res = check_output(
                    'calibredb add -d {} "{}" {} {}'.format(
                        path, cur, series_options, tags_options), shell=True, stderr=STDOUT, stdin=PIPE, )
                lock.release()
            except Exception as e:
                lock.release()
                output += log(e)
                if not live:
                    print(output.strip())
                raise
            try:
                lock.acquire()
                res = check_output(
                    'calibredb search "Identifiers:url:{}" {}'.format(
                        url, path), shell=True, stderr=STDOUT, stdin=PIPE)
                lock.release()
                output += log("\tAdded {} to library with id {}".format(cur,
                                                                        res), 'GREEN', live)
            except CalledProcessError as e:
                lock.release()
                output += log(
                    "It's been added to library, but not sure what the ID is.",
                    'WARNING',
                    live)
                output += log("Added /Story-file to library with id 0", 'GREEN', live)
                output += log(e.output)
            remove(cur)
        else:
            res = check_output(
                'cd "{}" && fanficfare -u "{}" --update-cover'.format(
                    loc, url), shell=True, stderr=STDOUT, stdin=PIPE)
            check_fff_output(force, res)
            cur = get_files(loc, '.epub', True)[0]
            name = get_files(loc, '.epub', False)[0]
            rename(cur, name)
            output += log(
                "Downloaded story {} to {}".format(
                    story_name.search(name).group(1),
                    name),
                'GREEN',
                live)
        if not live:
            print(output.strip())
        rmtree(loc)
    except Exception as e:
        output += log("Exception: {}".format(e), 'FAIL', live)
        if type(e) == CalledProcessError:
            output += log(e.output.decode('utf-8'), 'FAIL', live)
        if not live:
            print(output.strip())
        try:
            rmtree(loc)
        except BaseException:
            pass
        with open(inout_file, "a") as fp:
            fp.write("{}\n".format(url))


def init(l):
    global lock
    lock = l


def main(user, cookie, max_count, expand_series, force, dry_run, inout_file, path, live):
    if path:
        path = '--with-library "{}"'.format(path)
        try:
            with open(devnull, 'w') as nullout:
                call(['calibredb'], stdout=nullout, stderr=nullout)
        except OSError as e:
            if e.errno == ENOENT:
                log("Calibredb is not installed on this system. Cannot search the calibre library or update it.",
                    'FAIL')
                return

    touch(inout_file)

    with open(inout_file, "r") as fp:
        urls = set([x.replace("\n", "") for x in fp.readlines()])

    with open(inout_file, "w") as fp:
        fp.write("")

    try:
        urls |= get_ao3_bookmark_urls(cookie, expand_series, max_count, user)
    except BaseException:
        with open(inout_file, "w") as fp:
            for cur in urls:
                fp.write("{}\n".format(cur))
        return

    if not urls:
        return
    log("URLs to parse ({}):".format(len(urls)), 'HEADER')
    for url in urls:
        log("\t{}".format(url), 'BLUE')

    if dry_run:
        log("Not adding any stories to calibre because dry-run is set to True", 'HEADER')
    else:
        l = Lock()
        p = Pool(initializer=init, initargs=(l,))
        p.map(downloader, [[url, inout_file, path, force, live] for url in urls])

    return


def get_ao3_bookmark_urls(cookie, expand_series, max_count, user):
    if max_count == 0:
        return set([])

    api = AO3()
    api.login(user, cookie)
    urls = ['https://archiveofourown.org/works/%s'
            % work_id for work_id in
            api.user.bookmarks_ids(max_count, expand_series)]
    return set(urls)


if __name__ == "__main__":
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

    main(
        options.user,
        options.cookie,
        options.max_count,
        options.expand_series,
        options.force,
        options.dry_run,
        options.input,
        options.library,
        options.live)
