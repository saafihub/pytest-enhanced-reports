import os
from enum import Enum
from typing import Mapping, Any, Union

from _pytest.config import argparsing
from _pytest.fixtures import FixtureRequest

import logging


logger = logging.getLogger(__name__)
logger.info("Loaded " + __file__)


class EnhancedReportOperationFrequency(Enum):
    ALWAYS = "always"
    EACH_UI_OPERATION = "each_ui_operation"
    END_OF_EACH_TEST = "end_of_each_test"
    FAILED_TEST_ONLY = "failed_test_only"
    NEVER = "never"


class Parameter(Enum):
    JS_LOG_FREQUENCY = "browser_console_log_capture"

    SS_FREQUENCY = "screenshot_capture"
    SS_RESIZE_PERCENT = "screenshot_resize_percent"
    SS_HEIGHT = "screenshot_height"
    SS_WIDTH = "screenshot_width"
    SS_HIGHLIGHT_ELEMENT = "highlighted_screenshot"
    SS_KEEP_FILES = "keep_screenshots"
    SS_DIR = "screenshot_dir"

    VIDEO_ENABLED = "video_recording"
    VIDEO_KEEP_FILES = "keep_videos"
    VIDEO_DIR = "video_dir"
    VIDEO_RESIZE_PERCENT = "video_resize_percent"
    VIDEO_FRAME_RATE = "video_frame_rate"
    VIDEO_HEIGHT = "video_height"
    VIDEO_WIDTH = "video_width"


__default_action = "store"
__default_prefix = "report_"

__param_values: Mapping[Parameter, Any] = {}

__params: Mapping[Parameter, Mapping[str, Any]] = {
    Parameter.JS_LOG_FREQUENCY: {
        "default_value": "failed_test_only",
        "allowed_values": [
            "always",
            "each_ui_operation",
            "end_of_each_test",
            "failed_test_only",
            "never",
        ],
        "cast_to": EnhancedReportOperationFrequency,
        "doc": "Specifies when to capture info from the browser console log.",
    },
    Parameter.SS_FREQUENCY: {
        "default_value": "each_ui_operation",
        "allowed_values": [
            "always",
            "each_ui_operation",
            "end_of_each_test",
            "failed_test_only",
            "never",
        ],
        "cast_to": EnhancedReportOperationFrequency,
        "doc": "Specifies when to capture screenshots.",
    },
    Parameter.SS_RESIZE_PERCENT: {
        "default_value": 40,
        "doc": "A percentage by which the screenshot will be resized. This is ignored if screenshot height and width "
        "values are also provided. Valid values - 75, 60, 50, etc.",
        "cast_to": int,
    },
    Parameter.SS_HEIGHT: {
        "default_value": 0,
        "cast_to": int,
        "doc": "The expected height of the resized screenshot used in reports. Actual value could be slightly "
        "different as it needs to fit the aspect ratio.",
    },
    Parameter.SS_WIDTH: {
        "default_value": 0,
        "cast_to": int,
        "doc": "The expected width of the resized screenshot used in reports. Actual value could be slightly different "
        "as it needs to fit the aspect ratio.",
    },
    Parameter.SS_HIGHLIGHT_ELEMENT: {
        "default_value": False,
        "cast_to": bool,
        "doc": "If set to True, the element being interacted with will be highlighted before taking the screenshot.",
    },
    Parameter.SS_KEEP_FILES: {
        "default_value": False,
        "cast_to": bool,
        "doc": "If set to True, generated screenshot images will not be deleted after the test run.",
    },
    Parameter.SS_DIR: {
        "default_value": "reports/screenshots",
        "doc": "The path to the directory where screenshots will be stored.",
    },
    Parameter.VIDEO_ENABLED: {
        "default_value": False,
        "cast_to": bool,
        "doc": "If set to True, a video will be recorded for each test.",
    },
    Parameter.VIDEO_KEEP_FILES: {
        "default_value": False,
        "cast_to": bool,
        "doc": "If set to True, generated video files will not be deleted after the test run.",
    },
    Parameter.VIDEO_DIR: {
        "default_value": "reports/videos",
        "doc": "The path to the directory where video files will be stored.",
    },
    Parameter.VIDEO_RESIZE_PERCENT: {
        "default_value": 75,
        "cast_to": int,
        "doc": "A percentage by which the video frames will be resized. This is ignored if screenshot height and width "
        "values are also provided. Valid values - 75, 60, 50, etc.",
    },
    Parameter.VIDEO_FRAME_RATE: {
        "default_value": 30,
        "cast_to": int,
        "doc": "The expected number of frames per second while recording a video. This is applicable only when "
        "enough frames were recorded in one second, which is not guaranteed.",
    },
    Parameter.VIDEO_HEIGHT: {
        "default_value": 0,
        "cast_to": int,
        "doc": "Expected height of the video. Actual value could be different as it needs to fit the aspect ratio.",
    },
    Parameter.VIDEO_WIDTH: {
        "default_value": 0,
        "cast_to": int,
        "doc": "Expected width of the video. Actual value could be different as it needs to fit the aspect ratio.",
    },
}


def _get_value(request: FixtureRequest, parameter: Parameter):
    full_arg_name: str = f"{__default_prefix}{parameter.value}"
    val_from_env_var = os.getenv(
        full_arg_name.upper(), default=__params[parameter]["default_value"]
    )
    val_from_cmd_line = request.config.getoption(full_arg_name)
    value = val_from_cmd_line or val_from_env_var

    # Cast the value to the specified type, if needed
    if "cast_to" in __params[parameter]:
        value = __params[parameter]["cast_to"](value)

    return value


def register_with(
    parser_or_group: Union[argparsing.Parser, argparsing.OptionGroup]
):
    """Adds the command line arguments to the parser"""
    for parameter, details in __params.items():

        # Generate the docstring for the argument
        docstring: str = details.get("doc", "No docstring for this argument")
        if "default_value" in details:
            def_value = details.get("default_value")

            # Surround with single quotes if it is a string
            if type(def_value) == str:
                def_value = f"'{def_value}'"

            docstring += f""" Default value - {def_value}."""
        if "allowed_values" in details:
            docstring += f""" Allowed values: '{"', '".join(details.get("allowed_values"))}'."""

        parser_or_group.addoption(
            f"--{__default_prefix}{parameter.value}",
            action=details.get("action", __default_action),
            default=None,
            help=docstring,
        )


def get_all_values(request: FixtureRequest):
    """Returns a dictionary with values for all the options"""
    global __param_values

    if __param_values:
        return __param_values

    logger.debug("Getting values for all the options")
    __param_values = {
        parameter: _get_value(request, parameter)
        for parameter in __params.keys()
    }
    return __param_values


def get_value(parameter: Parameter, request: FixtureRequest = None):
    """Gets the value for a specified argument.
    Looks for the argument in the following order:
    1. Command line argument
    2. Environment variable
    3. Default value, set by the plugin
    """
    return get_all_values(request)[parameter]
