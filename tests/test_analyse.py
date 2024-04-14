import os.path
from unittest.mock import patch

from src import analyse, options

valid_config_path = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "fixtures", "valid_config.ini"
)


def _get_options(analysis_type):
    args = ["fanficmanagement.py", "analyse", "-C", valid_config_path, "--analysis-type", analysis_type]
    with patch("sys.argv", args):
        return options.set_up_options()


def mock_check_library(path):
    return f'--with-library "{path}"'


@patch("src.analyse.check_library_and_get_path", side_effect=mock_check_library)
def test_analyse_user_subscriptions(mock_check_library_and_get_path):
    command, namespace = _get_options(options.SOURCE_USER_SUBSCRIPTIONS)
    analyse.analyse(namespace)