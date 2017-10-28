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
import weakref

from .external import ExternalSignaller
from .utils import Executor, HANDLERS_SORT_MODE, pull_result
from .weak import MethodAwareWeakList
from . import SignalAndHandlerInitMeta


logger = logging.getLogger(__name__)


class InstanceProxy:
    """A small proxy used to get instance context when signal is a
    member of a class.
    """

    def __init__(self, signal, instance):
        self.signal = signal
        self.instance = instance
        self.subscribers = self.get_subscribers()

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

    def notify_no_ext(self, *args, **kwargs):
        "Like notify but avoid notifying external managers"
        loop = kwargs.pop('loop', self.loop)
        return self.signal.prepare_notification(
            subscribers=self.subscribers, instance=self.instance,
            loop=loop, notify_external=False).run(*args, **kwargs)


class Signal(object):
    """The core class. It collect subscriber *callables*, both normal and
    *awaitables* to execute them when its `~Signal.notify()` method is called.
    """
    _external_signaller = None
    _name = None
    _concurrent_handlers = False

    SORT_MODE = HANDLERS_SORT_MODE
    """All the available handlers sort modes. See `~.utils.HANDLERS_SORT_MODE`.
    """

    def __init__(self, fnotify=None, fconnect=None, fdisconnect=None,
                 name=None, loop=None, external=None,
                 concurrent_handlers=False, sort_mode=None,
                 **additional_params):
        self.name = name
        self.subscribers = MethodAwareWeakList()
        self.loop = loop or asyncio.get_event_loop()
        self.instance_subscribers = weakref.WeakKeyDictionary()
        self.external_signaller = external
        self._fnotify = fnotify
        self._fconnect = fconnect
        self._fdisconnect = fdisconnect
        self._iproxies = weakref.WeakKeyDictionary()
        self._concurrent_handlers = concurrent_handlers
        self._sort_mode = sort_mode or HANDLERS_SORT_MODE.BOTTOMUP
        self.additional_params = additional_params
        """additional parameter passed at construction time"""

    def __get__(self, instance, cls=None):
        if instance is not None:
            if instance not in self._iproxies:
                self._iproxies[instance] = InstanceProxy(self, instance)
            result = self._iproxies[instance]
        else:
            result = self
        return result

    def _connect(self, subscribers, cback):
        if cback not in subscribers:
            subscribers.append(cback)

    def _disconnect(self, subscribers, cback):
        if cback in subscribers:
            subscribers.remove(cback)

    def _loop_from_instance(self, instance):
        if instance is None:
            loop = self.loop
        else:
            loop = self.__get__(instance).loop
        return loop

    def _notify_one(self, instance, cback, *args, **kwargs):
        loop = self._loop_from_instance(instance)
        return self.prepare_notification(subscribers=(cback,), instance=instance,
                                         loop=loop).run(*args, **kwargs)

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
        """The registered `~.external.ExternalSignaller`."""
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

        :returns: an instance of `~.utils.MultipleResults` or the result of
          the execution of the corresponding wrapper function
        """
        return self.prepare_notification().run(*args, **kwargs)

    def prepare_notification(self, *, subscribers=None, instance=None,
                             loop=None, notify_external=True):
        """Sets up a and configures an `Executor` instance."""
        # merge callbacks added to the class level with those added to the
        # instance, giving the formers precedence while preserving overall order
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
                fnotify = partial(self._fnotify, instance)
        return Executor(self, self_subscribers,
                        concurrent=self._concurrent_handlers,
                        loop=loop, exec_wrapper=fnotify)

    def on_connect(self, fconnect):
        "On connect optional wrapper decorator"
        self._fconnect = fconnect
        return self

    def on_disconnect(self, fdisconnect):
        "On disconnect optional wrapper decorator"
        self._fdisconnect = fdisconnect
        return self
