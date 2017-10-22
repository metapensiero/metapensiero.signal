# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- utilities
# :Created:   sab 21 ott 2017 12:25:42 CEST
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright © 2015, 2016, 2017 Alberto Berti
#

from collections.abc import Awaitable
import asyncio
import inspect


class MultipleResults(Awaitable):
    """An utility class containing multiple results, either *synchronous* or
    *asynchronous*."""

    results = None
    done = False
    has_async = False

    def __init__(self, iterable=None, *, concurrent=False, owner=None):
        self.owner = owner
        self._concurrent = concurrent
        self._results = list(iterable)
        self._coro_ixs = tuple(ix for ix, e in enumerate(self._results)
                               if inspect.isawaitable(e))
        if self._coro_ixs:
            self.has_async = True
        else:
            self.results = tuple(self._results)
            self.done = True
            self.has_async = False

    def __await__(self):
        task = self._completion_task(
            map(self._results.__getitem__, self._coro_ixs),
            concurrent=self._concurrent)
        return task.__await__()

    async def _completion_task(self, coro_iter=None, concurrent=False):
        if not self.done:
            if concurrent:
                results = await asyncio.gather(*coro_iter)
                for ix, res in zip(self._coro_ixs, results):
                    self._results[ix] = res
            else:
                for ix, coro in zip(self._coro_ixs, coro_iter):
                    res = await coro
                    self._results[ix] = res
        self.results = tuple(self._results)
        self.done = True
        return self.results


class TokenClass:
    """A token class whose instances always generate a ``False`` bool."""

    def __bool__(self):
        return False

NoResult = TokenClass()
"""A value that is returned by a callable when there's no return value and
when ``None`` can be considered a value."""
