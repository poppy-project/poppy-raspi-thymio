Feature: Thing
  Find, sort, and format detectable things.

  Scenario Outline: Find all Things
    Given image from file <image>
    When find all
    Then found all <balls> <cubes> <stars>

    Examples:
    | image       | balls                 | cubes                | stars                  |
    | ball01.jpeg | 15,188,92             | None                 | None                   |
    | ball02.jpeg | 15,188,92;-855,263,87 | None                 | None                   |
    | cube01.jpeg | None                  | 25,354,95            | None                   |
    | cube02.jpeg | None                  | 451,327,92;1,488,90  | None                   |
    | star01.jpeg | None                  | None                 | -4,338,82              |
    | star02.jpeg | None                  | None                 | 806,119,80;-433,306,67 |
    | mixed.jpeg  | -855,263,87;15,188,92 | -7,452,90;462,341,91 | 754,120,80;-435,310,85 |

  Scenario Outline: Find best Things
    Given image from file <image>
    When find all
    And sort best
    Then found best 1 <balls> <cubes> <stars>

    Examples:
    | image      | balls       | cubes      | stars      |
    | mixed.jpeg | -855,263,87 | None       | None       |
    | mixed.jpeg | None        | 462,341,91 | None       |
    | mixed.jpeg | None        | None       | 754,120,80 |
    | mixed.jpeg | -855,263,87 | 462,341,91 | 754,120,80 |

  Scenario Outline: Format Things
    Given image from file <image>
    When find all
    And format
    Then format yields <balls> <cubes> <stars>

    Examples:
    | image       | balls | cubes | stars |
    | ball01.jpeg | W3siY2xhc3MiOjEsImNvbmYiOjkyLCJjb2xvciI6NiwiYXoiOjE1LCJlbCI6MTg4LCJ4eXh5IjpbMjkyLDUzNSwzNTgsNDY3XSwicmdiIjpbNjAsNzAsNzRdLCJuYW1lIjoiQmFsbGUiLCJsYWJlbCI6IkJhbGxlIDAuOTIifV0= | None | None |
    | cube01.jpeg | None | W3siY2xhc3MiOjMsImNvbmYiOjk1LCJjb2xvciI6NiwiYXoiOjI1LCJlbCI6MzU0LCJ4eXh5IjpbMjk3LDQ1MSwzNTksMzc2XSwicmdiIjpbNTUsNjgsNzJdLCJuYW1lIjoiQ3ViZSIsImxhYmVsIjoiQ3ViZSAwLjk1In1d | None |
    | star01.jpeg | None | None | W3siY2xhc3MiOjExLCJjb25mIjo4MiwiY29sb3IiOjcsImF6IjotNCwiZWwiOjMzOCwieHl4eSI6WzI5Miw0NDksMzQ4LDM5NV0sInJnYiI6WzAsNDgsMTY4XSwibmFtZSI6IkV0b2lsZSIsImxhYmVsIjoiRXRvaWxlIDAuODIifV0= |
    # | ball01.jpeg | '[{"class":1,"conf":92,"color":6,"az":15,"el":188,"xyxy":[292,535,358,467],"rgb":[60,70,74],"name":"Ball","label":"Balle 0.92"}]' | None | None |
    # | cube01.jpeg | None | '[{"class":3,"conf":95,"color":6,"az":25,"el":354,"xyxy":[297,451,359,376],"rgb":[55,68,72],"name":"Cube","label":"Cube 0.95"}]' | None |
    # | star01.jpeg | None | None | '[{"class":11,"conf":82,"color":7,"az":-4,"el":338,"xyxy":[292,449,348,395],"rgb":[0,48,168],"name":"Etoile","label":"Etoile 0.82"}]' |
