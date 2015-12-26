# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- fixtures
# :Created:    ven 25 dic 2015 02:05:42 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

import asyncio

import pytest

class EventFactory:
    """An helper class that helps creating asyncio.Event instances and waiting for
    them.
    """

    def __init__(self, loop=None):
        self.loop = loop
        self.events = set()

    def __getattr__(self, name):
        event = asyncio.Event(loop=self.loop)
        setattr(self, name, event)
        self.events.add(event)
        return event

    __getitem__ = __getattr__

    def wait(self, *exclude, timeout=None):
        exclude = set(exclude)
        return asyncio.wait(
            map(lambda e: e.wait(),
            self.events - exclude), timeout=timeout,
            loop=self.loop)

    def reset(self):
        for e in self.events:
            e.clear()

    def define(self, *names):
        for name in names:
            getattr(self, name)

    def wait_for(self, event, timeout=None):
        return asyncio.wait_for(event.wait(), timeout=timeout, loop=self.loop)

    TimeoutError = asyncio.TimeoutError


@pytest.fixture(scope='function')
def events(event_loop):
    return EventFactory(event_loop)
