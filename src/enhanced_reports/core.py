import enum
import inspect
import logging
from types import ModuleType
from typing import Any, List, Callable, Dict, Set

import threading
import wrapt

from _pytest.config import argparsing
from _pytest.fixtures import FixtureRequest
from pytest import fixture

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.abstract_event_listener import (
    AbstractEventListener,
)
from selenium.webdriver.support.event_firing_webdriver import (
    EventFiringWebDriver,
)

from . import screenshot_manager
from . import browser_console_manager
from .video_manager import ScreenRecorder
from . import common_utils
from . import config
from .config import EnhancedReportOperationFrequency as OpFreq, Parameter

logger = logging.getLogger(__name__)
logger.info("Loaded " + __file__)

# region Global Vars
__currently_applicable_reports: List[ModuleType] = []
__report_options: Dict[Parameter, Any] = {}


# endregion


# region Registering and retrieving config parameters
def pytest_addoption(parser: argparsing.Parser):
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    group = parser.getgroup("enhanced-report")
    config.register_with(group)


@fixture(scope="session", autouse=True)
def _report_options(request: FixtureRequest) -> Dict[Parameter, Any]:
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    __report_options.update(config.get_all_values(request))
    # logger.info("Report options: \n"+"\n".join([str(item) for item in __report_options.items()]))
    return __report_options


# endregion


# region Custom enums
class EnhancedReportAttachments(enum.Enum):
    # Tuple format: (type of attachment, minimal description for the attachment type)
    JS_LOG = ("text", "js log")
    SS = ("image", "screenshot")
    SS_WITH_HIGHLIGHT = ("image", "highlighted screenshot")
    VIDEO = ("video", "video")


class EnhancedReportLabels(enum.Enum):
    # Labels that would be used in the actual report(s)
    JS_LOGS = "Logs from browser console"
    JS_LOGS_WITH_DESC = f"{JS_LOGS} {{}}"
    SS = "Screenshot"
    SS_WITH_DESC = f"{SS} {{}}"
    VIDEO = "Video"
    VIDEO_WITH_DESC = f"{VIDEO} {{}}"

    def desc(self, desc: str = "") -> str:
        return self.value.format(desc)


class EnhancedReportTestState(enum.Enum):
    """Test states during which we expect a reportable event to occur."""

    BEFORE_TEST = "before test"
    CUSTOM_DURING_TEST = "custom during test"
    AFTER_TEST = "after test"
    BEFORE_UI_OPERATION = "before ui operation"
    AFTER_UI_OPERATION = "after ui operation"
    ERROR = "error"
    FAILED = "failed"
    PASSED = "passed"
    SKIPPED = "skipped"


# endregion


# region Rules and generic logic for attaching data to reports
"""
Maps each test state to a set of op. frequencies that allow data capture in that state.
"""
__state_and_allowed_frequencies: Dict[EnhancedReportTestState, Set[OpFreq]] = {
    EnhancedReportTestState.BEFORE_TEST: {OpFreq.ALWAYS},
    EnhancedReportTestState.BEFORE_UI_OPERATION: {
        OpFreq.ALWAYS,
        OpFreq.EACH_UI_OPERATION,
    },
    EnhancedReportTestState.AFTER_UI_OPERATION: {
        OpFreq.ALWAYS,
        OpFreq.EACH_UI_OPERATION,
    },
    EnhancedReportTestState.AFTER_TEST: {
        OpFreq.ALWAYS,
        OpFreq.END_OF_EACH_TEST,
    },
    EnhancedReportTestState.ERROR: {
        OpFreq.ALWAYS,
        OpFreq.END_OF_EACH_TEST,
        OpFreq.FAILED_TEST_ONLY,
    },
    EnhancedReportTestState.FAILED: {
        OpFreq.ALWAYS,
        OpFreq.END_OF_EACH_TEST,
        OpFreq.FAILED_TEST_ONLY,
    },
    EnhancedReportTestState.PASSED: {OpFreq.ALWAYS, OpFreq.END_OF_EACH_TEST},
    # planned for the future. not supported atm
    EnhancedReportTestState.CUSTOM_DURING_TEST: {},
    # a skipped test is not expected to have an active browser session to extract info from
    EnhancedReportTestState.SKIPPED: {},
}

"""
Maps each attachment type to the config param for that type.
"""
__attachment_and_config: Dict[EnhancedReportAttachments, Parameter] = {
    EnhancedReportAttachments.JS_LOG: Parameter.JS_LOG_FREQUENCY,
    EnhancedReportAttachments.SS: Parameter.SS_FREQUENCY,
    EnhancedReportAttachments.SS_WITH_HIGHLIGHT: Parameter.SS_HIGHLIGHT_ELEMENT,
    EnhancedReportAttachments.VIDEO: Parameter.VIDEO_ENABLED,
}


