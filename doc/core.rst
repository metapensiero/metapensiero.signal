.. -*- coding: utf-8 -*-
.. :Project:   metapensiero.signal -- core module documentation
.. :Created:   ven 27 gen 2017 14:20:05 CET
.. :Author:    Lele Gaifax <lele@metapensiero.it>,
..             Alberto Berti <alberto@metapensiero.it>
.. :License:   GNU General Public License version 3 or later
.. :Copyright: © 2017 Lele Gaifax, Alberto Berti
..

======
 Core
======

.. currentmodule:: metapensiero.signal.core

Contains the core class, `Signal`:class: and the helper class used when
installed as a descriptor, `InstanceProxy`:class:.

.. autoclass:: metapensiero.signal.core.Signal
  :members:

  A signal performs three main operations: *connect()*, *disconnect()* and
  *notify()*. Each one of these operations can be wrapped with a custom
  function to alter its behavior, These functions can be specified at creation
  time using the ``fconnect``, ``fdisconnect`` and ``fdisconnect`` keyword
  pararameters or can specified after creation by using the related
  `on_connect`:meth:, `on_disconnect`:meth: and `on_notify`:meth: methods
  which all return ``self`` so that they can be used also as decorators of the
  designated wrappers. When the operation is performed, each wrapper will be
  called with the following arguments:

  fconnect:
    Its signature should be:

    .. function:: fconnect(callback, subscribers, connect, notify)

      Alter the connection process

      :arg callback: the *callback* originally passed to `connect`:meth:
      :arg subscribers: a list containing all the registered subscribers
      :arg connect: a *callable* that will execute the default connection
                    logic to the passed in `callback`
      :arg notify: a *callable* that will execute the default notification
                   logic to the passed in `callback`

    The wrapper function can be either a normal callable or a coroutine. The
    result of the wrapper execution will become the result of the
    `connect`:meth: call.

   fdisconnect:
    Its signature should be:


    .. function:: fdisconnect(callback, subscribers, disconnect, notify)

      Alter the disconnection process

      :arg callback: the *callback* originally passed to
                     `disconnect`:meth:
      :arg subscribers: a list containing all the registered subscribers
      :arg disconnect: a *callable* that will execute the default connection
                       logic to the passed in `callback`
      :arg notify: a *callable* that will execute the default notification
                   logic to the passed in `callback`

    The wrapper function can be either a normal callable or a coroutine. The
    result of the wrapper execution will become the result of the
    `disconnect`:meth: call.

  fnotify:
    Its signature should be:

    .. function:: fnotify(subscribers, notify, *args, **kwargs)

      Alter the notification process

      :arg subscribers: a list containing all the registered subscribers
      :arg notify: a *callable* that will execute the default notification
                   logic to all the subscribers
      :arg \*args: the arguments passed to the `notify`:meth: call
      :arg \*\*kwargs: the keyword params passed to the `notify`:meth:
                       call

    The wrapper function can be either a normal callable or a coroutine. The
    result of the wrapper execution will become the result of the
    `notify`:meth: call.


.. autoclass:: metapensiero.signal.core.InstanceProxy
