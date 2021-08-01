# encoding: utf-8

import re
from subprocess import PIPE, STDOUT, check_output
from tempfile import mkdtemp
from shutil import rmtree
from ebooklib import epub
from os import listdir
from os.path import isfile, join

# Get ids of all ao3 works from Calibre, save as ao3books.csv
# For each id, export the book as epub
# Use ebooklib to load the book, get the title_page and load the body text
# Use beautifulsoup to get the rating and the wordcount
# Add the rating tag (fanfic.rating.XXX) and wordcount (in custom column words) to the book
path = '--with-library "/home/rae/Calibre Library"'
word_count_pattern = re.compile("<b>Words:</b> ([0-9,]*)<br/>")
rating_pattern = re.compile("<b>Rating:</b> ([A-z ]*)<br/>")


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


def get_existing_tag_string(story_id):
    metadata = check_output(
        "calibredb show_metadata {} {}".format(path, story_id),
        shell=True,
        stdin=PIPE,
        stderr=STDOUT,
    )
    metadata = metadata.split(b"\n")
    existing_tag_string = ""
    for line in metadata:
        line = line.decode("utf-8")
        if line.startswith("Tags"):
            tags = line[len("Tags                : ") :].split(", ")
            for tag in tags:
                existing_tag_string += '"{}",'.format(tag)
            return existing_tag_string


if __name__ == "__main__":
    with open("ao3books.csv", "r") as f:
        ids = f.readlines()

    for story_id in ids:
        # Chop off a ZWNBSP at the start and the \n at the end
        story_id = story_id[: len(story_id) - 1].replace("﻿", "")
        print(story_id)
        loc = mkdtemp()
        check_output(
            'calibredb export --dont-save-cover --dont-write-opf --single-dir --to-dir "{}" {} {}'.format(
                loc, path, story_id
            ),
            shell=True,
            stdin=PIPE,
            stderr=STDOUT,
        )
        story_file = get_files(loc, ".epub", True)[0]
        book = epub.read_epub(story_file)
        title_page = book.get_item_with_id("title_page")
        html = str(title_page.get_body_content())

        m2 = word_count_pattern.search(html)
        if m2:
            word_count = m2.group(1)
            word_count = word_count.replace(",", "")
            check_output(
                "calibredb set_custom {} words {} {}".format(
                    path, story_id, word_count
                ),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )
        else:
            print("No word count found!")

        m1 = rating_pattern.search(html)
        if m1:
            existing_tag_string = get_existing_tag_string(story_id)
            rating = m1.group(1)
            tag_string = existing_tag_string + '"fanfic.rating.' + rating + '"'

            command = "calibredb set_metadata {} --field tags:{} {}".format(
                path, tag_string, story_id
            )
            result = check_output(
                "calibredb set_metadata {} --field tags:{} {}".format(
                    path, tag_string, story_id
                ),
                shell=True,
                stderr=STDOUT,
                stdin=PIPE,
            )

            print(result.decode("utf-8"))
        else:
            print("No rating found!")

        rmtree(loc)
