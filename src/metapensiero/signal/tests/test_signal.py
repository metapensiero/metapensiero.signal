# -*- coding: utf-8 -*-
# :Project: metapensiero.signal -- Signal class tests
# :Created: ven 25 dic 2015 01:51:16 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

import asyncio

import pytest

from metapensiero.signal import handler, Signal, SignalAndHandlerInitMeta
from metapensiero.signal.core import InstanceProxy


def test_01_signal_with_functions(events):
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

    res = signal.notify(1, kw='a')
    events.loop.run_until_complete(res)
    assert c['called1'] == (1, 'a')
    assert c['called2'] == (1, 'a')


def test_02_signal_with_async_functions(events):
    signal = Signal()
    c = dict(called1=False, called2=False)
    events.define('h1', 'h2')

    async def handler1(arg, kw):
        c['called1'] = (arg, kw)
        events.h1.set()

    async def handler2(arg, kw):
        c['called2'] = (arg, kw)
        events.h2.set()

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    res = signal.notify(1, kw='a')

    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.wait())
    assert c['called1'] == (1, 'a')
    assert c['called2'] == (1, 'a')


def test_03_signal_with_mixed_functions(events):
    signal = Signal()
    c = dict(called1=False, called2=False)
    events.define('h1')

    async def handler1(arg, kw):
        c['called1'] = (arg, kw)
        events.h1.set()

    def handler2(arg, kw):
        c['called2'] = (arg, kw)

    signal.connect(handler1)
    signal.connect(handler2)

    assert len(signal.subscribers) == 2

    res = signal.notify(1, kw='a')
    events.loop.run_until_complete(res)
    assert c['called2'] == (1, 'a')
    events.loop.run_until_complete(events.wait())
    assert c['called1'] == (1, 'a')


def test_04_signal_with_methods(events):
    signal = Signal()

    class A(object):
        def __init__(self, name):
            self.ev = events[name]

        called = False

        async def handler(self, arg, kw):
            self.called = (arg, kw)
            self.ev.set()

    a1 = A('a1')
    a2 = A('a2')

    signal.connect(a1.handler)
    signal.connect(a2.handler)

    assert len(signal.subscribers) == 2

    res = signal.notify(1, kw='a')
    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.wait())

    assert a1.called == (1, 'a')
    assert a2.called == (1, 'a')


def test_05_class_defined_signal(events):
    class A(object):

        # the name here is needed for classes that don't explicitly support
        # signals
        click = Signal(name='click')

        def __init__(self, name):
            self.called = False
            self.click.connect(self.onclick)
            self.on_click_ev = events[name]

        async def onclick(self, arg, kw):
            self.called = (arg, kw)
            self.on_click_ev.set()

    c = dict(called1=False)

    async def handler1(arg, kw):
        c['called1'] = (arg, kw)
        events.h1.set()

    a1 = A('a1')
    a2 = A('a2')
    events.define('h1')

    assert a1.called is False
    assert a2.called is False

    assert isinstance(a1.click, InstanceProxy)

    a1.click.connect(handler1)
    assert len(a1.click.subscribers) == 2
    assert len(a2.click.subscribers) == 1

    res = a1.click.notify(1, kw='a')
    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.wait(events.a2))

    assert a1.called == (1, 'a')

    assert c['called1'] == (1, 'a')
    assert a2.called is False

    res = a2.click.notify(2, kw='b')
    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.wait())

    assert a1.called == (1, 'a')
    assert c['called1'] == (1, 'a')
    assert a2.called == (2, 'b')


def test_06_signal_init_mclass():
    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal()

    assert A.click.name == 'click'


