# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- Signal class tests
# :Created:    ven 25 dic 2015 01:51:16 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

import asyncio

import pytest
from metapensiero.signal import Signal
from metapensiero.signal import SignalAndHandlerInitMeta, handler

def test_01_signal_with_functions():
    signal = Signal()
    called1 = False
    called2 = False

    def handler1(arg, kw):
        nonlocal called1
        called1 = (arg, kw)

    def handler2(arg, kw):
        nonlocal called2
        called2 = (arg, kw)

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    assert called1 == (1, 'a')
    assert called2 == (1, 'a')

@pytest.mark.asyncio
@asyncio.coroutine
def test_02_signal_with_async_functions(events):
    signal = Signal()
    called1 = False
    called2 = False
    events.define('h1', 'h2')

    @asyncio.coroutine
    def handler1(arg, kw):
        nonlocal called1
        called1 = (arg, kw)
        events.h1.set()

    @asyncio.coroutine
    def handler2(arg, kw):
        nonlocal called2
        called2 = (arg, kw)
        events.h2.set()

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    yield from events.wait()
    assert called1 == (1, 'a')
    assert called2 == (1, 'a')

@pytest.mark.asyncio
@asyncio.coroutine
def test_03_signal_with_mixed_functions(events):
    signal = Signal()
    called1 = False
    called2 = False
    events.define('h1')

    @asyncio.coroutine
    def handler1(arg, kw):
        nonlocal called1
        called1 = (arg, kw)
        events.h1.set()

    def handler2(arg, kw):
        nonlocal called2
        called2 = (arg, kw)

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    assert called2 == (1, 'a')
    yield from events.wait()
    assert called1 == (1, 'a')

@pytest.mark.asyncio
@asyncio.coroutine
def test_04_signal_with_methods(events):
    signal = Signal()
    called2 = False

    class A:
        def __init__(self, name):
            self.ev = events[name]

        called = False

        @asyncio.coroutine
        def handler(self, arg, kw):
            self.called = (arg, kw)
            self.ev.set()

    a1 = A('a1')
    a2 = A('a2')

    signal.connect(a1.handler)
    signal.connect(a2.handler)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    yield from events.wait()
    assert a1.called == (1, 'a')
    assert a2.called == (1, 'a')

@pytest.mark.asyncio
@asyncio.coroutine
def test_05_class_defined_signal(events):
    class A:

        # the name here is needed for classes that don't explicitly support
        # signals
        click = Signal('click')

        def __init__(self, name):
            self.called = False
            self.click.connect(self.onclick)
            self.on_click_ev = events[name]

        @asyncio.coroutine
        def onclick(self, arg, kw):
            self.called = (arg, kw)
            self.on_click_ev.set()

    called1 = False

    @asyncio.coroutine
    def handler1(arg, kw):
        nonlocal called1
        called1 = (arg, kw)
        events.h1.set()

    a1 = A('a1')
    a2 = A('a2')
    events.define('h1')

    assert a1.called == False
    assert a2.called == False

    assert isinstance(a1.click, Signal.InstanceProxy)

    a1.click.connect(handler1)
    assert len(a1.click.subscribers) == 2
    assert len(a2.click.subscribers) == 1

    a1.click.notify(1, kw='a')
    yield from events.wait(events.a2)
    assert a1.called == (1, 'a')

    assert called1 == (1, 'a')
    assert a2.called == False

    a2.click.notify(2, kw='b')

    yield from events.wait()

    assert a1.called == (1, 'a')
    assert called1 == (1, 'a')
    assert a2.called == (2, 'b')


def test_signal_06_init_mclass():
    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal()

    assert A.click.name == 'click'

@pytest.mark.asyncio
@asyncio.coroutine
def test_07_class_defined_signal_with_decorator_named(events):
    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal()

        def __init__(self, name):
            self.called = False
            self.a_ev = events['a_' + name]

        @handler('click')
        @asyncio.coroutine
        def onclick(self, arg, kw):
            self.called = (arg, kw)
            self.a_ev.set()
            return 1

    a1 = A('a1')

    assert a1.called == False

    assert isinstance(a1.click, Signal.InstanceProxy)

    assert len(a1.click.subscribers) == 0

    res = a1.click.notify(1, kw='a')

    yield from events.a_a1.wait()
    assert len(res) == 1
    assert a1.called == (1, 'a')

    # a sublcass, inherits and adds an handler

    class B(A):

        def __init__(self, name):
            super().__init__(name)
            self.calledb = False
            self.b_ev = events['b_' + name]

        @handler('click')
        @asyncio.coroutine
        def another_click_handler(self, arg, kw):
            self.calledb = (arg, kw)
            self.b_ev.set()
            return 2

    b1 = B('b1')
    a2 = A('a2')

    assert b1.called == False
    assert b1.calledb == False

    res = a1.click.notify(1, kw='a')
    events.a_a1.clear()
    yield from events.a_a1.wait()
    assert len(res) == 1

    assert b1.called == False
    assert b1.calledb == False

    res = b1.click.notify(2, kw='b')
    yield from events.b_b1.wait()
    yield from events.a_b1.wait()

    #assert len(res) == 2

    assert b1.called == (2, 'b')
    assert b1.calledb == (2, 'b')
    assert a1.called == (1, 'a')
    # another subclass reimplents an handler


    class C(B):

        @handler('click')
        @asyncio.coroutine
        def onclick(self, arg, kw):
            self.called = (arg, kw)
            self.a_ev.set()
            return 3

    c1 = C('c1')

    assert c1.called == False
    assert c1.calledb == False

    res = c1.click.notify(3, kw='c')
    yield from events.a_c1.wait()
    yield from events.b_c1.wait()

    #assert len(res) == 2

    assert c1.called == (3, 'c')
    assert c1.calledb == (3, 'c')

    assert b1.called == (2, 'b')
    assert b1.calledb == (2, 'b')
    assert a1.called == (1, 'a')
