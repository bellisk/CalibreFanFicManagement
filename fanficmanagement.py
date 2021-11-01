#! /usr/bin/env python
# encoding: utf-8

import locale
from src.analyse import analyse
from src.download import download
from src.utils import set_up_options

if __name__ == "__main__":
    # The locale for AO3, for converting formatted numbers.
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    command, options = set_up_options()
    permitted_commands = {"download": download, "analyse": analyse}

    eval(command + "(options)", permitted_commands, {"options": options})