def test_07_class_defined_signal_with_decorator_named(events):
    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal()

        def __init__(self, name):
            self.called = False
            self.a_ev = events['a_' + name]

        @handler('click')
        async def onclick(self, arg, kw):
            self.called = (arg, kw)
            self.a_ev.set()
            return 1

    a1 = A('a1')

    assert a1.called is False

    assert isinstance(a1.click, InstanceProxy)

    assert len(a1.click.subscribers) == 0

    res = a1.click.notify(1, kw='a')

    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.a_a1.wait())
    res = res.results

    assert len(res) == 1
    assert a1.called == (1, 'a')

    # a sublcass, inherits and adds an handler

    class B(A):

        def __init__(self, name):
            super(B, self).__init__(name)
            self.calledb = False
            self.b_ev = events['b_' + name]

        @handler('click')
        async def another_click_handler(self, arg, kw):
            self.calledb = (arg, kw)
            self.b_ev.set()
            return 2

    b1 = B('b1')

    assert b1.called is False
    assert b1.calledb is False

    res = a1.click.notify(1, kw='a')
    events.a_a1.clear()
    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.a_a1.wait())
    res = res.results

    assert len(res) == 1

    assert b1.called is False
    assert b1.calledb is False

    res = b1.click.notify(2, kw='b')
    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.a_b1.wait())
    events.loop.run_until_complete(events.b_b1.wait())
    res = res.results

    # assert len(res) == 2

    assert b1.called == (2, 'b')
    assert b1.calledb == (2, 'b')
    assert a1.called == (1, 'a')
    # another subclass reimplents an handler

    class C(B):

        @handler('click')
        async def onclick(self, arg, kw):
            self.called = (arg, kw)
            self.a_ev.set()
            return 3

    c1 = C('c1')

    assert c1.called is False
    assert c1.calledb is False

    res = c1.click.notify(3, kw='c')
    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.a_c1.wait())
    events.loop.run_until_complete(events.b_c1.wait())
    res = res.results

    assert c1.called == (3, 'c')
    assert c1.calledb == (3, 'c')

    assert b1.called == (2, 'b')
    assert b1.calledb == (2, 'b')
    assert a1.called == (1, 'a')


def test_08_class_defined_signal_with_decorator_mixed(events):

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal()

        def __init__(self):
            self.called = False
            self.called2 = False

        @handler('click')
        def onclick(self, arg, kw):
            self.called = (arg, kw)

        @handler('click')
        async def click2(self, arg, kw):
            self.called2 = (arg, kw)

    a1 = A()

    assert a1.called is False
    assert a1.called2 is False

    res = a1.click.notify(1, kw='a')
    assert a1.called == (1, 'a')
    assert a1.called2 is False

    events.loop.run_until_complete(res)

    assert a1.called2 == (1, 'a')


def test_09_external_signaller(events):

    import asyncio
    from metapensiero.signal import ExternalSignaller

    c = dict(publish_called=False, register_called=False)

    class MyExternalSignaller(object):

        def publish_signal(self, signal, instance, loop, args, kwargs):
            c['publish_called'] = (signal, instance, loop, args, kwargs)

        def register_signal(self, signal, name):
            c['register_called'] = (signal, name)

    ExternalSignaller.register(MyExternalSignaller)

    assert c['register_called'] is False
    assert c['publish_called'] is False

    signaller = MyExternalSignaller()
    signal = Signal(name='foo', external=signaller)

    assert c['register_called'] == (signal, 'foo')
    assert c['publish_called'] is False

    res = signal.notify('foo', zoo='bar')
    events.loop.run_until_complete(res)

    assert c['publish_called'] == (signal, None, asyncio.get_event_loop(),
                                   ('foo',), {'zoo': 'bar'})
    assert c['register_called'] == (signal, 'foo')


