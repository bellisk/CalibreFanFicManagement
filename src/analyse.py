# encoding: utf-8
from csv import DictWriter
from datetime import datetime
from os import getcwd, mkdir
from os.path import isdir, join

from .ao3_utils import (
    get_ao3_subscribed_series_work_counts,
    get_ao3_subscribed_users_work_counts,
)
from .calibre_utils import get_author_works_count, get_series_works_count
from .utils import log

ANALYSIS_TYPES = ["user_subscriptions", "series_subscriptions"]

USER_SUBS_WORK_NUMBERS = {
    "annular_eye": 24,
    "AnotherSpaceWitch": 31,
    "any_open_eye": 30,
    "aphilologicalbatman": 64,
    "Ariaste": 24,
    "AstraUne": 2,
    "astronicht": 35,
    "babylxxrry": 143,
    "Betty": 75,
    "bloodletter": 23,
    "bottlecapmermaid": 21,
    "brawlite": 116,
    "bu_ding_talk": 8,
    "bumbledees": 6,
    "Buried_in_Roses": 13,
    "Burnadette_dpdl": 53,
    "cartesiandaemon": 9,
    "deadbeatrefrain": 28,
    "Dionysus18": 8,
    "dlemur": 8,
    "dorothy_notgale": 52,
    "DRMacIver": 12,
    "DumplingWhisperer": 8,
    "el_em_en_oh_pee": 98,
    "Fioreail": 36,
    "fiveleavesleft": 1,
    "Forestofglory": 15,
    "frostferox": 52,
    "gloriousmonsters": 48,
    "grimdarkfandango": 26,
    "hawkshadow": 61,
    "hisevilforest": 13,
    "hw_campbell_jr": 10,
    "idfic_palace": 7,
    "ilgaksu": 139,
    "introductory": 43,
    "iodhadh": 46,
    "Iseult_Variante": 12,
    "isozyme": 83,
    "jeweledichneumon": 26,
    "kitschlet": 42,
    "klconley85": 2,
    "la_dissonance": 82,
    "LesbianlazerOwl": 15,
    "letsgogetlost": 36,
    "Lirelyn": 28,
    "Lise": 519,
    "lithosphere808": 14,
    "lmeden": 158,
    "Lunarwriter75": 109,
    "Moirail": 53,
    "mongrelmind": 22,
    "monstersinthecosmos": 40,
    "MooseFeels": 77,
    "names_for_dusk": 22,
    "natcat5": 82,
    "nenyanaryavilya": 24,
    "neurogenicshock": 3,
    "newredshoes": 87,
    "noctiphany": 375,
    "not_yibo": 18,
    "OchreHeart": 4,
    "onlysayitonce": 4,
    "orange_crushed": 134,
    "Pettecal72": 16,
    "plonk": 16,
    "quigonejinn": 166,
    "real_ghost": 22,
    "Rebness": 41,
    "rheawrites": 24,
    "ritualist": 62,
    "roquen": 31,
    "rowanburies": 25,
    "Rustex": 9,
    "rynleaf": 73,
    "saturnalyia": 60,
    "Sectionladvivi": 81,
    "shallots": 12,
    "short_tandem_repeats": 10,
    "singeli": 7,
    "spitandvinegar": 10,
    "SputnikCentury": 26,
    "SunBlueSun": 3,
    "tellingetienne": 48,
    "The_Archangel_of_Zeref": 23,
    "TheDameJudiWench": 43,
    "theherocomplex": 94,
    "tiniestawoo": 185,
    "tofsla": 191,
    "tucuxi": 83,
    "tuhreesha": 5,
    "twigofwillow": 27,
    "tyleet": 145,
    "unsee": 4,
    "veilchenjaeger": 11,
    "Vorvayne": 33,
    "welcome_equivocator": 39,
    "westiec": 91,
    "WhenasInSilks": 47,
    "williamshooketh": 11,
    "Woehubbub": 13,
    "x_los": 165,
    "yesterdaychild": 55,
    "yicityslut": 14,
    "Zarkonnen": 4,
    "Zeebie": 33,
    "zippkat": 21,
}
CALIBRE_AUTHOR_WORKS_NUMBERS = {
    "annular_eye": 25,
    "AnotherSpaceWitch": 29,
    "any_open_eye": 4,
    "aphilologicalbatman": 64,
    "Ariaste": 24,
    "AstraUne": 2,
    "astronicht": 35,
    "babylxxrry": 143,
    "Betty": 75,
    "bloodletter": 23,
    "bottlecapmermaid": 21,
    "brawlite": 116,
    "bu_ding_talk": 8,
    "bumbledees": 6,
    "Buried_in_Roses": 13,
    "Burnadette_dpdl": 53,
    "cartesiandaemon": 9,
    "deadbeatrefrain": 29,
    "Dionysus18": 8,
    "dlemur": 8,
    "dorothy_notgale": 52,
    "DRMacIver": 12,
    "DumplingWhisperer": 8,
    "el_em_en_oh_pee": 98,
    "Fioreail": 12,
    "fiveleavesleft": 1,
    "Forestofglory": 15,
    "frostferox": 51,
    "gloriousmonsters": 49,
    "grimdarkfandango": 26,
    "hawkshadow": 61,
    "hisevilforest": 14,
    "hw_campbell_jr": 10,
    "idfic_palace": 8,
    "ilgaksu": 137,
    "introductory": 43,
    "iodhadh": 45,
    "Iseult_Variante": 12,
    "isozyme": 82,
    "jeweledichneumon": 6,
    "kitschlet": 42,
    "klconley85": 1,
    "la_dissonance": 82,
    "LesbianlazerOwl": 15,
    "letsgogetlost": 36,
    "Lirelyn": 28,
    "Lise": 520,
    "lithosphere808": 14,
    "lmeden": 157,
    "Lunarwriter75": 106,
    "Moirail": 52,
    "mongrelmind": 22,
    "monstersinthecosmos": 40,
    "MooseFeels": 72,
    "names_for_dusk": 22,
    "natcat5": 82,
    "nenyanaryavilya": 25,
    "neurogenicshock": 3,
    "newredshoes": 87,
    "noctiphany": 375,
    "not_yibo": 18,
    "OchreHeart": 4,
    "onlysayitonce": 2,
    "orange_crushed": 10,
    "Pettecal72": 16,
    "plonk": 16,
    "quigonejinn": 166,
    "real_ghost": 23,
    "Rebness": 41,
    "rheawrites": 24,
    "ritualist": 3,
    "roquen": 30,
    "rowanburies": 25,
    "Rustex": 9,
    "rynleaf": 74,
    "saturnalyia": 60,
    "Sectionladvivi": 85,
    "shallots": 12,
    "short_tandem_repeats": 10,
    "singeli": 7,
    "spitandvinegar": 10,
    "SputnikCentury": 27,
    "SunBlueSun": 2,
    "tellingetienne": 47,
    "The_Archangel_of_Zeref": 6,
    "TheDameJudiWench": 43,
    "theherocomplex": 94,
    "tiniestawoo": 180,
    "tofsla": 190,
    "tucuxi": 83,
    "tuhreesha": 5,
    "twigofwillow": 27,
    "tyleet": 145,
    "unsee": 4,
    "veilchenjaeger": 11,
    "Vorvayne": 33,
    "welcome_equivocator": 39,
    "westiec": 90,
    "WhenasInSilks": 7,
    "williamshooketh": 2,
    "Woehubbub": 7,
    "x_los": 165,
    "yesterdaychild": 54,
    "yicityslut": 14,
    "Zarkonnen": 4,
    "Zeebie": 32,
    "zippkat": 20,
}


