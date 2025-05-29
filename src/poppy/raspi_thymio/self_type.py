# -*- coding: utf-8 -*-

"""
Define Self type, depending on Python version.
"""

import sys

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self  # noqa: F401
