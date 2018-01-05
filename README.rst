.. -*- coding: utf-8 -*-
.. :Project:   metapensiero.signal -- An event framework that is asyncio aware
.. :Created:   dom 09 ago 2015 12:57:35 CEST
.. :Author:    Alberto Berti <alberto@metapensiero.it>
.. :License:   GNU General Public License version 3 or later
.. :Copyright: Copyright © 2015, 2016, 2017, 2018 Alberto Berti
..

.. image:: https://gitlab.com/metapensiero/metapensiero.signal/badges/master/pipeline.svg
   :target: https://gitlab.com/metapensiero/metapensiero.signal/commits/master
   :align: left
   :alt: tests status

.. image:: https://gitlab.com/metapensiero/metapensiero.signal/badges/master/coverage.svg
   :target: https://gitlab.com/metapensiero/metapensiero.signal/commits/master
   :align: left
   :alt: tests coverage

=======================================================
 metapensiero.signal: An asyncio aware event framework
=======================================================

 :author: Alberto Berti
 :contact: alberto@metapensiero.it
 :license: GNU General Public License version 3 or later


Goal
====

This package implements a light event system that is able to deal with both
synchronous and asynchronous event handlers. It can be used standalone or as
member of a class.

Installation
============

To install the package execute the following command:

.. code:: bash

  $ pip install metapensiero.signal

Usage
=====

An example of usage as standalone object:

.. code:: python

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

.. code:: python

  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(result)
  ('result1', 'result2')
  >>> called
  {'handler1': (1, 'a'), 'handler2': (1, 'a')}


and an example of use as class member:

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

Read the documentation to discover how to use these features.

Testing
=======

To run the tests you should run the following at the package root::

  python setup.py test
