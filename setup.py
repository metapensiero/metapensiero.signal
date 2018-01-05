# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- A event framework that is asyncio aware
# :Created:   dom 09 ago 2015 12:57:35 CEST
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2015 Alberto Berti
#

import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.rst'), encoding='utf-8') as f:
    CHANGES = f.read()
with open(os.path.join(here, 'version.txt'), encoding='utf-8') as f:
    VERSION = f.read().strip()

setup(
    name="metapensiero.signal",
    version=VERSION,
    url="https://github.com/azazel75/metapensiero.signal",

    description="An asyncio aware event framework",
    long_description=README + '\n\n' + CHANGES,

    author="Alberto Berti",
    author_email="alberto@metapensiero.it",

    license="GPLv3+",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        ],
    keywords='signal event asyncio framework',

    packages=['metapensiero.' + pkg
              for pkg in find_packages('src/metapensiero')],
    package_dir={'': 'src'},
    namespace_packages=['metapensiero'],
    install_requires=[
        'setuptools>=36.7.2',
        'weakreflist>=0.4',
    ],
    extras_require={
        'dev': [
            'metapensiero.tool.bump_version',
        ],
        'doc': [
            'sphinx'
        ],
        'test': [
            'pytest',
            'pytest-asyncio',
            'pytest-cov',
            'sphinx',
        ]
    },
    setup_requires=['pytest-runner'],
    tests_require=['metapensiero.signal[test]'],
)
