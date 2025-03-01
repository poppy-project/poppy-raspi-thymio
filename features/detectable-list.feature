Feature: DetectableList
  List of detectable things.

  Scenario Outline: Merge thing lists
    Given a list with one thing <initial_spec>
    Given a new list with one thing <new_spec>
    When merge lists
    Then result is <expect_spec>

    Examples:
    # 1,10,30,9,2 is kind=1, xyxy=(10,20,20,10), color=(30,30,30), confidence=0.9, ttl=2
    | initial_spec | new_spec     | expect_spec             |
    | 1,10,30,9,2  | 1,10,30,9,3  | 1,10,30,9,3             |  # identical
    | 1,10,30,9,2  | 1,10,30,8,3  | 1,10,30,8,3             |  # identical except conf
    | 1,10,30,9,2  | 1,17,30,9,3  | 1,17,30,9,3             |  # same xyxy
    | 1,10,30,9,2  | 1,17,60,9,3  | 1,17,30,9,3             |  # same xyxy, color
    # | 1,10,30,9,2  | 2,17,30,9,3  | 1,10,30,9,1;1,17,30,9,3 |  # ≠ kind
    # | 1,10,30,9,2  | 1,25,30,9,3  | 1,10,30,9,1;0,25,30,9,3 |  # not same as xyxy
    # | 1,10,30,9,2  | 1,17,50,9,3  | 1,10,30,9,1;0,17,50,9,3 |  # not same as color
    # | 1,10,30,9,0  | 2,17,30,9,3  | 2,17,30,9,3             |  # ttl timeout
    # | 1,10,30,9,2;1,17,30,9,3  | 1,10,30,9,3  | 1,10,30,9,3;2,17,30,9,3  |