def _compare_user_subscriptions(username, cookie, path, output_file):
    """Compares the number of fics downloaded for each user subscribed to with the
    number posted to AO3.
    :return:
    """
    # ao3_user_work_counts = get_ao3_subscribed_users_work_counts(username, cookie)
    ao3_user_work_counts = USER_SUBS_WORK_NUMBERS
    # calibre_user_work_counts = {
    #     u: get_author_works_count(u, path) for u in ao3_user_work_counts.keys()
    # }
    calibre_user_work_counts = CALIBRE_AUTHOR_WORKS_NUMBERS

    with open(output_file, "a") as f:
        writer = DictWriter(f, ["author", "works on AO3", "works on Calibre"])
        writer.writeheader()
        for u in ao3_user_work_counts:
            line = {
                "author": u,
                "works on AO3": ao3_user_work_counts[u],
                "works on Calibre": calibre_user_work_counts[u],
            }
            writer.writerow(line)


def _compare_series_subscriptions(username, cookie, path, output_file):
    """Compares the number of fics downloaded for each series subscribed to with the
    number posted to AO3.
    :return:
    """
    ao3_series_work_counts = get_ao3_subscribed_series_work_counts(username, cookie)
    calibre_series_work_counts = {
        u: get_series_works_count(u, path) for u in ao3_series_work_counts.keys()
    }

    with open(output_file, "a") as f:
        writer = DictWriter(f, ["series", "works on AO3", "works on Calibre"])
        writer.writeheader()
        for u in ao3_series_work_counts:
            line = {
                "series": u,
                "works on AO3": ao3_series_work_counts[u],
                "works on Calibre": calibre_series_work_counts[u],
            }
            writer.writerow(line)


def analyse(options):
    if not (options.user and options.cookie):
        log("User and Cookie are required for downloading from AO3", "FAIL")
        return

    path = options.library
    if path:
        path = '--with-library "{}"'.format(path)
        # todo: abstract checking that the library is OK from download and do that here too

    analysis_dir = (
        options.analysis_dir if options.analysis_dir else join(getcwd(), "analysis")
    )

    if not isdir(analysis_dir):
        mkdir(analysis_dir)

    for type in ANALYSIS_TYPES:
        filename = "{}_{}.csv".format(
            type, datetime.strftime(datetime.now(), "%Y%m%d_%H%M%S")
        )
        output_file = join(analysis_dir, filename)

        if type == "user_subscriptions":
            _compare_user_subscriptions(options.user, options.cookie, path, output_file)
        elif type == "series_subscriptions":
            _compare_series_subscriptions(
                options.user, options.cookie, path, output_file
            )
