Feature: Thing
  Find, sort, and format detectable things.

  Scenario Outline: Find all Things
    Given an <image> file
    When find all
    Then found all <balls> <cubes> <stars>

    Examples:
    | image       | balls                 | cubes                | stars                  |
    | ball01.jpeg | 15,188,92             | None                 | None                   |
    | ball02.jpeg | 15,188,92;-855,263,87 | None                 | None                   |
    | cube01.jpeg | None                  | 25,354,95            | None                   |
    | cube02.jpeg | None                  | 451,327,92;1,488,90  | None                   |
    | star01.jpeg | None                  | None                 | 0,338,82               |
    | star02.jpeg | None                  | None                 | 806,119,80;-433,306,67 |
    | mixed.jpeg  | -855,263,87;15,188,92 | -7,452,90;462,341,91 | 754,120,80;-435,310,85 |

  Scenario Outline: Find best Things
    Given an <image> file
    When find all
    And sort best
    Then found best 1 <balls> <cubes> <stars>

    Examples:
    | image      | balls     | cubes      | stars       |
    | mixed.jpeg | 15,188,92 | 462,341,91 | -435,310,85 |

  Scenario Outline: Format Things
    Given an <image> file
    When find all
    And sort best
    And format
    Then format yields <balls> <cubes> <stars>

    Examples:
    | image       | balls | cubes | stars |
    | ball01.jpeg | '[{"class":0,"conf":92,"color":6,"az":15,"el":188,"xyxy":[292,535,358,467],"rgb":[60,70,74],"name":"Ball","label":"Ball 0.92"}]' | None | None |
    | cube01.jpeg | None | '[{"class":1,"conf":95,"color":6,"az":25,"el":354,"xyxy":[297,451,359,376],"rgb":[55,68,72],"name":"Cube","label":"Cube 0.95"}]' | None |
    | star01.jpeg | None | None | '[{"class":2,"conf":82,"color":7,"az":0,"el":338,"xyxy":[292,449,348,395],"rgb":[0,48,168],"name":"Star","label":"Star 0.82"}]' |
