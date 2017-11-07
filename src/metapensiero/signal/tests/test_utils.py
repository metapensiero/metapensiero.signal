# -*- coding: utf-8 -*-
# :Project: metapensiero.signal -- Signal class tests
# :Created: lun 06 nov 2017 00:08:45 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

import asyncio

import pytest

from metapensiero.signal.utils import MultipleResults

@pytest.mark.asyncio
async def test_multiple_and_ensure_future():

    async def handler():
        return "hello"

    mr = MultipleResults({handler()})
    task = asyncio.ensure_future(mr)
    res = await task
    assert res == ("hello", )