def __can_record(
    attachment_type: EnhancedReportAttachments,
    current_state: EnhancedReportTestState,
) -> bool:
    """
    This method returns True or False based on enhancement report attachment type and enhanced report state.
    @param attachment_type: Provide attachment type as VIDEO, TXT and SS_WITH_HIGHLIGHT
    @param current_state: Provide enhanced report state as "before test", "custom during test",
    "after test", "before ui operation", "after ui operation", "error", "failed", "passed", "skipped".
    @return: Return True or False
    """
    # Get the config value for the current type
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    param_value = __report_options[__attachment_and_config[attachment_type]]
    logger.info(f"current param_value {param_value}")
    if (
        not param_value
        or param_value not in __state_and_allowed_frequencies[current_state]
    ):
        return False

    can_record: bool = True

    if (
        attachment_type == EnhancedReportAttachments.VIDEO and not param_value
    ):  # Video is not enabled
        # logger.debug("Rejection reason: Video is not enabled")
        can_record = False
    elif attachment_type == EnhancedReportAttachments.SS_WITH_HIGHLIGHT:
        # With highlighted screenshots, check both the specific param and the screenshot frequency
        if (
            not param_value
            or __report_options[Parameter.SS_FREQUENCY]
            not in __state_and_allowed_frequencies[current_state]
        ):
            # logger.debug("Rejection reason: Highlighted screenshots are either not enabled, or they're not allowed
            # in this state")
            can_record = False

    # logger.debug(f"Recording {attachment_type} is {'' if can_record else 'NOT '} allowed in state - {current_state}")
    return can_record


def __report_data_handler(
    attachment_type: EnhancedReportAttachments,
    attachment_name: str,
    attachment_value: str,
    **kwargs,
):
    """
    This method call the attachment methods dynamic like attach_text, attach_image and attach_video
    @param attachment_type: Provide attachment type as JS_LOG, SS, SS_WITH_HIGHLIGHT and VIDEO
    @param attachment_name: Provide label as a string like text, image and video
    @param attachment_value: Provide path as a string
    @param kwargs: Provide any related args of EnhancedReportAttachments
    """
    logger.debug(
        logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    )
    for report_mod in __currently_applicable_reports:
        try:
            # Form a method Ex: attach_text(attachment_name, attachment_value)
            getattr(report_mod, f"attach_{attachment_type.value[0]}")(
                attachment_name, attachment_value, **kwargs
            )
        except Exception as e:
            logger.error(
                f"Error while attaching {attachment_type.value[1]} to report {report_mod}: {e}"
            )


# endregion


# region Convenience functions for attaching data to reports
def __capture_ss(
    attachment_type: EnhancedReportAttachments,
    state: EnhancedReportTestState,
    scenario_name: str,
    name: str,
    driver: WebDriver,
    element=None,
):
    """
    Capture screenshots of a scenario for every action of a highlighted element
    @param attachment_type: Provide attachment type as VIDEO, TXT, SS and SS_WITH_HIGHLIGHT
    @param state: Provide enhanced report state as "before test", "custom during test",
    "after test", "before ui operation", "after ui operation", "error", "failed", "passed", "skipped".
    @param scenario_name: Provide scenario name
    @param name: Provide action name or screenshot name
    @param driver: Provide instance of a driver
    @param element: Provide an element
    @return:
    """
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    if not __can_record(attachment_type, state):
        return

    if (
        attachment_type == EnhancedReportAttachments.SS_WITH_HIGHLIGHT
        and element
    ):

        path: str = screenshot_manager.get_highlighted_screenshot(
            element, name, scenario_name, __report_options, driver
        )
    else:
        path: str = screenshot_manager.get_screenshot(
            name, scenario_name, __report_options, driver
        )

    logger.debug(f"Captured screenshot path: {path}")
    if path:  # there is a chance that a screenshot was not captured
        __report_data_handler(
            attachment_type, EnhancedReportLabels.SS_WITH_DESC.desc(name), path
        )


def __capture_js_logs(
    state: EnhancedReportTestState, driver: WebDriver, label: str
):
    """
    Capture JavaScript Logs
    @param state: Provide enhanced report state as "before test", "custom during test",
    "after test", "before ui operation", "after ui operation", "error", "failed", "passed", "skipped".
    @param driver: Provide driver instance
    @param label: Provide label as string
    @return: Return none for alert as a special case.
    """
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    if not __can_record(EnhancedReportAttachments.JS_LOG, state):
        return

    logs = browser_console_manager.get_js_logs(driver)
    __report_data_handler(
        EnhancedReportAttachments.JS_LOG,
        EnhancedReportLabels.JS_LOGS_WITH_DESC.desc(label),
        logs,
    )


