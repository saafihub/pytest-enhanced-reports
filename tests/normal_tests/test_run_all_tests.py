from pytest_bdd import scenarios
from tests.step_defs.shared_steps import *  # noqa

scenarios("../features/test_site.feature")
