# encoding: utf-8
import json
from subprocess import PIPE, STDOUT, check_output

path = '--with-library "/home/rae/Calibre Fanfic Library"'


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
    ids = check_output(
        "calibredb list {} --for-machine --fields=id".format(path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    ids = json.loads(ids)
    print(ids)

    for story_id in ids:
        story_id = story_id["id"]
        if int(story_id) <= 12875:
            continue
        print(story_id)
        existing_tag_string = get_existing_tag_string(story_id)
        new_tag_string = existing_tag_string.replace("fanfic.", "")

        result = check_output(
            "calibredb set_metadata {} --field tags:{} {}".format(
                path, new_tag_string, story_id
            ),
            shell=True,
            stderr=STDOUT,
            stdin=PIPE,
        )
        print(result)
