# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- Signal class tests
# :Created:    ven 25 dic 2015 01:51:16 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

from __future__ import unicode_literals, absolute_import

import six

if six.PY3:
    import asyncio
else:
    asyncio = None

import pytest

from metapensiero.signal import Signal
from metapensiero.signal import SignalAndHandlerInitMeta, handler


def _coroutine(func):
    if six.PY3:
        return asyncio.coroutine(func)
    else:
        return func


def test_01_signal_with_functions():
    signal = Signal()
    c = dict(called1=False, called2=False)

    def handler1(arg, kw):
        # let python get the outer var here without using PY3 "nonlocal"
        c['called1'] = (arg, kw)

    def handler2(arg, kw):
        c['called2'] = (arg, kw)

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    assert c['called1'] == (1, 'a')
    assert c['called2'] == (1, 'a')

def test_02_signal_with_async_functions(events):
    signal = Signal()
    c = dict(called1=False, called2=False)
    if six.PY3:
        events.define('h1', 'h2')

    @_coroutine
    def handler1(arg, kw):
        c['called1'] = (arg, kw)
        if six.PY3:
            events.h1.set()

    @_coroutine
    def handler2(arg, kw):
        c['called2'] = (arg, kw)
        if six.PY3:
            events.h2.set()

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    if six.PY3:
        events.loop.run_until_complete(events.wait())
    assert c['called1'] == (1, 'a')
    assert c['called2'] == (1, 'a')

def test_03_signal_with_mixed_functions(events):
    signal = Signal()
    c = dict(called1=False, called2=False)
    if six.PY3:
        events.define('h1')

    @_coroutine
    def handler1(arg, kw):
        c['called1'] = (arg, kw)
        if six.PY3:
            events.h1.set()

    def handler2(arg, kw):
        c['called2'] = (arg, kw)

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    assert c['called2'] == (1, 'a')
    if six.PY3:
        events.loop.run_until_complete(events.wait())
    assert c['called1'] == (1, 'a')

def test_04_signal_with_methods(events):
    signal = Signal()

    class A(object):
        def __init__(self, name):
            if six.PY3:
                self.ev = events[name]

        called = False

        @_coroutine
        def handler(self, arg, kw):
            self.called = (arg, kw)
            if six.PY3:
                self.ev.set()

    a1 = A('a1')
    a2 = A('a2')

    signal.connect(a1.handler)
    signal.connect(a2.handler)

    assert len(signal.subscribers) == 2

    signal.notify(1, kw='a')
    if six.PY3:
        events.loop.run_until_complete(events.wait())
    assert a1.called == (1, 'a')
    assert a2.called == (1, 'a')

def test_05_class_defined_signal(events):
    class A(object):

        # the name here is needed for classes that don't explicitly support
        # signals
        click = Signal('click')

        def __init__(self, name):
            self.called = False
            self.click.connect(self.onclick)
            if six.PY3:
                self.on_click_ev = events[name]

        @_coroutine
        def onclick(self, arg, kw):
            self.called = (arg, kw)
            if six.PY3:
                self.on_click_ev.set()

    c = dict(called1=False)

    @_coroutine
    def handler1(arg, kw):
        c['called1'] = (arg, kw)
        if six.PY3:
            events.h1.set()

    a1 = A('a1')
    a2 = A('a2')
    if six.PY3:
        events.define('h1')

    assert a1.called == False
    assert a2.called == False

    assert isinstance(a1.click, Signal.InstanceProxy)

    a1.click.connect(handler1)
    assert len(a1.click.subscribers) == 2
    assert len(a2.click.subscribers) == 1

    a1.click.notify(1, kw='a')
    if six.PY3:
        events.loop.run_until_complete(events.wait(events.a2))
    assert a1.called == (1, 'a')

    assert c['called1'] == (1, 'a')
    assert a2.called == False

    a2.click.notify(2, kw='b')

    if six.PY3:
        events.loop.run_until_complete(events.wait())

    assert a1.called == (1, 'a')
    assert c['called1'] == (1, 'a')
    assert a2.called == (2, 'b')


def test_signal_06_init_mclass():
    @six.add_metaclass(SignalAndHandlerInitMeta)
    class A(object):

        click = Signal()

    assert A.click.name == 'click'

