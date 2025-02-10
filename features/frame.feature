Feature: Frame
  Camera frame.

  Scenario Outline: Retrieve grayscale
    Given a camera image
    When get grayscale
    Then grayscale is as expected

  Scenario Outline: Retrieve edges
    Given a camera image
    When get edges
    Then edges is as expected

  Scenario Outline: Remap features
    Given a camera image
    When get grayscale
    And get edges
    And remap grayscale feature
    And remap edge feature
    Then remapped grayscale feature is correct
    And remapped edge feature is correct

  Scenario Outline: Decorate
    Given a camera image
    When decorate things
    And decorate lanes
    Then decorated image is as expected
