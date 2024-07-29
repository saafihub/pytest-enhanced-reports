Feature: Test First Page
  Background:
    Given I open first page

  # fail scenario
  Scenario: Failed test only
    When User enters first name Existing
    And User enters last name User
    And User enters email test@test.com
    And User enters phone 1234567890
    And User clicks on submit button
    # True:
    # Then User can see welcome message for existing user
    # False:
    Then User can see welcome message for new user

  # pass scenario
  Scenario: Run Test for browser's outputs
    When I click go to page 2
