Feature: Lane
  Find, sort, and format detectable lanes.  

  Scenario Outline: Lane detection
    Given image from file <image>
    When find all
    Then found all <lane>

    Examples:
    | image            | lane     |
    | straight.jpeg    | 68       |
    | curve-right.jpeg | 230;330  |
    | curve-left.jpeg  | -230;330 |
    | star01.jpeg      | None     |
