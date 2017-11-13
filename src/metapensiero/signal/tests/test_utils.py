# -*- coding: utf-8 -*-
# :Project: metapensiero.signal -- Signal class tests
# :Created: lun 06 nov 2017 00:08:45 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

import asyncio

import pytest

from metapensiero.signal.utils import Executor, ExecutionError, MultipleResults


# All test coroutines will be treated as marked
pytestmark = pytest.mark.asyncio()


async def test_multiple_and_ensure_future():

    async def handler():
        return "hello"

    mr = MultipleResults({handler()})
    task = asyncio.ensure_future(mr)
    res = await task
    assert res == ("hello", )


async def test_executor_signature():

    d = dict(sub_called=False, valid_called=False)

    def subscriber(arg1, *, arg2=None):
        d['sub_called'] = True
        return arg1, arg2

    def validator(arg1, *, arg2=None):
        d['valid_called'] = True
        return arg1 == 'foo'

    ex = Executor([subscriber], fvalidation=validator)

    mr = ex.run(arg1='foo')

    assert mr.done is True
    assert mr.results[0] == ('foo', None)
    assert d['sub_called'] is True
    assert d['valid_called'] is True

    d = dict(sub_called=False, valid_called=False)

    with pytest.raises(ExecutionError) as exc_info:
        mr = ex.run(arg3='bar')

    assert exc_info.match('validation.*failed')
    assert d['sub_called'] is False
    assert d['valid_called'] is False


    d = dict(sub_called=False, valid_called=False)

    with pytest.raises(ExecutionError) as exc_info:
        mr = ex.run(arg1='bar')

    assert exc_info.match('validation.*failed')
    assert d['sub_called'] is False
    assert d['valid_called'] is True
