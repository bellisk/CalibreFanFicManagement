# encoding: utf-8
import csv
import json
from subprocess import PIPE, STDOUT, check_output
from sys import argv

PATH = '--with-library "/home/rae/Calibre Fanfic Library"'
TAG_TYPES = [
    "ao3categories",
    "characters",
    "fandoms",
    "freeformtags",
    "rating",
    "ships",
    "status",
    "warnings",
]


def check_or_create_extra_tag_type_columns(path):
    res = check_output(
        "calibredb custom_columns {}".format(path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    # Get rid of the number after each column name, e.g. "columnname (1)"
    columns = [c.split(" ")[0] for c in res.decode("utf-8").split("\n")]
    if set(columns).intersection(TAG_TYPES) == set(TAG_TYPES):
        print("All AO3 tag types are columns in Calibre library")
        return
    print("Adding AO3 tag types as columns in Calibre library")
    for tag in TAG_TYPES:
        check_output(
            "calibredb add_custom_column {} {} {} text --is-multiple".format(
                path, tag, tag
            ),
            shell=True,
            stderr=STDOUT,
            stdin=PIPE,
        )


def check_tag_data(tag_type):
    check_output(
        "calibredb list_categories -r tags --csv {} > all_tags.csv".format(path),
        shell=True,
        stdin=PIPE,
        stderr=STDOUT,
    )
    with open("all_tags.csv", "r") as f:
        reader = csv.DictReader(f)
        tags_of_type = [
            row["tag_name"]
            for row in reader
            if row.get("tag_name")
            and row.get("tag_name", "").startswith(tag_type + ".")
        ]

    print(f"Got {len(tags_of_type)} tags of the type {tag_type}")


def get_all_fic_data():
    res = check_output(
        "calibredb list {} --for-machine".format(path),
        shell=True,
        stdin=PIPE,
        stderr=STDOUT,
    )
    return json.loads(res.decode("utf-8")[: -len("Initialized urlfixer\n")])


def get_existing_tags(story_id):
    metadata = check_output(
        "calibredb show_metadata {} {}".format(path, story_id),
        shell=True,
        stdin=PIPE,
        stderr=STDOUT,
    )
    metadata = metadata.split(b"\n")
    for line in metadata:
        line = line.decode("utf-8")
        if line.startswith("Tags"):
            tags = line[len("Tags                : ") :].split(", ")
            return tags


def fix_tags_for_fic(fic_id, path):
    update_command = f"calibredb set_metadata {str(fic_id)} {path} --field tags:'' "
    existing_tags = get_existing_tags(fic_id)
    if not existing_tags:
        return
    for tag_type in TAG_TYPES:
        tags = [
            f'"{tag.split(".")[1]}"'
            for tag in existing_tags
            if tag.startswith(tag_type)
        ]
        update_command += f"--field=#{tag_type}:{','.join(tags)} "
    # print(update_command)

    res = check_output(
        update_command,
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    # print(res)


if __name__ == "__main__":
    path = PATH
    if len(argv) > 1:
        path = argv[1]

    check_or_create_extra_tag_type_columns(path)
    for tag_type in TAG_TYPES:
        check_tag_data(tag_type)

    fics = get_all_fic_data()
    print(f"Fixing tags for {len(fics)} fics")

    n = 0
    for fic in fics:
        print(f"Fixing tags for fic {fic['id']} {fic['title']}")
        fix_tags_for_fic(fic["id"], path)
        n += 1
        if n % 100 == 0:
            print(f"PROGRESS: {n}/{len(fics)}, {n * 100 / len(fics)}%")
