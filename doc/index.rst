.. -*- coding: utf-8 -*-
.. :Project:   metapensiero.signal -- Documentation
.. :Created:   dom 18 dic 2016 15:01:08 CET
.. :Author:    Lele Gaifax <lele@metapensiero.it>
.. :License:   GNU General Public License version 3 or later
.. :Copyright: © 2016, 2017 Lele Gaifax, Alberto Berti
..


 metapensiero.signal: An asyncio aware event framework
=======================================================

This package implements a simple but scalable event system that can deal with
handlers that are either normal functions or coroutines.

It manages the asynchronous handlers using coroutines by default, with the
possibility of handling them using futures.

An example of usage in a class:

.. code:: python

  import asyncio

  from metapensiero.signal import Signal, SignalAndHandlerInitMeta, handler


  class B(metaclass=SignalAndHandlerInitMeta):

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

  b = B()

.. code:: python

  >>> result = b.click.notify(1, kw='a')
  >>> b.called
  (1, 'a')
  >>> b.called2
  False
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(result)
  (None, None)
  >>> b.called2
  (1, 'a')


Features
========

* handlers can return no value, one value, or multiple values;
* **configurable execution** of **async** handlers: *sequential* or
  *concurrent*;
* **connect handlers** in a simple way **by decorating methods** in class
  body;
* **easily tap into signal** machinery by defining wrappers for the main
  operations: *connect*, *disconnect*, *notify*;
* **integrate** signals in your application or framework by implementing well
  defined ABCs;
* **control** class defined handlers **sorting** during **execution** when
  using signals for *setup* or *teardown* use cases;
* allows you to **easily validate arguments** when firing the signal;
* **auto-generates documentation** for Sphinx's *autodoc* extension;



.. toctree::

   intro
   api
