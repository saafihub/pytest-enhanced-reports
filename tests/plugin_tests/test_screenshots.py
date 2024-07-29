import cv2
import numpy as np
import json
import pytest
from os import getcwd, path, listdir
from subprocess import Popen
from tests.util import util
import logging
from enhanced_reports.config import EnhancedReportOperationFrequency

logger = logging.getLogger(__name__)

TIMEOUT = 120  # 120 seconds timeout for running normal tests

RUN_NORMAL_TESTS = "pytest -vv --disable-warnings \
--headless=True \
--alluredir='{0}' \
--report_screenshot_capture='{1}' \
normal_tests"


@pytest.mark.parametrize(
    "frequency", [e.value for e in EnhancedReportOperationFrequency]
)
def test_screenshot(frequency):
    logger.info("Clean up folder ")
    util.clean_up_report_directories(frequency)

    logger.info(
        f"Start running NORMAL tests: screenshot_frequency={frequency}..."
    )
    test_process = Popen(
        RUN_NORMAL_TESTS.format(frequency, frequency), shell=True
    )
    test_process.wait(TIMEOUT)

    logger.info(
        f"Start running PLUGIN tests: screenshot_frequency={frequency}..."
    )
    verify_screenshot(frequency)


def verify_screenshot(frequency):
    actual_report_dir = frequency
    curr_dir = getcwd()
    if frequency == "never":
        actual_files = util.count_file_match(".png", actual_report_dir)
        assert (
            actual_files == 0
        ), "there are some screenshot files inside the report folder while screenshot frequency = never"
    elif frequency in ["always", "end_of_each_test"]:
        verify_screenshot_with_params(
            curr_dir, actual_report_dir, "Run Test for browser's outputs"
        )
    elif frequency in ["failed_test_only", "each_ui_operation"]:
        verify_screenshot_with_params(
            curr_dir, actual_report_dir, "Failed test only"
        )


def verify_screenshot_with_params(current_dir, frequency, scenario):
    actual_report_file = util.find_newest_report(scenario, frequency)

    with open(actual_report_file) as f:
        output = json.load(f)

    if not output:
        assert False, "Test was not run successfully or file not found!"

    actual_files = []
    actual_report_dir = f"{current_dir}/{frequency}/"
    # collect screenshots in steps (output > steps > attachments)
    for step in output["steps"]:
        actual_files.extend(
            util.collect_files_from_report(
                step, "Screenshot", actual_report_dir
            )
        )
    # collect screenshots in attachment (output > attachments)
    actual_files.extend(
        util.collect_files_from_report(output, "Screenshot", actual_report_dir)
    )

    data_path_prefix = f"{current_dir}/data/screenshots/{frequency}"
    expected_files = [
        path.join(data_path_prefix, f)
        for f in listdir(data_path_prefix)
        if path.isfile(path.join(data_path_prefix, f))
    ]
    expected_files = sorted(expected_files, key=lambda x: path.basename(x))

    # compare number of screenshots
    assert len(actual_files) == len(
        expected_files
    ), "number of screenshots are different"

    for i in range(len(expected_files)):
        actual_image = cv2.imread(actual_files[i])

        expected_image = cv2.imread(expected_files[i])
        height, width, e = actual_image.shape

        if actual_image.shape == expected_image.shape:
            # Get the difference between the two images and returns an arrays with 0,1 and 2
            # Mean Square Error (MSE) of the pixel values of the two images.
            # Similar images will have less mean square error value.
            # Using this method, we can compare two images having the same height, width and number of channels.
            difference = cv2.subtract(actual_image, expected_image)
            err = np.sum(difference**2)
            mse = err / (height * width)
            assert (
                mse == 0.0 or mse <= 0.1
            ), f"image is different {actual_files[i]} vs {expected_files[i]} "
