#! /usr/bin/env python
# encoding: utf-8

import locale
import sys

from src.analyse import analyse
from src.download import download
from src.options import set_up_options

if __name__ == "__main__":
    # The locale for AO3, for converting formatted numbers.
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    try:
        command, options = set_up_options()
    except ValueError as e:
        sys.exit(e)

    permitted_commands = {"download": download, "analyse": analyse}

    eval(command + "(options)", permitted_commands, {"options": options})
