Feature: Lane
  Find, sort, and format detectable lanes.  

  Scenario Outline: Lane detection
    Given an <image> file
    When find all
    Then found all <lane>

    Examples:
    | image            | lane     |
    | straight.jpeg    | 0,200    |
    | curve-right.jpeg | 230;330  |
    | curve-left.jpeg  | -230;330 |
    | star01.jpeg      | NA       |
