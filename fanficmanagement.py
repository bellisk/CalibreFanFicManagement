# encoding: utf-8

from download import download
from utils import set_up_options

if __name__ == "__main__":
    command, options = set_up_options()
    permitted_commands = {"download": download}

    eval(command + "(options)", permitted_commands, {"options": options})