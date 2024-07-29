import inspect
import logging
from typing import Mapping, Any

from _pytest.fixtures import FixtureRequest
import wrapt

import allure
from allure_commons.types import AttachmentType
from allure_commons.lifecycle import AllureLifecycle
from allure_commons.model2 import TestResult
from allure_commons import plugin_manager
from allure_commons.model2 import TestStepResult

from allure_pytest_bdd.pytest_bdd_listener import PytestBDDListener

from enhanced_reports.config import Parameter

logger = logging.getLogger(__name__)


logger.info("Loaded " + __file__)


def attach_text(name: str, value: str, **kwargs):
    """
    Attach text to the scenario step
    @param name: Provide name as a string input
    @param value: Provide value as a string input
    @param kwargs:
    """
    allure.attach(bytes(value, "utf-8"), name, AttachmentType.TEXT)


def attach_image(name: str, path: str, **kwargs):
    """
    Attach image path to the scenario step
    @param name: Provide name as a string input
    @param path: Provide image path as a string input
    @param kwargs:
    """
    allure.attach.file(
        path,
        name=name,
        attachment_type=AttachmentType.PNG,
    )


def attach_video(name: str, path: str, **kwargs):
    """
    Attach video path to the scenario step
    @param name: Provide name as a string input
    @param path: Provide video path as a string input
    @param kwargs:
    """
    allure.attach.file(
        path,
        name=name,
        attachment_type=AttachmentType.WEBM,
    )


def update_test_results_for_scenario_outline():
    """
    Allure has an open bug (https://github.com/allure-framework/allure-python/issues/636) which prevents the
    inclusion of tests with scenario outlines in allure report. There is no fix available yet, so we manually
    remove the params which are equals to '_pytest_bdd_example'. This param if included in test results, causes
    errors in report generation due to duplicate keys in the json
    """
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")

    def _custom_write_test_case(self, uuid=None):
        """Allure has an open bug (https://github.com/allure-framework/allure-python/issues/636) which prevents the
        inclusion of tests with scenario outlines in allure report. There is no fix available yet, so we manually
        remove the params which are equals to '_pytest_bdd_example'. This param if included in test results, causes
        errors in report generation due to duplicate keys in the json"""
        test_result = self._pop_item(uuid=uuid, item_type=TestResult)
        if test_result:
            if test_result.parameters:
                adj_parameters = []
                for param in test_result.parameters:
                    if param.name != "_pytest_bdd_example":
                        # do not include parameters with "_pytest_bdd_example"
                        adj_parameters.append(param)
                test_result.parameters = adj_parameters

            for index in range(0, len(test_result.steps)):
                if ":\n|" in test_result.steps[index].name:
                    # Remove the data table from the step name
                    step_desc = test_result.steps[index].name.split(":")
                    test_result.steps[index].name = step_desc[0]

            plugin_manager.hook.report_result(result=test_result)

    AllureLifecycle.write_test_case = _custom_write_test_case


def wrapper_for_unexecuted_steps():
    """
    When a bdd step fails, test execution is stopped hence next steps are not executed,
    allure report doesn't include the steps that were not executed due to a failed step before them
    To overcome this issue we are intercepting the PytestBDDListener._scenario_finalizer method to add the
    non executed steps to test results
    """
    logger.debug(f"Entered {inspect.currentframe().f_code.co_name}")

    @wrapt.patch_function_wrapper(PytestBDDListener, "_scenario_finalizer")
    def wrap_scenario_finalizer(wrapped, instance, args, kwargs):
        # here, wrapped is the original perform method in PytestBDDListener
        # instance is `self` (it is not the case for classmethods though),
        # args and kwargs are a tuple and a dict respectively.

        wrapped(*args, **kwargs)  # note it is already bound to the instance

        test_result = instance.lifecycle._get_item(
            uuid=instance.lifecycle._last_item_uuid(item_type=TestResult),
            item_type=TestResult,
        )
        if len(args[0].steps) > len(test_result.steps):
            # if there are more steps in scenario than in test result, then add the remaining steps to test result
            for i in range(len(test_result.steps), len(args[0].steps)):
                test_result.steps.append(
                    TestStepResult(
                        name=f"{args[0].steps[i].keyword} {args[0].steps[i].name}",
                        status="skipped",
                    )
                )


def perform_session_setup(
    request: FixtureRequest, report_options: Mapping[Parameter, Any]
):
    update_test_results_for_scenario_outline()
    wrapper_for_unexecuted_steps()


def perform_session_cleanup(
    request: FixtureRequest, report_options: Mapping[Parameter, Any]
):
    pass


def perform_function_setup(
    request: FixtureRequest, report_options: Mapping[Parameter, Any]
):
    pass


def perform_function_cleanup(
    request: FixtureRequest, report_options: Mapping[Parameter, Any]
):
    pass