# endregion


# region Report agnostic setup and teardown
@fixture(scope="session", autouse=True)
def _global_config(
    request: FixtureRequest, _report_options: Dict[Parameter, Any]
):
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")

    # region Teardown
    def remove_test_dir():
        try:
            if not _report_options[Parameter.VIDEO_KEEP_FILES]:
                common_utils.delete_dir(_report_options[Parameter.VIDEO_DIR])

            if not _report_options[Parameter.SS_KEEP_FILES]:
                common_utils.delete_dir(_report_options[Parameter.SS_DIR])
            else:
                common_utils.delete_files(_report_options[Parameter.SS_DIR])
        except Exception as error:
            logger.error(f"Error occurred while cleaning up: {error}")

    request.addfinalizer(remove_test_dir)
    # endregion

    # region Setup
    # create the screenshot directory if it doesn't exist
    if _report_options[Parameter.SS_FREQUENCY] != OpFreq.NEVER:
        common_utils.mkdir(_report_options[Parameter.SS_DIR])

    # create the video directory if it doesn't exist
    if _report_options[Parameter.VIDEO_ENABLED]:
        common_utils.mkdir(_report_options[Parameter.VIDEO_DIR])
    # endregion


# endregion


# region Local utils
def __get_all_module_names_in_relative_path(path: str) -> List[str]:
    """
    Getting the absolute path to the current file, and removing the file name to get the current directory
    @param path: Provide directory path
    @return: Return list of strings
    """
    import pkgutil
    import os

    # Getting the absolute path to the current file, and removing the file name to get the current directory
    lib_path: str = os.path.abspath(__file__)[: -len("core.py")]
    return [name for _, name, _ in pkgutil.iter_modules([lib_path + path])]


def __is_pytest_plugin_installed(
    request: FixtureRequest, plugin_name: str
) -> bool:
    """
    Return true or false boolean value is the pytest plugin installed
    @param request: The request fixture is a special fixture providing information of the requesting test function.
    @param plugin_name: Provide plugin name
    @return: Return True or False
    """
    return request.config.pluginmanager.has_plugin(plugin_name)


# endregion


# region handling report lib integrations
@fixture(scope="session", autouse=True)
def _reports(
    request: FixtureRequest, _report_options: Dict[Parameter, Any]
) -> List[ModuleType]:
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")

    # region Teardown
    def report_specific_cleanup():
        for report_mod in __currently_applicable_reports:
            try:
                logger.debug(
                    "Calling session scoped teardown for " + report_mod.__name__
                )
                report_mod.perform_session_cleanup(request, _report_options)
            except Exception as exc:
                logger.error(
                    f"Error while performing session level cleanup for report {report_mod.__name__}: {exc}"
                )

    request.addfinalizer(report_specific_cleanup)
    # endregion

    # region Setup
    supported_reports: List[str] = __get_all_module_names_in_relative_path(
        "report_libs"
    )
    logger.debug(f"supported reports - {supported_reports}")

    import importlib

    for report_name in supported_reports:
        try:
            if __is_pytest_plugin_installed(request, report_name):
                logger.debug(
                    f"pytest plugin '{report_name}' is installed. Importing corresponding report lib"
                )
                mod = importlib.import_module(
                    f".report_libs.{report_name}", package="enhanced_reports"
                )
                __currently_applicable_reports.append(mod)
                logger.debug("Calling session scoped setup for " + report_name)
                mod.perform_session_setup(request, _report_options)
            else:
                logger.debug(
                    f"pytest plugin '{report_name}' is not installed. Ignoring module"
                )
        except Exception as e:
            logger.error(
                f"Failed to load or setup session level enhancements for report {report_name}: {e}"
            )

    return __currently_applicable_reports
    # endregion


@fixture(autouse=True)
def _reports_function_scope(
    request: FixtureRequest,
    _reports: List[ModuleType],
    _report_options: Dict[Parameter, Any],
):
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")

    # region Teardown
    def report_specific_cleanup():
        for report_mod in _reports:
            try:
                logger.debug(
                    "Calling function scoped teardown for "
                    + report_mod.__name__
                )
                report_mod.perform_function_cleanup(request, _report_options)
            except Exception as exc:
                logger.error(
                    f"Error while performing cleanup for function scope for report {report_mod.__name__}: {exc}"
                )

    request.addfinalizer(report_specific_cleanup)
    # endregion

    # region Setup
    for report_mod in _reports:
        try:
            logger.debug(
                "Calling function scoped setup for " + report_mod.__name__
            )
            report_mod.perform_function_setup(request, _report_options)
        except Exception as e:
            logger.error(
                f"Error while performing function level setup for report {report_mod.__name__}: {e}"
            )
    # endregion


