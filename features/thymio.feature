Feature: Thymio
  Manage a TDM client connection to a Thymio.

  Scenario Outline: Obtain a program
    Given a Thymio
    When Ask for a program
    Then Obtain a program

  @tdm
  Scenario Outline: Compile and run a program
    Given a Thymio
    And a program
    When compile and run program
    Then program is running
