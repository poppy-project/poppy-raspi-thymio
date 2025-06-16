# Overview

Raspberry Pi—Thymio Vision

  - Free software: GPLv3+


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

 https://sherman.gitlabpages.inria.fr/poppy_raspi_thymio/


## Development

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

poppy_raspi_thymio version v0.3.4
