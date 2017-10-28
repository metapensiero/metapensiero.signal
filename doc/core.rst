.. -*- coding: utf-8 -*-
.. :Project:   metapensiero.signal -- atom documentation
.. :Created:   ven 27 gen 2017 14:20:05 CET
.. :Author:    Lele Gaifax <lele@metapensiero.it>,
..             Alberto Berti <alberto@metapensiero.it>
.. :License:   GNU General Public License version 3 or later
.. :Copyright: © 2017 Lele Gaifax, Alberto Berti
..

======
 Core
======

Contains the core class, `~Signal` and the main utility classes.

.. autoclass:: metapensiero.signal.core.Signal

  :param fnotify: a *callable* that will be executed to alter the notification
                  process. It is called with the following arguments:

    .. function:: fnotify(subscribers, notify, *args, **kwargs)

      Alter the notification process

      :arg subscribers: a list containing all the registered subscribers
      :arg notify: a *callable* that will execute the default notification
                   logic to all the subscribers
      :arg \*args: the arguments passed to the `~.Signal.notify()` call
      :arg \*\*kwargs: the keyword params passed to the `~.Signal.notify()`
                       call

    The wrapper function can be either a normal callable or a coroutine. The
    result of the wrapper execution will become the result of the
    `~.Signal.notify()` call. It can be specified using the signal as a
    decorator, like:

    .. code:: python

      @Signal
      def notify_wrapper(subs, notify, *args, **kwargs):
          ...

  :param fconnect: a *callable* to alter the connection process. It's called
                   with the following arguments:


    .. function:: fconnect(callback, subscribers, connect, notify)

      Alter the connection process

      :arg callback: the *callback* originally passed to `~Signal.connect()`
      :arg subscribers: a list containing all the registered subscribers
      :arg connect: a *callable* that will execute the default connection
                    logic to the passed in `callback`
      :arg notify: a *callable* that will execute the default notification
                   logic to the passed in `callback`

    The wrapper function can be either a normal callable or a coroutine. The
    result of the wrapper execution will become the result of the
    `~.Signal.connect()` call.

  :param fdisconnect: a *callable* to alter the connection process. It's
                      called with the following arguments:


    .. function:: fdisconnect(callback, subscribers, disconnect, notify)

      Alter the disconnection process

      :arg callback: the *callback* originally passed to
                     `~Signal.disconnect()`
      :arg subscribers: a list containing all the registered subscribers
      :arg disconnect: a *callable* that will execute the default connection
                       logic to the passed in `callback`
      :arg notify: a *callable* that will execute the default notification
                   logic to the passed in `callback`

    The wrapper function can be either a normal callable or a coroutine. The
    result of the wrapper execution will become the result of the
    `~.Signal.disconnect()` call.

  :param str name: optional name of the signal, used when interfacing with
                   external systems
  :param loop: optional *asyncio* loop instance
  :param external: optional external interface object
  :type external: `~.external.ExternalSignaller`
  :param bool concurrent_handlers: optional flag indicating if the
    *awaitables* are to be evaluated concurrently instead of sequentially
  :param sort_mode: an optional enum value indicating the sort order of the
                    class-based handlers, by default it is
                    `~.utils.HANDLERS_SORT_MODE.BOTTOMUP`
  :type sort_mode: `~.utils.HANDLERS_SORT_MODE`
  :param \*\*additional_params: optional additional params that will be stored
                                in the instance

.. autoclass:: metapensiero.signal.core.InstanceProxy
