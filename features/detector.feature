Feature: Detector
  Continuously capture an image and detect objects.

  Scenario Outline: Initialize detector
    Given a camera
    And a YOLO detector
    And a Thymio
    And a frame directory
    When Initialize
    Then have thread
    And have expected attributes
