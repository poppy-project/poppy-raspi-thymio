# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os


extensions = [
    "autoapi.extension",
    "myst_nb",
    "sphinx.ext.coverage",
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.ifconfig',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    "sphinx_autodoc_typehints",
    "sphinxcontrib.restbuilder",
]

master_doc = 'index'
project = 'poppy-raspi-thymio'
year = '2024-2025'
author = 'David James Sherman'
copyright = '{0}, {1}'.format(year, author)
version = release = '0.2.1'

highlight_language = "none"

autoapi_type = 'python'
autoapi_dirs = ['../src']

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://gitlab.inria.fr/sherman/poppy-raspi-thymio/issues/%s', '#'),
    'pr': ('https://gitlab.inria.fr/sherman/poppy-raspi-thymio/pull/%s', 'PR #'),
}
# on_rtd is whether we are on readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only set the theme if we're building docs locally
    html_theme = 'sphinx_rtd_theme'

html_use_smartypants = True
html_last_updated_fmt = '%Y-%m-%d'
html_split_index = False
html_sidebars = {
   '**': ['searchbox.html', 'globaltoc.html', 'sourcelink.html'],
}
html_short_title = '%s-%s' % (project, version)

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False

autodoc_typehints = "both"

# Jupyter notebooks are saved with their outputs, so don't execute them
nb_execution_mode = "off"