# endregion


# region Gather test metadata
@fixture
def _scenario_name(request: FixtureRequest) -> str:
    return __scenario_name_supplier(request)()


def __scenario_name_supplier(request: FixtureRequest) -> Callable[[], str]:
    return lambda: request.node.nodeid.split("/")[-1].replace("::", " - ")


# endregion


# region WebDriver acquisition
@fixture
def _local_driver() -> Dict[str, WebDriver]:
    return {"driver": None}  # type: ignore


@fixture  # TODO: test this with a session scoped fixture in the test framework for instantiating the driver
def enhance_driver(
    request: FixtureRequest,
    _report_options: Dict[Parameter, Any],
    _local_driver,
):
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")

    def _enhanced_driver_getter(driver: WebDriver):
        _local_driver["driver"] = driver

        return EventFiringWebDriver(
            driver,
            WebDriverEventListener(
                _report_options,
                __capture_ss,
                __capture_js_logs,
                __scenario_name_supplier(request),
            ),
        )

    return _enhanced_driver_getter


# endregion


# region Video recording
@fixture(autouse=True)
def _video_capture(
    request: FixtureRequest,
    _scenario_name: str,
    _report_options: Dict[Parameter, Any],
):
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    screen_recorder = {}
    recorder_thread = None
    if __can_record(
        EnhancedReportAttachments.VIDEO, EnhancedReportTestState.BEFORE_TEST
    ):
        logger.debug("Initializing video recording")
        screen_recorder = ScreenRecorder(
            directory=_scenario_name,
            video_store=_report_options[Parameter.VIDEO_DIR],
        )
        common_utils.mkdir(_report_options[Parameter.VIDEO_DIR])

        driver = request.getfixturevalue("_local_driver")["driver"]
        recorder_thread = threading.Thread(
            target=screen_recorder.start_capturing,
            name="Recorder",
            args=[driver],
        )

        logger.debug("Starting video recording")
        recorder_thread.start()

        # this is inside the if block intentionally. only need to stop the recording if it was started
        request.addfinalizer(
            lambda: screen_recorder.stop_recording_and_stitch_video(
                _report_options, recorder_thread, _scenario_name, _scenario_name
            )
        )

    yield  # dummy yield in order to prevent the fixture from being run from the beginning during teardown


# endregion


# region Screenshot & js log capture
def pytest_bdd_step_error(
    request: FixtureRequest, feature, scenario, step, step_func
):
    """
    Record screenshot or js logs for bdd step error
    @param request: Provide request a fixture
    @param feature:
    @param scenario:
    @param step:
    @param step_func:
    """
    current_state = EnhancedReportTestState.ERROR
    op_name = "after action chain"

    driver = request.getfixturevalue("_local_driver")["driver"]
    scenario_name = request.getfixturevalue("_scenario_name")

    if __can_record(EnhancedReportAttachments.SS, current_state):
        __capture_ss(
            EnhancedReportAttachments.SS,
            current_state,
            scenario_name,
            op_name,
            driver,
        )

    if __can_record(EnhancedReportAttachments.JS_LOG, current_state):
        __capture_js_logs(current_state, driver, op_name)


def pytest_bdd_after_scenario(request: FixtureRequest, feature, scenario):
    """
    Record screenshot or js logs for after each scenario
    @param request: Provide request a fixture
    @param feature:
    @param scenario:
    """
    current_state = EnhancedReportTestState.AFTER_TEST
    op_name = "after test"

    driver = request.getfixturevalue("_local_driver")["driver"]
    scenario_name = request.getfixturevalue("_scenario_name")

    if __can_record(EnhancedReportAttachments.SS, current_state):
        __capture_ss(
            EnhancedReportAttachments.SS,
            current_state,
            scenario_name,
            op_name,
            driver,
        )

    if __can_record(EnhancedReportAttachments.JS_LOG, current_state):
        __capture_js_logs(current_state, driver, op_name)


