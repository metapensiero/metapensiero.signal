.. -*- coding: utf-8 -*-
.. :Project:   metapensiero.signal -- An event framework that is asyncio aware
.. :Created:   dom 09 ago 2015 12:57:35 CEST
.. :Author:    Alberto Berti <alberto@metapensiero.it>
.. :License:   GNU General Public License version 3 or later
.. :Copyright: Copyright (C) 2015 Alberto Berti
..

=====================
 metapensiero.signal
=====================

 :author: Alberto Berti
 :contact: alberto@metapensiero.it
 :license: GNU General Public License version 3 or later

An event framework that is asyncio aware
========================================

.. contents::

Goal
----

This package implements a light event system that is able to deal with
both synchronous and asynchronous event handlers. It can be used as-is
or as member of a class.

If you use it on Python 2.7 you'll get just synchronous handlers
management, but there is a way to bind it to external event systems in
a generic way. Check out the ``external.py`` submodule and the tests
for more info.

Installation
------------

To install the package execute the following command::

  $ pip install metapensiero.signal

Usage
-----

Basic functionality
~~~~~~~~~~~~~~~~~~~

The most significant component provided by this package is the class
``Signal``:

.. code:: python

  from metapensiero.signal import Signal

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

  signal.notify(1, kw='a')
  assert called1 == (1, 'a')
  assert called2 == (1, 'a')

As you can see, to have a function or method called when a signal is
*fired* you just have to call the ``connect()`` method of the signal
instance. To remove that same method you can use the ``disconnect()``
method.

As you can see above, the way to fire an event is by calling the
``notify()`` method and any argument or keyword argument passed to
that function will be added to the handlers call.

It's possible to remove all the connected handlers by invoking the
``clear()`` method.

Asynchronous signal handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Not only you can have synchronous handlers, but you can have
asynchronous handlers as well:

.. code:: python

  import asyncio
  from metapensiero.signal import Signal

  @asyncio.coroutine
  def test_with_mixed_handlers():
      signal = Signal()
      called1 = False
      called2 = False
      h1 = asyncio.Event()

      @asyncio.coroutine
      def handler1(arg, kw):
          nonlocal called1
          called1 = (arg, kw)
          h1.set()

      def handler2(arg, kw):
          nonlocal called2
          called2 = (arg, kw)

      signal.connect(handler1)
      signal.connect(handler2)

      signal.notify(1, kw='a')
      assert called2 == (1, 'a')
      assert called1 == False
      yield from h1.wait()
      assert called1 == (1, 'a')

  loop = asyncio.get_event_loop()
  loop.run_until_complete(test_with_mixed_handlers())

As you can see in this example the var ``called2`` immediately after
the notify has the expected value but the value of the var ``called1``
hasn't. To have it the code has to suspend itself and wait for the
flag event to be set. This is because ``handler1()`` is scheduled to
be executed with ``asyncio.ensure_future()`` but it isn't waited for a
result by the ``notify()`` method.

The usage of a flag to synchronize is a bit silly, what if we have
more than one async handler? Do we have to create an ``asyncio.Event``
instance for all of them and then wait for everyone of those? And if
the actual amount of async handlers isn't known in advance, what
should we do?

Transaction support
~~~~~~~~~~~~~~~~~~~

This is exactly where the sister package
`metapensiero.asyncio.transaction`__ comes handy. The ``Signal`` class
works with it to ensure that two coroutines (the one calling
``notify()`` and ``handler1()``) can be synchronized.

To do that the *outer* code has just to start a  *transaction* and
if it is in place, the ``Signal`` class' code will automatically add
any async event handler to it.

To summarize this feature the previous example can be written also
as:

.. code:: python

  import asyncio
  from metapensiero.signal import Signal
  from metapensiero.asyncio import transaction

  @asyncio.coroutine
  def test_with_mixed_handlers():
      signal = Signal()
      called1 = False
      called2 = False

      @asyncio.coroutine
      def handler1(arg, kw):
          nonlocal called1
          called1 = (arg, kw)
          h1.set()

      def handler2(arg, kw):
          nonlocal called2
          called2 = (arg, kw)

      signal.connect(handler1)
      signal.connect(handler2)

      trans = transaction.begin()
      signal.notify(1, kw='a')
      assert called2 == (1, 'a')
      assert called1 == False
      yield from trans.end()
      assert called1 == (1, 'a')

  loop = asyncio.get_event_loop()
  loop.run_until_complete(test_with_mixed_handlers())

Or, with python 3.5, we can use async context managers, so it becomes:

.. code:: python

  import asyncio
  from metapensiero.signal import Signal
  from metapensiero.asyncio import transaction

  async def test_with_mixed_handlers():
      signal = Signal()
      called1 = False
      called2 = False

      async def handler1(arg, kw):
          nonlocal called1
          called1 = (arg, kw)
          h1.set()

      def handler2(arg, kw):
          nonlocal called2
          called2 = (arg, kw)

      signal.connect(handler1)
      signal.connect(handler2)

      async with transaction.begin():
          signal.notify(1, kw='a')
          assert called2 == (1, 'a')
          assert called1 == False
      assert called1 == (1, 'a')

  loop = asyncio.get_event_loop()
  loop.run_until_complete(test_with_mixed_handlers())

__ https://pypi.python.org/pypi/metapensiero.asyncio.transaction

