from selenium.webdriver.remote.webdriver import WebDriver
from datetime import datetime
import logging
import inspect


logger = logging.getLogger(__name__)
logger.info("Loaded " + __file__)


def get_js_logs(driver: WebDriver) -> str:
    """
    Return JavaScript logs in the format of %Y-%m-%d %H:%M:%S level source message.
    @param driver: Instance of a Webdriver.
    @return: Return formatted output string.
    """
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    logs = _capture_output(driver)
    return _format_outputs(logs)


def _capture_output(driver: WebDriver) -> list:
    """
    Return browser log of a driver
    @param driver: Instance of a Webdriver.
    @return: Return list of browser logs
    """
    return driver.get_log("browser")


def _format_outputs(logs: list) -> str:
    """
    Format list of logs and convert in the string format - %Y-%m-%d %H:%M:%S level source message.
    @param logs: List of logs
    @return: Output in the String format
    """
    output = ""
    for item in logs:
        i_time = datetime.fromtimestamp(
            item.get("timestamp", 0) / 1000
        ).strftime("%Y-%m-%d %H:%M:%S")
        i_source = item.get("source")
        i_level = item.get("level")
        i_message = item.get("message")
        output += "{} {} {} {}\n".format(i_time, i_level, i_source, i_message)

    return output