def test_10_external_signaller_async(events):

    from metapensiero.signal import ExternalSignaller

    c = dict(publish_called=False, register_called=False)

    class MyExternalSignaller(object):

        async def publish_signal(self, signal, instance, loop, args, kwargs):
            c['publish_called'] = (signal, instance, loop, args, kwargs)
            events.publish.set()

        def register_signal(self, signal, name):
            c['register_called'] = (signal, name)

    ExternalSignaller.register(MyExternalSignaller)

    assert c['register_called'] is False
    assert c['publish_called'] is False

    signaller = MyExternalSignaller()
    signal = Signal(name='foo', external=signaller)

    assert c['register_called'] == (signal, 'foo')
    assert c['publish_called'] is False

    res = signal.notify('foo', zoo='bar')
    events.loop.run_until_complete(res)
    events.loop.run_until_complete(events.publish.wait())

    assert c['publish_called'] == (signal, None, asyncio.get_event_loop(),
                                   ('foo',), {'zoo': 'bar'})
    assert c['register_called'] == (signal, 'foo')


def test_11_notify_wrapper(events):

    c = dict(called=0, wrap_args=None, handler_called=0, handler_args=None)

    @Signal
    def asignal(subscribers, notify, *args, **kwargs):
        c['called'] += 1
        c['wrap_args'] = (args, kwargs)
        assert len(subscribers) == 1
        notify('foo', k=2)
        return 'foo'

    def handler(*args, **kwargs):
        c['handler_called'] += 1
        c['handler_args'] = (args, kwargs)

    asignal.connect(handler)
    res = asignal.notify('bar', k=1)

    assert res == 'foo'
    assert c['called'] == 1
    assert c['wrap_args'] == (('bar',), {'k': 1})
    assert c['handler_called'] == 1
    assert c['handler_args'] == (('foo',), {'k': 2})

    c = dict(called=0, wrap_args=None, handler_called=0, handler_args=None,
             handler2_called=0, handler2_args=None)

    class A(metaclass=SignalAndHandlerInitMeta):

        @Signal
        def click(self, subscribers, notify, *args, **kwargs):
            c['called'] += 1
            c['wrap_args'] = (args, kwargs)
            assert len(subscribers) == 2
            assert isinstance(self, A)
            notify('foo', k=2)
            return 'foo'

        @handler('click')
        def handler(self, *args, **kwargs):
            c['handler_called'] += 1
            c['handler_args'] = (args, kwargs)

    a = A()

    def handler2(*args, **kwargs):
        c['handler2_called'] += 1
        c['handler2_args'] = (args, kwargs)

    a.click.connect(handler2)
    res = a.click.notify('bar', k=1)
    assert res == 'foo'
    assert c['called'] == 1
    assert c['wrap_args'] == (('bar',), {'k': 1})
    assert c['handler_called'] == 1
    assert c['handler_args'] == (('foo',), {'k': 2})
    assert c['handler2_called'] == 1
    assert c['handler2_args'] == (('foo',), {'k': 2})


def test_12_connect_wrapper(events):

    c = dict(called=0, connect_handler=None, handler_called=0,
             handler_args=None)

    asignal = Signal()

    @asignal.on_connect
    def asignal(handler, subscribers, connect, notify):
        c['called'] += 1
        c['connect_handler'] = handler
        assert len(subscribers) == 0
        connect(handler)
        return 'foo'

    def handler(*args, **kwargs):
        c['handler_called'] += 1
        c['handler_args'] = (args, kwargs)

    res = asignal.connect(handler)
    res2 = asignal.notify('bar', k=1)
    events.loop.run_until_complete(res2)

    assert res == 'foo'
    assert c['called'] == 1
    assert c['connect_handler'] == handler
    assert c['handler_called'] == 1
    assert c['handler_args'] == (('bar',), {'k': 1})

    c = dict(called=0, connect_handler=None, handler_called=0,
             handler_args=None, handler2_called=0, handler2_args=None)

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal()

        @click.on_connect
        def click(self, handler, subscribers, connect, notify):
            c['called'] += 1
            c['connect_handler'] = handler
            assert len(subscribers) == 0
            connect(handler)
            return 'foo'

        @handler('click')
        def handler(self, *args, **kwargs):
            c['handler_called'] += 1
            c['handler_args'] = (args, kwargs)

    a = A()

    def handler2(*args, **kwargs):
        c['handler2_called'] += 1
        c['handler2_args'] = (args, kwargs)

    res = a.click.connect(handler2)
    res2 = a.click.notify('bar', k=1)
    events.loop.run_until_complete(res2)

    assert res == 'foo'
    assert c['called'] == 1
    assert c['handler_called'] == 1
    assert c['connect_handler'] == handler2
    assert c['handler_args'] == (('bar',), {'k': 1})
    assert c['handler2_called'] == 1
    assert c['handler2_args'] == (('bar',), {'k': 1})


