from typing import Dict, Any, Tuple

from datetime import datetime
import base64
from PIL import Image
from io import BytesIO

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions

from . import common_utils
from .config import Parameter

import logging
import inspect

logger = logging.getLogger(__name__)
logger.info("Loaded " + __file__)


__desired_resolution: Tuple[int, int] = None
__resize_factor: float = None


@common_utils.fail_silently
def get_screenshot(
    screenshot_name: str, scenario_name: str, plugin_options, driver: WebDriver
) -> str:
    """
    Return the screenshot for the scenario name
    @param screenshot_name: Provide the screenshot name
    @param scenario_name: Provide the scenario name
    @param plugin_options: Provide plugin options contains video_height and video_width
    @param driver: Provide the driver instance
    @return: Return image path
    """
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    # selenium can't take screenshots if a browser alert/prompt is open. trying to do so would break the current test.
    # so, skipping screenshots in such a case
    if expected_conditions.alert_is_present()(driver):
        return ""
    return __get_resized_image(
        driver.get_screenshot_as_base64(),
        plugin_options,
        scenario_name,
        screenshot_name=screenshot_name,
    )


@common_utils.fail_silently
def get_highlighted_screenshot(
    element: WebElement,
    action_name: str,
    scenario_name: str,
    report_options,
    driver: WebDriver,
    color: str = "red",
    border_width: int = 5,
) -> str:
    """
    Return an image path for the web element action
    @param element: Provide web element
    @param action_name: Provide action name
    @param scenario_name: Provide Scenario name
    @param report_options: Provide report options
    @param driver: Provide driver instance
    @param color: Provide color values like red, green and yellow
    @param border_width: Provide border width
    @return: return path of an image
    """
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")

    def apply_style(s):
        driver.execute_script(
            "arguments[0].setAttribute('style', arguments[1]);", element, s
        )

    original_style = element.get_attribute("style")
    apply_style(
        "border: {0}px solid {1}; padding:{2}px".format(border_width, color, 5)
    )

    path: str = get_screenshot(
        action_name, scenario_name, report_options, driver
    )

    apply_style(original_style)

    return path


def __get_resized_image(
    image_bytes: bytes,
    report_options: Dict[Parameter, Any],
    scenario_name: str,
    screenshot_name="screenshot",
) -> str:
    """
    Return resized screenshot file path
    @param image_bytes: Provide image size in the form of bytes
    @param report_options: Provide report options
    @param scenario_name: Provide scenario name
    @param screenshot_name: Provide screenshot name
    @return: Resized screenshot file path
    """
    global __desired_resolution, __resize_factor
    __desired_resolution = (
        __desired_resolution
        if __desired_resolution
        else (
            report_options[Parameter.SS_WIDTH],
            report_options[Parameter.SS_HEIGHT],
        )
    )
    __resize_factor = (
        __resize_factor
        if __resize_factor
        else report_options[Parameter.SS_RESIZE_PERCENT] / 100
    )

    screenshot_file_name: str = (
        common_utils.clean_filename(f" {str(datetime.now())}") + ".png"
    )
    logger.debug("Temp screenshot file name: " + screenshot_file_name)

    # open the image directly thru an in-memory buffer
    img = Image.open(BytesIO(base64.b64decode(image_bytes)))

    # Check if user wants to keep the screenshots, if yes then create directory and save original images
    if report_options[Parameter.SS_KEEP_FILES]:
        ss_dir: str = f"{report_options[Parameter.SS_DIR]}/{scenario_name}"
        common_utils.mkdir(ss_dir)
        img.save(f"{ss_dir}/{screenshot_file_name}")

    # if the user has not passed a specific resolution, create it from the resize factor
    desired_resolution = (
        common_utils.get_resized_resolution(
            img.width, img.height, __resize_factor
        )
        if __desired_resolution == (0, 0)
        else __desired_resolution
    )
    logger.debug("Desired resolution: " + str(desired_resolution))

    # resize image to the desired resolution. if more customizability is needed, consider the resize or reduce methods
    img.thumbnail(desired_resolution)
    # in tobytes() need to return the array before the join operation happens
    # return img.tobytes()

    path: str = (
        f"{report_options[Parameter.SS_DIR]}/"
        f"{common_utils.clean_filename(scenario_name)}_{screenshot_file_name}"
    )
    img.save(path)
    logger.debug("Resized screenshot file path: " + path)
    return path
