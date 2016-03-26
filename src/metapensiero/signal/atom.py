# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- signal class
# :Created:    mer 16 dic 2015 12:28:23 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

from __future__ import unicode_literals, absolute_import

import six

if six.PY3:
    import asyncio
else:
    asyncio = None

from functools import partial
import logging
import weakref

if six.PY3:
    from metapensiero.asyncio import transaction
else:
    transaction = None

from .weak import MethodAwareWeakSet
from . import ExternalSignaller
from . import SignalAndHandlerInitMeta

logger = logging.getLogger(__name__)


class Signal(object):
    """ The atom of event handling
    """
    _external_signaller = None
    _name = None

    class InstanceProxy(object):
        """A small proxy used to get instance context when signal is a
        member of a class.
        """

        def __init__(self, signal, instance):
            self.signal = signal
            self.instance = instance
            self.subscribers = self.get_subscribers()
            self.loop = getattr(self.instance, 'loop', None)

        def get_subscribers(self):
            """Get per-instance subscribers from the signal.
            """
            data = self.signal.instance_subscribers
            if self.instance not in data:
                data[self.instance] = MethodAwareWeakSet()
            return data[self.instance]

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

        def notify(self, *args, **kwargs):
            "See signal"
            loop = kwargs.pop('loop', self.loop)
            return self.signal.notify(*args,
                                      _subscribers=self.subscribers,
                                      _instance=self.instance,
                                      _loop=loop,
                                      **kwargs)

        def clear(self):
            """Remove all the connected handlers, for this instance"""
            self.subscribers.clear()

    def __init__(self, fnotify=None, fconnect=None, fdisconnect=None, name=None,
                 loop=None, external=None):
        self.name = name
        self.subscribers = MethodAwareWeakSet()
        if six.PY3:
            self.loop = loop or asyncio.get_event_loop()
        else:
            self.loop = None
        self.instance_subscribers = weakref.WeakKeyDictionary()
        self.external_signaller = external
        self._fnotify = fnotify
        self._fconnect = fconnect
        self._fdisconnect = fdisconnect

    @property
    def external_signaller(self):
        return self._external_signaller

    @external_signaller.setter
    def external_signaller(self, value):
        if value:
            assert isinstance(value, ExternalSignaller)
        self._external_signaller = value
        if self._name and value:
            value.register_signal(self, self._name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        if value and self._external_signaller:
            self._external_signaller.register_signal(self, value)

    def connect(self, cback, subscribers=None, instance=None):
        """Add  a function or a method as an handler of this signal.
        Any handler added can be a coroutine.
        """
        if subscribers is None:
            subscribers = self.subscribers
        # wrapper
        if self._fconnect:
            def _connect(cback):
                self._connect(subscribers, cback)

            _connect.notify = partial(self._notify_one, instance)
            if instance:
                result = self._fconnect(instance, cback, subscribers, _connect)
            else:
                result = self._fconnect(cback, subscribers, _connect)
        else:
            self._connect(subscribers, cback)
            result = None
        return result

    def _connect(self, subscribers, cback):
        subscribers.add(cback)

    def disconnect(self, cback, subscribers=None, instance=None):
        """Remove a previously added function or method from the set of the
        signal's handlers.
        """
        if subscribers is None:
            subscribers = self.subscribers
        # wrapper
        if self._fdisconnect:
            def _disconnect(cback):
                self._disconnect(subscribers, cback)

            _disconnect.notify = partial(self._notify_one, instance)
            if instance:
                result = self._fdisconnect(instance, cback, subscribers,
                                           _disconnect)
            else:
                result = self._fdisconnect(cback, subscribers, _disconnect)
        else:
            self._disconnect(subscribers, cback)
            result = None
        return result

    def _disconnect(self, subscribers, cback):
        if cback in subscribers:
            subscribers.remove(cback)

    def notify(self, *args, **kwargs):
        """Call all the registered handlers with the arguments passed. If a
        notify wrapper is defined it is called with a notify callback
        to really start the notification and a set of the registered
        class-defined and per-instance subscribers.
        """
        subscribers = kwargs.pop('_subscribers', None)
        instance = kwargs.pop('_instance', None)
        loop = kwargs.pop('_loop', None)
        # if i'm not called from an instance, use the default
        # subscribers
        if subscribers is None:
            subscribers = set(self.subscribers)
        else:
            # do not keep weaksets for the duration of the notification
            subscribers = set(self.subscribers | subscribers)
        if instance and self.name and isinstance(instance.__class__,
                                                 SignalAndHandlerInitMeta):
            # merge the set of instance-only handlers with those declared
            # in the main class body and marked with @handler
            subscribers |= self._get_class_handlers(instance)
        if self._fnotify:
            def cback(*args, **kwargs):
                return self._notify(subscribers, instance, loop, args, kwargs)
            if instance:
                result = self._fnotify(instance, subscribers, cback, *args, **kwargs)
            else:
                result = self._fnotify(subscribers, cback, *args, **kwargs)
        else:
            result = self._notify(subscribers, instance, loop, args, kwargs)
        return result

    def _notify(self, subscribers, instance, loop, args, kwargs):
        """Call all the registered handlers with the arguments passed.
        If this signal is a class member, call also the handlers registered
        at class-definition time. If an external publish function is
        supplied, call it with the provided arguments at the end.

        Returns a list with the results from the handlers execution.
        """
        coros = []
        results = []
        for method in subscribers:
            try:
                res = method(*args, **kwargs)
                if six.PY3:
                    if asyncio.iscoroutine(res):
                        coros.append(res)
                    else:
                        results.append(res)
                else:
                    results.append(res)
            except:
                logger.exception('Error in notify')
                raise
        loop = loop or self.loop
        # maybe do a round of external publishing
        ext_res = self.ext_publish(instance, loop, args, kwargs)
        if six.PY3:
            if asyncio.iscoroutine(ext_res):
                coros.append(ext_res)

            trans = transaction.get(None)
            all_co = asyncio.gather(*coros, loop=loop)
            if trans:
                trans.add(all_co)
            results.append(all_co)
        return results

    def ext_publish(self, instance, loop, args, kwargs):
        """If 'external_signaller' is defined, calls it's publish method to
        notify external event systems.
        """
        if self.external_signaller:
            # Assumes that the loop is managed by the external handler
            return self.external_signaller.publish_signal(self, instance, loop,
                                                          args, kwargs)

    def _notify_one(self, instance, cback, *args, **kwargs):
        if instance:
            loop = self.__get__(instance).loop
        else:
            loop = None
        return self._notify(set((cback,)), instance, loop, args, kwargs)

    def __get__(self, instance, cls=None):
        if instance:
            result = self.InstanceProxy(self, instance)
        else:
            result = self
        return result

    def _get_class_handlers(self, instance):
        """Returns the handlers registered at class level.
        """
        # TODO: Move this to SignalAndHandlerInitMeta
        cls = instance.__class__
        handlers = cls._signal_handlers
        return set(getattr(instance, hname) for hname, sig_name in
                   six.iteritems(handlers) if sig_name == self.name)

    def on_connect(self, fconnect):
        "On connect optional wrapper decorator"
        self._fconnect = fconnect
        return self

    def on_disconnect(self, fdisconnect):
        "On disconnect optional wrapper decorator"
        self._fdisconnect = fdisconnect
        return self

    def clear(self):
        """Remove all the connected handlers"""
        self.subscribers.clear()