This way the calling context has a generic and scalable way of
synchronize the block of code that runs ``notify()`` with the side effects,
even when they are async and their number is unknown.

Use signals with classes
~~~~~~~~~~~~~~~~~~~~~~~~

A ``Signal`` instance class can also be used as a member of a
class. When this is the case a decorator is provided to declare
class-level handlers. To let this feature work, the user class has to
have a specific metaclass:

.. code:: python

  from metapensiero.signal import Signal, SignalAndHandlerInitMeta, handler

  class A(metaclass=SignalAndHandlerInitMeta):

      click = Signal()

      def __init__(self):
          self.called = False

      @handler('click')
      def onclick(self, arg, kw):
          self.called = (arg, kw)

  a1 = A()
  assert a1.called == False
  a1.click.notify(1, kw='a')
  assert a1.called == (1, 'a')

Of course a class-level handler can be async:

.. code:: python

  import asyncio

  from metapensiero.asyncio import transaction
  from metapensiero.signal import Signal, SignalAndHandlerInitMeta, handler

  class A(metaclass=SignalAndHandlerInitMeta):

      click = Signal()

      def __init__(self):
          self.called = False
          self.called2 = False

      @handler('click')
      def onclick(self, arg, kw):
          self.called = (arg, kw)

      @handler('click')
      @asyncio.coroutine
      def click2(self, arg, kw):
          self.called2 = (arg, kw)

  a1 = A()

  @asyncio.coroutine
  def runner():
      assert a1.called == False
      assert a1.called2 == False

      trans = transaction.begin()
      a1.click.notify(1, kw='a')
      assert a1.called == (1, 'a')
      assert a1.called2 == False
      yield from trans.end()
      assert a1.called2 == (1, 'a')

  loop = asyncio.get_event_loop()
  loop.run_until_complete(runner())

Of course, you can use the ``Signal`` class without user class
instrumentation, but you will have to do per-instance subscriptions by
yourself:

.. code:: python

  class B:

      # the name here is needed for classes that don't explicitly support
      # signals
      click = Signal('click')

      def __init__(self):
          self.called = False
          self.click.connect(self.onclick)

      def onclick(self, arg, kw):
          self.called = (arg, kw)

  b = B()
  assert b.called == False
  b.onclick.notify(1, kw='b')
  assert b.called == (1, 'b')

Extensibility
~~~~~~~~~~~~~

Signals support two way to extend their functionality. The first is
global and is intended as a way to plug in signals into other event
systems. Please have a look at the code in ``external.py`` and the
corrisponding tests to learn how to use those abstract classes, they
give you a way to tap into signal's machinery do your stuff.

The second way is per-signal and allows you to define three functions
to wrap around ``notify()``, ``connect()``, ``disconnect()`` and
attach them to each instance of signal via decorators, much like with
builtins properties.

Each of these functions will receive all the relevant arguments to
customize the behavior of the internal signal methods and will receive
another argument that every function has to call in order to trigger
the default behavior. The return value of your wrapper function will
be returned to the calling context instead of default return values.

Here is an example, pay attention to the signature of each wrapper
beacuse you have to respect that:

.. code:: python

  from metapensiero.signal import Signal, SignalAndHandlerInitMeta, handler

  c = dict(called=0, connnect_handler=None, handler_called=0, handler_args=None,
           disconnnect_handler=None, handler2_called=0, handler2_args=None)

  class A(metaclass=SignalAndHandlerInitMeta):

       @Signal
       def click(self, subscribers, notify, *args, **kwargs):
           c['called'] += 1
           c['wrap_args'] = (args, kwargs)
           assert len(subscribers) == 2
           assert isinstance(self, A)
           notify('foo', k=2)
           return 'mynotify'

       @click.on_connect
       def click(self, handler, subscribers, connect):
           c['called'] += 1
           c['connect_handler'] = handler
           assert len(subscribers) == 0
           connect(handler)
           return 'myconnect'

       @click.on_disconnect
       def click(self, handler, subscribers, disconnect):
           c['called'] += 1
           c['disconnect_handler'] = handler
           assert len(subscribers) == 1
           disconnect(handler)
           return 'mydisconnect'

       @handler('click')
       def handler(self, *args, **kwargs):
           c['handler_called'] += 1
           c['handler_args'] = (args, kwargs)

  a = A()

  def handler2(*args, **kwargs):
      c['handler2_called'] += 1
      c['handler2_args'] = (args, kwargs)

  res = a.click.connect(handler2)
  assert res == 'myconnect'
  res = a.click.notify('bar', k=1)
  assert res == 'mynotify'
  res = a.click.disconnect(handler2)
  assert res == 'mydisconnect'
  assert c['called'] == 3
  assert c['wrap_args'] == (('bar',), {'k': 1})
  assert c['handler_called'] == 1
  assert c['handler_args'] == (('foo',), {'k': 2})
  assert c['handler2_called'] == 1
  assert c['handler2_args'] == (('foo',), {'k': 2})
  assert c['disconnect_handler'] == handler2
  assert c['connect_handler'] == handler2

As you can see, with this way of managing wrappers to default
behaviors, you can modify arguments, return customized values or even
avoid triggering the default behavior.

Testing
-------

To run the tests you should run the following at the package root::

  python setup.py test


Build status
------------

.. image:: https://travis-ci.org/azazel75/metapensiero.signal.svg?branch=master
    :target: https://travis-ci.org/azazel75/metapensiero.signal
