# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- signal class
# :Created:   mer 16 dic 2015 12:28:23 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright © 2015, 2016, 2017 Alberto Berti
#

import asyncio
from functools import partial
import logging
import inspect
import sys
import re
import textwrap
import types
import weakref

from .external import ExternalSignaller
from .utils import Executor, pull_result, SignalOptions
from .weak import MethodAwareWeakList
from . import SignalAndHandlerInitMeta


logger = logging.getLogger(__name__)
SIGN_DOC_TEMPLATE="""

:returns: an awaitable that will return the results from the handlers
:rtype: an instance of `metapensiero.signal.utils.MultipleResults`:py:class:

This is a `metapensiero.signal.core.Signal`:py:class:
"""


class InstanceProxy:
    """A small proxy used to get instance context when signal is a
    member of a class.
    """

    def __init__(self, signal, instance):
        self.signal = signal
        self.instance = instance
        self.subscribers = self.get_subscribers()
        sdoc = signal.__dict__.get('__doc__')
        if sdoc is not None:
            self.__doc__ = sdoc

    def __repr__(self):
        return ('<Signal "{self.signal.name}" '
                ' on {self.instance!r}>').format(self=self)

    def clear(self):
        """Remove all the connected handlers, for this instance"""
        self.subscribers.clear()

    def connect(self, cback):
        "See signal"
        return self.signal.connect(cback,
                                   subscribers=self.subscribers,
                                   instance=self.instance)

    def disconnect(self, cback):
        "See signal"
        return self.signal.disconnect(cback,
                                      subscribers=self.subscribers,
                                      instance=self.instance)

    def get_subscribers(self):
        """Get per-instance subscribers from the signal.
        """
        data = self.signal.instance_subscribers
        if self.instance not in data:
            data[self.instance] = MethodAwareWeakList()
        return data[self.instance]

    @property
    def loop(self):
        return getattr(self.instance, 'loop', None)

    def notify(self, *args, **kwargs):
        "See signal"
        loop = kwargs.pop('loop', self.loop)
        return self.signal.prepare_notification(
            subscribers=self.subscribers, instance=self.instance,
            loop=loop).run(*args, **kwargs)

    __call__ = notify

    def notify_prepared(self, args=None, kwargs=None, **opts):
        """Like notify allows to pass more options to the underlying
        `Signal.prepare_notification()` method.

        The allowed options are:

        notify_external : bool
          a flag indicating if the notification should also include the
          registered `~.external.ExternalSignaller` in the notification. It's
          ``True`` by default

        """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        loop = kwargs.pop('loop', self.loop)
        return self.signal.prepare_notification(
            subscribers=self.subscribers, instance=self.instance,
            loop=loop, **opts).run(*args, **kwargs)