def test_13_disconnect_wrapper():

    c = dict(called=0, disconnect_handler=None)

    asignal = Signal()

    @asignal.on_disconnect
    def asignal(handler, subscribers, disconnect, notify):
        c['called'] += 1
        c['disconnect_handler'] = handler
        assert len(subscribers) == 1
        disconnect(handler)
        return 'foo'

    def handler(*args, **kwargs):
        pass

    asignal.connect(handler)
    res = asignal.disconnect(handler)

    assert res == 'foo'
    assert c['called'] == 1
    assert c['disconnect_handler'] == handler
    assert len(asignal.subscribers) == 0

    c = dict(called=0, disconnect_handler=None)

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal()

        @click.on_disconnect
        def click(self, handler, subscribers, disconnect, notify):
            c['called'] += 1
            c['disconnect_handler'] = handler
            assert len(subscribers) == 1
            disconnect(handler)
            return 'foo'

        @handler('click')
        def handler(self, *args, **kwargs):
            pass
    a = A()

    def handler2(*args, **kwargs):
        pass

    a.click.connect(handler2)
    res = a.click.disconnect(handler2)
    assert res == 'foo'
    assert c['called'] == 1
    assert c['disconnect_handler'] == handler2
    # class-level handlers are excluded
    assert len(a.click.subscribers) == 0


def test_14_nonexistent_signal():

    from metapensiero.signal import SignalError

    with pytest.raises(SignalError):
        class A(metaclass=SignalAndHandlerInitMeta):

            @Signal
            def click(self, subscribers, notify, *args, **kwargs):
                notify('foo', k=2)

            @handler('dblclick')
            def handler(self, *args, **kwargs):
                pass


def test_15_external_signaller_filters_handlers():

    from metapensiero.signal import ExternalSignallerAndHandler

    class MyExternalSignaller(object):

        def publish_signal(self, signal, instance, loop, args, kwargs):
            pass

        def register_signal(self, signal, name):
            pass

        def register_class(self, cls, bases, namespace, signals, handlers):
            ext_handlers = {}
            for hname, sig_name in handlers.items():
                if sig_name not in signals and sig_name.startswith('myext'):
                    ext_handlers[hname] = sig_name
            for ext_signame in set(ext_handlers.values()):
                signals[ext_signame] = None
            cls._ext_handlers = ext_handlers

    ExternalSignallerAndHandler.register(MyExternalSignaller)
    signaller = MyExternalSignaller()

    MySignalMeta = SignalAndHandlerInitMeta.with_external(signaller,
                                                          'MySignalMeta')

    class A(metaclass=MySignalMeta):

        click = Signal()

        @handler('click')
        def handler1(self, *args, **kwargs):
            pass

        @handler('myext.dbclick')
        def handler2(self, *args, **kwargs):
            pass

    assert A._ext_handlers == {'handler2': 'myext.dbclick'}
    assert A._signal_handlers == {'handler1': 'click',
                                  'handler2': 'myext.dbclick'}
    assert A._signals == {'click': A.click, 'myext.dbclick': None}


def test_16_dot_handlers(events):

    class A(metaclass=SignalAndHandlerInitMeta):

        me = Signal()
        me.name = '.'

        def __init__(self):
            self.called = False

        @handler('.')
        def onme(self, arg, kw):
            self.called = (arg, kw)

    a1 = A()

    assert a1.called is False

    res = a1.me.notify(1, kw='a')

    assert a1.called == (1, 'a')

    events.loop.run_until_complete(res)


