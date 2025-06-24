# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.6] (2025-06-23)

  - Coureuse, Balayeuse: brisker acceleration
  - Coureuse, Balayeuse: better “look around” handling
  - Chasseuse: better searching (state 1)
  - poweroff: delay 10s to accomodate Raspberry Pi shutdown

## [0.3.5] (2025-06-17)

  - Improvements to behaviors
  - Balayeuse camera.detect set flag, slow down by anticipation
  - Fix arithmetic errors when slowing down (again)

## [0.3.4] (2025-06-16)

  - Added "reload Thymio" button, resends last program
  - Fix race condition when initializing camera
  - Fix arithmetic errors when slowing down

## [0.3.3] (2025-06-16)

  - Improvements to Web UI
  - Coureuse and Balayeuse deliberately look left and right when lost
  - Balayeuse is simplified, just Coureuse with sweeping
  - Chasseuse listens to GO and tries to chain hunting + fetching

## [0.3.2] (2025-06-13)

  - Module webui.aesl handles Aesl program metadata
  - Buttons use SVG images

## [0.3.1] (2025-06-11)

  - Chasseuse can look for multiple things and nests
  - Balayeuse tries to clean up
  - Best things must be below horizon
  - Web UI highlights last program chosen

## [0.3.0] (2025-06-10)

  - Service ucia-webui handles user interface
  - ZMQ for interprocess communication
  - Thymio remote control
  - Web UI imitates remote control
  - Web UI buttons to change programs
  - Fallback frames if no detector

## [0.2.2] (2025-05-15)

  - YOLO8 network V3 
  - Fourteen thing types
  - Removed Hough lane detection
  - Camera variables written directly
  - Multiple Aesl programs
  - Thing names in French

## [0.2.1] (2025-05-15)

  - Package poppy.raspi_thymio

## [0.2.0] (2025-02-05)

  - Initial