def test_07_class_defined_signal_with_decorator_named(events):
    @six.add_metaclass(SignalAndHandlerInitMeta)
    class A(object):

        click = Signal()

        def __init__(self, name):
            self.called = False
            if six.PY3:
                self.a_ev = events['a_' + name]

        @handler('click')
        @_coroutine
        def onclick(self, arg, kw):
            self.called = (arg, kw)
            if six.PY3:
                self.a_ev.set()
            return 1

    a1 = A('a1')

    assert a1.called == False

    assert isinstance(a1.click, Signal.InstanceProxy)

    assert len(a1.click.subscribers) == 0

    res = a1.click.notify(1, kw='a')

    if six.PY3:
        events.loop.run_until_complete(events.a_a1.wait())
    assert len(res) == 1
    assert a1.called == (1, 'a')

    # a sublcass, inherits and adds an handler

    class B(A):

        def __init__(self, name):
            super().__init__(name)
            self.calledb = False
            if six.PY3:
                self.b_ev = events['b_' + name]

        @handler('click')
        @_coroutine
        def another_click_handler(self, arg, kw):
            self.calledb = (arg, kw)
            if six.PY3:
                self.b_ev.set()
            return 2

    b1 = B('b1')

    assert b1.called == False
    assert b1.calledb == False

    res = a1.click.notify(1, kw='a')
    if six.PY3:
        events.a_a1.clear()
    if six.PY3:
        events.loop.run_until_complete(events.a_a1.wait())
    assert len(res) == 1

    assert b1.called == False
    assert b1.calledb == False

    res = b1.click.notify(2, kw='b')
    if six.PY3:
        events.loop.run_until_complete(events.b_b1.wait())
        events.loop.run_until_complete(events.a_b1.wait())

    #assert len(res) == 2

    assert b1.called == (2, 'b')
    assert b1.calledb == (2, 'b')
    assert a1.called == (1, 'a')
    # another subclass reimplents an handler


    class C(B):

        @handler('click')
        @_coroutine
        def onclick(self, arg, kw):
            self.called = (arg, kw)
            if six.PY3:
                self.a_ev.set()
            return 3

    c1 = C('c1')

    assert c1.called == False
    assert c1.calledb == False

    res = c1.click.notify(3, kw='c')
    if six.PY3:
        events.loop.run_until_complete(events.a_c1.wait())
        events.loop.run_until_complete(events.b_c1.wait())

    #assert len(res) == 2

    assert c1.called == (3, 'c')
    assert c1.calledb == (3, 'c')

    assert b1.called == (2, 'b')
    assert b1.calledb == (2, 'b')
    assert a1.called == (1, 'a')

def test_08_class_defined_signal_with_decorator_mixed(events):

    if six.PY3:
        from metapensiero.asyncio import transaction

    @six.add_metaclass(SignalAndHandlerInitMeta)
    class A(object):

        click = Signal()

        def __init__(self):
            self.called = False
            self.called2 = False

        @handler('click')
        def onclick(self, arg, kw):
            self.called = (arg, kw)

        @handler('click')
        @_coroutine
        def click2(self, arg, kw):
            self.called2 = (arg, kw)

    a1 = A()

    assert a1.called == False
    assert a1.called2 == False

    if six.PY3:
        trans = transaction.begin()
    a1.click.notify(1, kw='a')
    assert a1.called == (1, 'a')
    assert a1.called2 == False
    if six.PY3:
        events.loop.run_until_complete(trans.end())
    assert a1.called2 == (1, 'a')


def test_09_external_signaller():

    if six.PY3:
        import asyncio
    from metapensiero.signal import ExternalSignaller

    c = dict(publish_called=False, register_called=False)

    @ExternalSignaller.register
    class MyExternalSignaller(object):

        def publish(self, signal, instance, loop, args, kwargs):
            c['publish_called'] = (signal, instance, loop, args, kwargs)

        def register_signal(self, signal, name):
            c['register_called'] = (signal, name)

    assert c['register_called'] == False
    assert c['publish_called'] == False

    signaller = MyExternalSignaller()
    signal = Signal(name='foo', external=signaller)

    assert c['register_called'] == (signal, 'foo')
    assert c['publish_called'] == False

    signal.notify('foo', zoo='bar')
    if six.PY3:
        assert c['publish_called'] == (signal, None, asyncio.get_event_loop(), ('foo',), {'zoo': 'bar'})
    else:
        assert c['publish_called'] == (signal, None, None, ('foo',), {'zoo': 'bar'})
    assert c['register_called'] == (signal, 'foo')

def test_10_external_signaller_async(events):

    from metapensiero.signal import ExternalSignaller

    c = dict(publish_called=False, register_called=False)

    @ExternalSignaller.register
    class MyExternalSignaller(object):

        @_coroutine
        def publish(self, signal, instance, loop, args, kwargs):
            c['publish_called'] = (signal, instance, loop, args, kwargs)
            if six.PY3:
                events.publish.set()

        def register_signal(self, signal, name):
            c['register_called'] = (signal, name)

    assert c['register_called'] == False
    assert c['publish_called'] == False

    signaller = MyExternalSignaller()
    signal = Signal(name='foo', external=signaller)

    assert c['register_called'] == (signal, 'foo')
    assert c['publish_called'] == False

    signal.notify('foo', zoo='bar')
    assert c['publish_called'] == False
    if six.PY3:
        events.loop.run_until_complete(events.publish.wait())
        assert c['publish_called'] == (signal, None, asyncio.get_event_loop(), ('foo',), {'zoo': 'bar'})
    else:
        assert c['publish_called'] == (signal, None, None, ('foo',), {'zoo': 'bar'})
    assert c['register_called'] == (signal, 'foo')
