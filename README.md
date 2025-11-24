# Overview

Raspberry Pi—Thymio Vision

This package provides computer vision and human decision inputs to a Thymio-II mobile robot.

- **Computer vision** (module `poppy.raspi_thymio`) uses a pre-trained YOLO8 NCNN model to detect objects, roads, and road signs. Raw and consensus detection events are sent to the message queue. Every clock tick, a composite image with detection boxes overlaid on the raw camera frame is written to a file.
- **Human decisions** (module `poppy.raspi_thymio.webui`) are detected using a Web interface, that provides:
	- An embedded image with the decorated camera frame.
	- Buttons to choose between robot behaviors.
	- A virtual remote control mimicking the Thymio IR remote.

These modules communicate between themselves using the ZeroMQ messaging library, and with the Thymio using the AESL protocol.

## Prerequisites:

This package is tailored for a Raspberry Pi 3–5 with a wide-angle camera, connected to a Thymio II by a USB cable. The Raspberry Pi must run the [Thymio Device Manager](https://github.com/Mobsya/aseba/tree/master/aseba/thymio-device-manager) as a separate service.

## Running on Raspberry Pi

Three _systemd_ services are typically run to use this software:

**lucia-detector.service**

```
[Unit]
Description=UCIA detector
After=network-online.target

StartLimitIntervalSec=500
StartLimitBurst=15

[Service]
Restart=on-failure
RestartSec=12s
ExecStart=bash -c "source /home/ucia/UCIA/vision/bin/activate && cd /home/ucia/UCIA/UCIA_ObjectDetection && /home/ucia/UCIA/vision/bin/poppy-raspi-thymio-detector --loglevel=INFO"

[Install]
WantedBy=multi-user.target
```

**ucia-webui.service**

```
[Unit]
Description=UCIA webui
After=network-online.target ucia-detector.service

StartLimitIntervalSec=500
StartLimitBurst=15

[Service]
Restart=on-failure
RestartSec=5s
ExecStart=bash -c "source /home/ucia/UCIA/vision/bin/activate && poppy-raspi-thymio-webui run --host 0.0.0.0 --port 5000"

[Install]
WantedBy=multi-user.target
```

**thymio-device-manager.service**

```
[Unit]
Description=Thymio Device Manager
After=network-online.target

StartLimitIntervalSec=500
StartLimitBurst=15

[Service]
Restart=on-failure
RestartSec=5s
ExecStart=/usr/local/bin/thymio-device-manager --password=UCIA --allow-remote-connections --log info

[Install]
WantedBy=multi-user.target
```

## Build and Install

```sh
pip install .
```

To use a live development environment, run

```sh
tox run -e dev
source .tox/dev/bin/activate
```


## Documentation

 https://pypi.org/project/poppy_raspi_thymio/


## Development

This project uses [Tox](https://tox.wiki/) for testing and [Hatch](https://hatch.pypa.io/) for packaging. 
To run the all tests run:

```sh
tox
```

Note, to combine the coverage data from all the tox environments, set
environment variable `PYTEST_ADDOPTS=--cov-append`.

To run Sonarqube analyses:

```sh
tox run -e sonar
```


# Version

poppy_raspi_thymio version v0.3.6

Free software: GPLv3+
