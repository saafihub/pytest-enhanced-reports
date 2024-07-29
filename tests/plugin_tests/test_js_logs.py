import json
from os import getcwd, path, listdir
from subprocess import Popen
import pytest
import logging
from tests.util import util
from enhanced_reports.config import EnhancedReportOperationFrequency
import re

logger = logging.getLogger(__name__)

TIMEOUT = 120  # 120 seconds timeout for running normal tests

RUN_NORMAL_TESTS = "pytest -vv --disable-warnings \
--headless=True \
--alluredir='{0}' \
--report_browser_console_log_capture='{1}' \
normal_tests"


@pytest.mark.parametrize(
    "frequency", [e.value for e in EnhancedReportOperationFrequency]
)
def test_js_logs(frequency):
    logger.info("Clean up folder ")
    util.clean_up_report_directories(frequency)

    logger.info(f"Start running NORMAL tests: js_log_frequency={frequency}...")
    test_process = Popen(
        RUN_NORMAL_TESTS.format(frequency, frequency), shell=True
    )
    test_process.wait(TIMEOUT)

    logger.info(f"Start running PLUGIN tests: js_log_frequency={frequency}...")
    verify_js_logs(frequency)


def verify_js_logs(js_log_frequency):
    actual_report_dir = js_log_frequency
    curr_dir = getcwd()
    if js_log_frequency == "never":
        actual_txt_files = util.count_file_match(".txt", actual_report_dir)
        assert (
            actual_txt_files == 0
        ), "there are some txt files inside the report folder while js log frequency = never"
    elif js_log_frequency in ["always", "end_of_each_test"]:
        verify_js_logs_with_params(
            curr_dir, actual_report_dir, "Run Test for browser's outputs"
        )
    elif js_log_frequency in ["failed_test_only", "each_ui_operation"]:
        verify_js_logs_with_params(
            curr_dir, actual_report_dir, "Failed test only"
        )


def verify_js_logs_with_params(current_dir, frequency, scenario):
    actual_file = util.find_newest_report(scenario, frequency)

    # read report file (to get all js log files in ordered)
    with open(actual_file) as f:
        output = json.load(f)

    if not output:
        assert False, "Test was not run successfully or file not found!"

    actual_files = []
    actual_report_dir = f"{current_dir}/{frequency}/"
    # collect js_logs in steps (output > steps > attachments)
    for step in output["steps"]:
        actual_files.extend(
            util.collect_files_from_report(
                step, "Logs from browser console", actual_report_dir
            )
        )
    # collect js_logs in attachment (output > attachments)
    actual_files.extend(
        util.collect_files_from_report(
            output, "Logs from browser console", actual_report_dir
        )
    )

    data_path_prefix = f"{current_dir}/data/js_logs/{frequency}"
    expected_files = [
        path.join(data_path_prefix, f)
        for f in listdir(data_path_prefix)
        if path.isfile(path.join(data_path_prefix, f))
    ]
    expected_files = sorted(expected_files, key=lambda x: path.basename(x))

    # compare number of js files
    assert len(actual_files) == len(
        expected_files
    ), "number of js output files are different"

    # compare file content
    for i in range(len(expected_files)):
        with open(actual_files[i]) as act:
            actual_file_content = act.readlines()
        with open(expected_files[i]) as exp:
            expected_file_content = exp.readlines()

        assert len(actual_file_content) == len(
            expected_file_content
        ), f"2 files are different {actual_file_content} vs {expected_file_content}"
        for j in range(len(actual_file_content)):
            assert compare_js_logs_without_timespan(
                actual_file_content[j], expected_file_content[j]
            ), f"js logs are different {actual_file_content[j]} vs {expected_file_content[j]}"


def compare_js_logs_without_timespan(actual, expect):
    if actual.strip() == expect.strip():
        return True
    # remove datetime and timestamp
    regex_str = r"^[\d-]*\s[\d:]*"
    actual = re.sub(regex_str, "", actual)
    expect = re.sub(regex_str, "", expect)
    return actual == expect
