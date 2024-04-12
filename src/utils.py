# encoding: utf-8
import logging
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
        line = "{}{}{}: \t {}{}{}".format(
            Bcolors.BOLD,
            strftime("%m/%d/%Y %H:%M:%S", localtime()),
            Bcolors.ENDC,
            color,
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