@pytest.mark.asyncio
async def test_17_handlers_sorting():

    called = []

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal(sort_mode=Signal.SORT_MODE.BOTTOMUP)

        @handler('click')
        def z(self):
            called.append('z')


    class B(A):

        @handler('click')
        def a(self):
            called.append('a')

    b = B()

    await b.click.notify()

    assert len(called) == 2
    assert called.index('z') == 0
    assert called.index('a') == 1


    called = []

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal(sort_mode=Signal.SORT_MODE.TOPDOWN)

        @handler('click')
        def z(self):
            called.append('z')


    class B(A):

        @handler('click')
        def a(self):
            called.append('a')

    b = B()

    await b.click.notify()

    assert len(called) == 2
    assert called.index('z') == 1
    assert called.index('a') == 0


    # bottom_up
    called = []

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal(sort_mode=Signal.SORT_MODE.BOTTOMUP)

        @handler('click')
        def z(self):
            called.append('z')

    class B(A):

        @handler('click')
        def a(self):
            called.append('a')

    class Cee(B):

        @handler('click', begin=True)
        def b(self):
            called.append('b')

    c = Cee()

    await c.click.notify()

    assert len(called) == 3
    assert called.index('z') == 1
    assert called.index('a') == 2
    assert called.index('b') == 0

    called = []

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal(sort_mode=Signal.SORT_MODE.BOTTOMUP)

        @handler('click')
        def z(self):
            called.append('z')

    class B(A):

        @handler('click', end=True)
        def a(self):
            called.append('a')

    class Cee(B):

        @handler('click')
        def b(self):
            called.append('b')

    c = Cee()

    await c.click.notify()

    assert len(called) == 3
    assert called.index('z') == 0
    assert called.index('a') == 2
    assert called.index('b') == 1

    # topdown
    called = []

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal(sort_mode=Signal.SORT_MODE.TOPDOWN)

        @handler('click')
        def z(self):
            called.append('z')

    class B(A):

        @handler('click')
        def a(self):
            called.append('a')

    class Cee(B):

        @handler('click', begin=True)
        def b(self):
            called.append('b')

    c = Cee()

    await c.click.notify()

    assert len(called) == 3
    assert called.index('z') == 2
    assert called.index('a') == 1
    assert called.index('b') == 0

    called = []

    class A(metaclass=SignalAndHandlerInitMeta):

        click = Signal(sort_mode=Signal.SORT_MODE.TOPDOWN)

        @handler('click')
        def z(self):
            called.append('z')

    class B(A):

        @handler('click', end=True)
        def a(self):
            called.append('a')

    class Cee(B):

        @handler('click')
        def b(self):
            called.append('b')

    c = Cee()

    await c.click.notify()

    assert len(called) == 3
    assert called.index('z') == 1
    assert called.index('a') == 2
    assert called.index('b') == 0


def test_18_notify_prepared_dont_signal_external():

    c = dict(publish_called=False, handler_called=False)

    from metapensiero.signal import ExternalSignallerAndHandler

    class MyExternalSignaller(object):

        def publish_signal(self, signal, instance, loop, args, kwargs):
            c['publish_called'] = True

        def register_signal(self, signal, name):
            pass

        def register_class(self, cls, bases, namespace, signals, handlers):
            pass

    ExternalSignallerAndHandler.register(MyExternalSignaller)
    signaller = MyExternalSignaller()

    MySignalMeta = SignalAndHandlerInitMeta.with_external(signaller,
                                                          'MySignalMeta')

    class A(metaclass=MySignalMeta):

        click = Signal()

        @handler('click')
        def handler1(self, *args, **kwargs):
            c['handler_called'] = True


    a = A()

    a.click.notify_prepared(notify_external=False)

    assert c.get('publish_called') is False
    assert c.get('handler_called') is True

    c['handler_called'] = False

    a.click.notify_prepared(notify_external=True)

    assert c.get('publish_called') is True
    assert c.get('handler_called') is True
