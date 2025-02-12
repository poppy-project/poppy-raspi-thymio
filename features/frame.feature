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
    And a feature <xy>
    When get grayscale
    And get edges
    And remap grayscale feature
    And remap edge feature
    Then remapped grayscale feature is <gray_xy>
    And remapped edge feature is <edge_xy>

    Examples:
    | xy    | gray_xy | edge_xy |
    | 10,10 | 10,10   | 20,20   |
    | 100,6 | 100,6   | 200,12  |

  Scenario Outline: Decorate
    Given a camera image
    And a set of things
    And a set of lanes
    When decorate things and lanes
    Then decorated image is as expected
