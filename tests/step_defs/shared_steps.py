import logging
from selenium.webdriver.common.by import By
import allure
from pytest_bdd import when, parsers, then, given

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://newpage-solutions-inc.github.io/pytest-enhanced-reports/test-site"
)
FIRST_PAGE_URL = f"{BASE_URL}/index.html"
SECOND_PAGE_URL = f"{BASE_URL}/page2.html"

# Locators
FIRST_NAME = By.ID, "firstName"
LAST_NAME = By.ID, "lastName"
EMAIL = By.ID, "email"
PHONE = By.ID, "phone"
SUBMIT = By.ID, "submit"
MESSAGE = By.ID, "message"
LINK_TO_PAGE_2 = By.ID, "link_to_page_2"
LINK_TO_PAGE_1 = By.ID, "back_to_page1"


@given("I open first page")
def open_first_page(driver):
    driver.get(FIRST_PAGE_URL)
    check_first_page_displayed(driver)


@when("I open second page")
def open_second_page(driver):
    driver.get(SECOND_PAGE_URL)
    check_second_page_displayed(driver)


@when(parsers.parse("User enters first name {first_name}"))
def enter_first_name(driver, first_name):
    first_name_field = driver.find_element(*FIRST_NAME)
    first_name_field.send_keys(first_name)
    logger.info("first_name is entered")


@when(parsers.parse("User enters last name {last_name}"))
def enter_last_name(driver, last_name):
    last_name_field = driver.find_element(*LAST_NAME)
    last_name_field.send_keys(last_name)
    logger.info("last_name is entered")


@when(parsers.parse("User enters email {email}"))
def enter_email(driver, email):
    email_field = driver.find_element(*EMAIL)
    email_field.send_keys(email)
    logger.info("email is entered")


@when(parsers.parse("User enters phone {phone}"))
def enter_phone(driver, phone):
    phone_field = driver.find_element(*PHONE)
    phone_field.send_keys(phone)
    logger.info("last_name is entered")


@when("User clicks on submit button")
def click_login(driver):
    with allure.step("Submit Click"):
        driver.find_element(*SUBMIT).click()


@allure.severity(allure.severity_level.MINOR)
@then("User can see welcome message for new user")
def verify_message_new_user(driver):
    check_message_content(driver, "Welcome new user!")


@allure.severity(allure.severity_level.MINOR)
@then("User can see welcome message for existing user")
def verify_message_existing_user(driver):
    check_message_content(driver, "Welcome back!")


@when("I click go to page 2")
def click_go_to_page2(driver):
    with allure.step("Go To Page 2 Click"):
        driver.find_element(*LINK_TO_PAGE_2).click()
        check_second_page_displayed(driver)


@then("I verify page 2 is displayed")
def verify_page_2(driver):
    check_second_page_displayed(driver)


@when("User clicks on go to page 1 button")
def click_go_to_page1(driver):
    driver.find_element(*LINK_TO_PAGE_1).click()


@then("User can see page 1")
def verify_page_1(driver):
    check_first_page_displayed(driver)


def check_first_page_displayed(driver):
    assert len(driver.find_elements(*FIRST_NAME)) == 1


def check_second_page_displayed(driver):
    assert len(driver.find_elements(*LINK_TO_PAGE_1)) == 1


def check_message_content(driver, content):
    message = driver.find_element(*MESSAGE)
    assert message.text == content, "message are different"