@fixture(scope="session", autouse=True)
def _create_wrappers(
    request: FixtureRequest, _report_options: Dict[Parameter, Any]
):
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")
    current_state = EnhancedReportTestState.AFTER_UI_OPERATION
    op_name = "after action chain"

    if not __can_record(EnhancedReportAttachments.SS, current_state):
        return

    @wrapt.patch_function_wrapper(ActionChains, "perform")
    def wrap_action_chains_perform_method(wrapped, instance, args, kwargs):
        # here, wrapped is the original perform method in ActionChains
        # instance is `self` (it is not the case for classmethods though),
        # args and kwargs are a tuple and a dict respectively.

        wrapped(*args, **kwargs)  # note it is already bound to the instance

        scenario_name = request.getfixturevalue("_scenario_name")
        __capture_ss(
            EnhancedReportAttachments.SS,
            current_state,
            scenario_name,
            op_name,
            instance._driver,
        )
        __capture_js_logs(current_state, instance._driver, op_name)


class WebDriverEventListener(AbstractEventListener):
    def __init__(
        self,
        _report_options: Dict[Parameter, Any],
        ss_handler: Callable,
        js_log_handler: Callable,
        scenario_name_supplier: Callable[[], str],
    ):
        # just store all arguments as instance vars
        self.__report_options: Dict[Parameter, Any] = _report_options
        self.__capture_ss: Callable = ss_handler
        self.__capture_js_logs: Callable = js_log_handler
        self.__scenario_name_supplier: Callable[
            [], str
        ] = scenario_name_supplier

    def after_navigate_to(self, url: str, driver: WebDriver):
        """
        Capture screenshot and JS logs before after navigating of an url
        @param url: Provide an url
        @param driver: Provide instance of a driver
        """
        current_state = EnhancedReportTestState.AFTER_UI_OPERATION
        op_name: str = f"Navigation to {url}"
        self.__capture_ss(
            EnhancedReportAttachments.SS,
            current_state,
            self.__scenario_name_supplier(),
            op_name,
            driver,
        )
        self.__capture_js_logs(current_state, driver, op_name)

    def before_click(self, element: WebElement, driver: WebDriver):
        """
        Capture screenshot before click of an element
        @param element: Provide web element
        @param driver: Provide instance of a driver
        """
        current_state = EnhancedReportTestState.BEFORE_UI_OPERATION
        op_name: str = "before click"
        self.__capture_ss(
            EnhancedReportAttachments.SS_WITH_HIGHLIGHT,
            current_state,
            self.__scenario_name_supplier(),
            op_name,
            driver,
            element=element,
        )

    def after_click(self, element: WebElement, driver: WebDriver):
        """
        Capture screenshot after click of an element
        @param element: Provide web element
        @param driver: Provide instance of a driver
        """
        current_state = EnhancedReportTestState.AFTER_UI_OPERATION
        op_name: str = "after click"
        self.__capture_ss(
            EnhancedReportAttachments.SS,
            current_state,
            self.__scenario_name_supplier(),
            op_name,
            driver,
        )
        self.__capture_js_logs(current_state, driver, op_name)

    def before_change_value_of(self, element: WebElement, driver: WebDriver):
        """
        Capture screenshot before keyboard input
        @param element: Provide web element
        @param driver: Provide instance of a driver
        """
        current_state = EnhancedReportTestState.BEFORE_UI_OPERATION
        op_name = "before keyboard input"
        self.__capture_ss(
            EnhancedReportAttachments.SS_WITH_HIGHLIGHT,
            current_state,
            self.__scenario_name_supplier(),
            op_name,
            driver,
            element=element,
        )

    def after_change_value_of(self, element: WebElement, driver: WebDriver):
        """
        Capture screenshot after keyboard input
        @param element: Provide web element
        @param driver: Provide instance of a driver
        """
        current_state = EnhancedReportTestState.AFTER_UI_OPERATION
        op_name = "after keyboard input"
        self.__capture_ss(
            EnhancedReportAttachments.SS,
            current_state,
            self.__scenario_name_supplier(),
            op_name,
            driver,
        )
        self.__capture_js_logs(
            EnhancedReportTestState.AFTER_UI_OPERATION, driver, op_name
        )

    def after_execute_script(self, driver: WebDriver):
        """
        Capture screenshot after JS execution
        @param driver: Provide instance of a driver
        """
        current_state = EnhancedReportTestState.AFTER_UI_OPERATION
        op_name = "after JS execution"
        self.__capture_ss(
            EnhancedReportAttachments.SS,
            current_state,
            self.__scenario_name_supplier(),
            op_name,
            driver,
        )
        self.__capture_js_logs(current_state, driver, op_name)

    def after_navigate_back(self, driver: WebDriver):
        """
        Capture JS logs for navigating back
        @param driver: Provide driver instance.
        """
        self.__capture_js_logs(
            EnhancedReportTestState.AFTER_UI_OPERATION,
            driver,
            "after navigating back",
        )


# endregion
