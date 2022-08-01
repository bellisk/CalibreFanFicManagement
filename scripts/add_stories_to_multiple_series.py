from subprocess import PIPE, STDOUT, check_output


# The AO3 metadata that we get from FanficFare includes these series keys as well as
# "series". Since "series" is a default Calibre field, we can ignore it here.
AO3_SERIES_KEYS = ["series00", "series01", "series02", "series03"]
PATH = '--with-library "/home/rae/Calibre Fanfic Library"'


def check_or_create_extra_series_columns(path):
    res = check_output(
        "calibredb custom_columns {}".format(path),
        shell=True,
        stderr=STDOUT,
        stdin=PIPE,
    )
    # Get rid of the number after each column name, e.g. "columnname (1)"
    columns = [c.split(" ")[0] for c in res.decode("utf-8").split("\n")]
    print(columns)
    print(set(columns).intersection(AO3_SERIES_KEYS))
    print(set(AO3_SERIES_KEYS))
    if set(columns).intersection(AO3_SERIES_KEYS) == set(AO3_SERIES_KEYS):
        print("Custom AO3 series columns are in Calibre Library")
        return

    print("Adding custom AO3 series columns to Calibre library")
    for c in AO3_SERIES_KEYS:
        check_output(
            "calibredb add_custom_column {} {} {} series".format(path, c, c),
            shell=True,
            stderr=STDOUT,
            stdin=PIPE,
        )


if __name__ == "__main__":
    # Next: export all fics from calibre that are in a series.
    # It looks like, if a fic is in more than one series, we save it into a different series than is added to the epub front
    # page by fanficfare.
    # So, look for all fics that have more than one series according to that measure?
    # Then get the metadata from AO3, and add multiple series to the ebook metadata, and save.
    check_or_create_extra_series_columns(PATH)