class Signal:
    """The core class. It collects subscribers that can be either normal
    "callable" or coroutine/awaitable generator functions. The subscription is
    managed using the `connect`:meth: and `disconnect`:meth: methods. The
    notification is done by executing e `notify`:meth: method.

    It can be used either as a standalone event or in the body of another class
    which uses `~.user.SignalAndHandlerInitMeta`:class: metaclass, with the help
    of the `~.utils.signal`:func: decorator.

    :param \*flags: any flags that can change the behavior of the signal
      instance, see `~.utils.SignalOptions`:class: class
    :keyword fconnect: an optional callable that wraps the `connect`:meth:
      method
    :keyword fdisconnect: an optional callable that wraps the
      `disconnect`:meth: method
    :keyword fnotify: an optional callable that wraps the
      `notify`:meth: method
    :keyword fvalidation: an optional validation callable used to ensure that
      arguments passed to the `notify`:meth: invocation are those permitted
    :keyword str name: optional name of the signal
    :keyword loop: optional asyncio event loop to use
    :keyword external: optional external signaller that extends the signal
    :type external: `~.external.ExternalSignaller`:class:
    :param \*\*additional_params: optional additional params that will be
      stored in the instance
    """
    _external_signaller = None
    _name = None
    _concurrent_handlers = False

    FLAGS = SignalOptions
    """All the available handlers sort modes. See `~.utils.SignalOptions`.
    """

    def __init__(self, *flags, fconnect=None, fdisconnect=None,
                 fnotify=None, fvalidation=None, name=None,
                 loop=None, external=None, **additional_params):
        self.name = name
        self.subscribers = MethodAwareWeakList()
        """A weak list containing the connected handlers"""
        self.loop = loop or asyncio.get_event_loop()
        self.instance_subscribers = weakref.WeakKeyDictionary()
        self.external_signaller = external
        self._fnotify = fnotify
        self._fconnect = fconnect
        self._fdisconnect = fdisconnect
        self._set_fvalidation(fvalidation)
        self._iproxies = weakref.WeakKeyDictionary()
        if not all(isinstance(f, SignalOptions) for f in flags):
            raise ValueError("``flags`` elements must be instances of "
                             "`SignalOptions")
        if (SignalOptions.SORT_BOTTOMUP in flags and
            SignalOptions.SORT_TOPDOWN in flags):
            raise ValueError("Both sort modes specified in the flags")
        elif not (SignalOptions.SORT_BOTTOMUP in flags or
                  SignalOptions.SORT_TOPDOWN in flags):
            flags = flags + (SignalOptions.SORT_BOTTOMUP,)
        self.flags = flags
        self.additional_params = additional_params
        """additional parameter passed at construction time"""

    def __get__(self, instance, owner):
        if instance is None:
            # just a silly trick to get some better autodoc docs
            if (self._fvalidation is not None and
                'sphinx.ext.autodoc' in sys.modules):
                result = self._fvalidation
            else:
                result = self
        else:
            if instance not in self._iproxies:
                self._iproxies[instance] = InstanceProxy(self, instance)
            result = self._iproxies[instance]
        return result

    def __repr__(self):
        return ("<%s with name %r, len: %d>" % (
            self.__class__.__name__, self.name, len(self.subscribers)
        ))

    def _connect(self, subscribers, cback):
        if cback not in subscribers:
            subscribers.append(cback)

    def _disconnect(self, subscribers, cback):
        if cback in subscribers:
            subscribers.remove(cback)

    def _find_indent(self, doct):
        lines = doct.splitlines()
        for l in lines:
            match = re.match('^[ ]+', l)
            if match is not None:
                return len(match[0])
        return 0

    def _loop_from_instance(self, instance):
        if instance is None:
            loop = self.loop
        else:
            loop = self.__get__(instance).loop
        return loop

    def _notify_one(self, instance, cback, *args, **kwargs):
        loop = self._loop_from_instance(instance)
        return self.prepare_notification(
            subscribers=(cback,), instance=instance,
            loop=loop).run(*args, **kwargs)

    def _set_fvalidation(self, value):
        self._fvalidation = value
        if value is not None:
            if value.__doc__ is  None:
                doc = ''
                indent = 0
            else:
                doc = value.__doc__
                indent = self._find_indent(doc)
            sig_doc = textwrap.indent(SIGN_DOC_TEMPLATE, ' ' * indent)
            value.__doc__ = self.__doc__ = doc + sig_doc

    def connect(self, cback, subscribers=None, instance=None):
        """Add  a function or a method as an handler of this signal.
        Any handler added can be a coroutine.

        :param cback: the callback (or *handler*) to be added to the set
        :returns: ``None`` or the value returned by the corresponding wrapper
        """
        if subscribers is None:
            subscribers = self.subscribers
        # wrapper
        if self._fconnect is not None:
            def _connect(cback):
                self._connect(subscribers, cback)

            notify = partial(self._notify_one, instance)
            if instance is not None:
                result = self._fconnect(instance, cback, subscribers,
                                        _connect, notify)
            else:
                result = self._fconnect(cback, subscribers, _connect, notify)
            if inspect.isawaitable(result):
                result = pull_result(result)
        else:
            self._connect(subscribers, cback)
            result = None
        return result

    def clear(self):
        """Remove all the connected handlers"""
        self.subscribers.clear()

    def disconnect(self, cback, subscribers=None, instance=None):
        """Remove a previously added function or method from the set of the
        signal's handlers.

        :param cback: the callback (or *handler*) to be added to the set
        :returns: ``None`` or the value returned by the corresponding wrapper
        """
        if subscribers is None:
            subscribers = self.subscribers
        # wrapper
        if self._fdisconnect is not None:
            def _disconnect(cback):
                self._disconnect(subscribers, cback)

            notify = partial(self._notify_one, instance)
            if instance is not None:
                result = self._fdisconnect(instance, cback, subscribers,
                                           _disconnect, notify)
            else:
                result = self._fdisconnect(cback, subscribers, _disconnect,
                                           notify)
            if inspect.isawaitable(result):
                result = pull_result(result)
        else:
            self._disconnect(subscribers, cback)
            result = None
        return result

    def ext_publish(self, instance, loop, *args, **kwargs):
        """If 'external_signaller' is defined, calls it's publish method to
        notify external event systems.

        This is for internal usage only, but it's doumented because it's part
        of the interface with external notification systems.
        """
        if self.external_signaller is not None:
            # Assumes that the loop is managed by the external handler
            return self.external_signaller.publish_signal(self, instance, loop,
                                                          args, kwargs)

    @property
    def external_signaller(self):
        """The registered `~.external.ExternalSignaller`:class:."""
        return self._external_signaller

    @external_signaller.setter
    def external_signaller(self, value):
        if value is not None:
            assert isinstance(value, ExternalSignaller)
        self._external_signaller = value
        if self._name and value:
            value.register_signal(self, self._name)

    @property
    def name(self):
        """The *name* of the signal used in conjunction with external
        notification systems."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        if value is not None and self._external_signaller:
            self._external_signaller.register_signal(self, value)

    def notify(self, *args, **kwargs):
        """Call all the registered handlers with the arguments passed.

        :returns: an instance of `~.utils.MultipleResults`:class: or the
          result of the execution of the corresponding wrapper function
        """
        return self.prepare_notification().run(*args, **kwargs)

    __call__ = notify

    def prepare_notification(self, *, subscribers=None, instance=None,
                             loop=None, notify_external=True):
        """Sets up a and configures an `~.utils.Executor`:class: instance."""
        # merge callbacks added to the class level with those added to the
        # instance, giving the formers precedence while preserving overall
        # order
        self_subscribers = self.subscribers.copy()
        # add in callbacks declared in the main class body and marked with
        # @handler
        if (instance is not None and self.name and
            isinstance(instance.__class__, SignalAndHandlerInitMeta)):
            class_handlers = type(instance)._get_class_handlers(
                self.name, instance)
            for ch in class_handlers:
                # eventual methods are ephemeral and normally the following
                # condition would always be True for methods but the dict used
                # has logic to take that into account
                if ch not in self_subscribers:
                    self_subscribers.append(ch)
        # add in the other instance level callbacks added at runtime
        if subscribers is not None:
            for el in subscribers:
                # eventual methods are ephemeral and normally the following
                # condition would always be True for methods but the dict used
                # has logic to take that into account
                if el not in self_subscribers:
                    self_subscribers.append(el)
        loop = loop or self.loop
        # maybe do a round of external publishing
        if notify_external and self.external_signaller is not None:
            self_subscribers.append(partial(self.ext_publish, instance, loop))
        if self._fnotify is None:
            fnotify = None
        else:
            if instance is None:
                fnotify = self._fnotify
            else:
                fnotify = types.MethodType(instance, self._fnotify)
        validator = self._fvalidation
        if validator is not None and instance is not None:
            validator = types.MethodType(validator, instance)
        return Executor(self_subscribers, owner=self,
                        concurrent=SignalOptions.EXEC_CONCURRENT in self.flags,
                        loop=loop, exec_wrapper=fnotify,
                        fvalidation=validator)

    def on_connect(self, fconnect):
        """On connect optional wrapper decorator.

        :param fconnect: the callable to install as `connect`:meth: wrapper
        :returns: the signal
        """
        self._fconnect = fconnect
        return self

    def on_disconnect(self, fdisconnect):
        """On disconnect optional wrapper decorator.

        :param fdisconnect: the callable to install as `disconnect`:meth:
          wrapper
        :returns: the signal
        """
        self._fdisconnect = fdisconnect
        return self

    def on_notify(self, fnotify):
        """On notify optional wrapper decorator.

        :param fnotify: the callable to install as `notify`:meth: wrapper
        :returns: the signal
        """
        self._fnotify = fnotify
        return self
