.. -*- coding: utf-8 -*-
.. :Project:   metapensiero.signal -- An asyncio aware event framework
.. :Created:   dom 09 ago 2015 12:57:35 CEST
.. :Author:    Alberto Berti <alberto@metapensiero.it>
.. :License:   GNU General Public License version 3 or later
.. :Copyright: Copyright © 2015, 2016, 2017 Alberto Berti
..

.. currentmodule:: metapensiero.signal

Introduction
============

This package implements a light event system that is able to deal with
both synchronous and asynchronous event handlers. It manages the asynchronous
handlers using coroutines by default, with the possibility of handling them
using futures.

It can be used standalone or as member of a class.

It supports Python 3.5+.

Basic functionality
~~~~~~~~~~~~~~~~~~~

The most significant component provided by this package is the class
`~core.Signal`:class: which is very simple to use. It has three main
operations: *connect()*, *disconnect()* and  *notify()*.

The first two are used to manage the subscriptions of handlers to the signal
and the latter is used to actually execute all the handlers in the order that
they had been connected, passing the arguments in the
`~core.Signal.notify`:meth: call to each one, while collecting the result of
the execution that will returned to the `~core.Signal.notify`:meth:'s
caller. Let's see a simple example:

.. testcode::

  from metapensiero.signal import Signal

  asignal = Signal()
  called = {
   'handler1': False,
   'handler2': False
  }

  def handler1(arg, kw):
      called['handler1'] = (arg, kw)
      return 'result1'

  def handler2(arg, kw):
      called['handler2'] = (arg, kw)
      return 'result2'

  asignal.connect(handler1)
  asignal.connect(handler2)

  result = asignal.notify(1, kw='a')

.. doctest::

  >>> called
  {'handler1': (1, 'a'), 'handler2': (1, 'a')}


As you can see, to have a function or method called when a signal is *fired*
you just have to call the `~core.Signal.connect`:meth: method of the signal
instance. To remove that same method you can use the
`~core.Signal.disconnect`:meth: method.

As you can see above, the way to fire an event is by calling the
`~core.Signal.notify`:meth: method and any argument or keyword argument passed
to that function will be passed on each handler execution.

A `~core.Signal`:class: has its ``__call__()`` method defined as an alias to
its `~core.Signal.notify`:meth: method so it can also be called as:

.. doctest::

  >>> result = asignal(2, kw='b')
  >>> called
  {'handler1': (2, 'b'), 'handler2': (2, 'b')}


When a notification is executed, the return values from the handlers are
collected and are available inside `~core.Signal.notify`:meth:'s return value,
which is always an instance of the utility class
`~utils.MultipleResults`:class:.

.. doctest::

  >>> type(result)
  <class 'metapensiero.signal.utils.MultipleResults'>
  >>> result.results
  ('result1', 'result2')


The signal keeps a weak reference to each handler so you don't have to worry
about dangling references:

.. doctest::

  >>> len(asignal.subscribers)
  2

It's possible to remove all the connected handlers by invoking the
`~core.Signal.clear`:meth:  method.

.. doctest::

  >>> asignal.clear()
  >>> len(asignal.subscribers)
  0

Asynchronous signal handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Not only you can have synchronous handlers, but you can have
asynchronous handlers as well:

.. testcode:: async

  import asyncio
  from metapensiero.signal import Signal

  called = {
   'handler1': False,
   'handler2': False
  }

  asignal = Signal()

  async def handler1(arg, kw):
      called['handler1'] = (arg, kw)
      return 'result1'

  def handler2(arg, kw):
      called['handler2'] = (arg, kw)
      return 'result2'

  asignal.connect(handler1)
  asignal.connect(handler2)

  result = asignal.notify(1, kw='a')

What will be the result this time? As you may immagine, at this point
``called`` variable is:

.. doctest:: async

  >>> called
  {'handler1': False, 'handler2': (1, 'a')}

This is because ``handler1()`` which is a coroutine function doesn't execute
immediately, but instead it returns a coroutine which needs to be driven by
the event loop to be executed. How to understand if the results are ready or
not when the presence of coroutines among the subscribers is unknown? The
``result`` value (which is an instance of `~utils.MultipleResults`:class:) can
help with that:

.. doctest:: async

  >>> print('done?', result.done)
  done? False
  >>> print('any result?', result.results)
  any result? None
  >>> print('any coroutine?', result.has_async)
  any coroutine? True

As you can see, even if one of the handlers is a normal callable, its result
isn't available until all the handlers are executed. But to do that, we need a
loop, and something to "pull" the asynchronous results!

But we are lucky, as the ``result`` object is also an *awaitable* object:

.. doctest:: async

  >>> import inspect
  >>> inspect.isawaitable(result)
  True

So we can just do:

.. doctest:: async

  >>> loop = asyncio.get_event_loop()
  >>> awaited_result = loop.run_until_complete(result)

Let's verify what we got:

  >>> print('done?', result.done)
  done? True
  >>> print('any result?', result.results)
  any result? ('result1', 'result2')
  >>> print('any coroutine?', result.has_async)
  any coroutine? False

When *awaited*, the ``result`` object will return its ``results`` attribute so
that you always can code notifications like:

.. code:: python

  # inside your coroutine...
  result = await mysignal.notify(foo, bar)

and you will not have to deal with `~.utils.MultipleResults`:class:, here
``result`` will be always a simple tuple. Just to verify in out case:

.. doctest:: async

  >>> type(awaited_result)
  <class 'tuple'>
  >>> awaited_result is result.results
  True

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
      async def click2(self, arg, kw):
          self.called2 = (arg, kw)

  a1 = A()


  async def runner():
      assert a1.called == False
      assert a1.called2 == False

      await a1.click.notify(1, kw='a')
      assert a1.called == (1, 'a')
      assert a1.called2 == False
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
       def click(self, handler, subscribers, connect, notify):
           c['called'] += 1
           c['connect_handler'] = handler
           assert len(subscribers) == 0
           connect(handler)
           return 'myconnect'

       @click.on_disconnect
       def click(self, handler, subscribers, disconnect, notify):
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

There are cases when you want to notify the callback during
``on_connect`` or ``on_disconnect`` wrappers, for example when your
handler has the chance of being connected too late to the signal,
where a notification has been delivered already. In such cases you may
want to check for this situation in the wrapper and immediately notify
the late callback if it's the case.

The ``connect`` and ``disconnect`` wrappers parameter of the preceding example
will be called with one more parameter, a function ``notify()`` that will take
the callback as first argument, and then any other argument that will be
passed to the handler. So, let's see and example:

.. code:: python

  class A(metaclass=SignalAndHandlerInitMeta):

       click = Signal()

       @click.on_connect
       def click(self, handler, subscribers, connect, notify):
           if self.clicked:
               notify(handler)
           connect(handler)

       def __init__(self):
           self.clicked = False

       @handler
       def click_handler(self):
           self.clicked = True
