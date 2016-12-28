# -*- coding: utf-8 -*-
# :Project: metapensiero.signal -- compatibility
# :Created: mer 28 dic 2016 00:33:01 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

import inspect
import sys

if sys.version_info[:2] >= (3, 4):
    import asyncio
    PY34 = sys.version_info[:2] == (3, 4)
    PY35 = sys.version_info[:2] > (3, 4)

    if PY34:
        def isawaitable(thing):
            return asyncio.iscoroutine(thing) or isinstance(thing, asyncio.Future)
    elif PY35:
        isawaitable = inspect.isawaitable
    else:
        def isawaitable(thing):
            return False
