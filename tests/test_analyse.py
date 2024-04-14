import json
import os.path
import time
from random import randint
from unittest.mock import patch

from src import analyse, options

from .mock_ao3 import MockAO3

valid_config_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "fixtures", "valid_config.ini"
)


def _get_options(analysis_type):
    args = [
        "fanficmanagement.py",
        "analyse",
        "-C",
        valid_config_path,
        "--analysis-type",
        analysis_type,
    ]
    with patch("sys.argv", args):
        return options.set_up_options()


def mock_check_library(path):
    return f'--with-library "{path}"'


def mock_check_output(command, *args, **kwargs):
    print(command)
    if command.startswith("calibredb search author"):
        return "1,2,3,4,5,6,7,8,9,10"


@patch("src.calibre_utils.check_output", side_effect=mock_check_output)
@patch("src.ao3_utils.AO3")
@patch("src.analyse.check_library_and_get_path", side_effect=mock_check_library)
def test_analyse_user_subscriptions(mock_check_library_and_get_path, mock_ao3, mock_subprocess_check_output):
    mock_ao3().user.user_subscription_ids.return_value = ["user1", "user2", "user3"]

    def mock_users_works_counts(username):
        return int(username[-1]) * 10

    mock_ao3().users_works_count.side_effect = mock_users_works_counts

    command, namespace = _get_options(options.SOURCE_USER_SUBSCRIPTIONS)
    analyse.analyse(namespace)
    assert 1 == 0