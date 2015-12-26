# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- signal class
# :Created:    mer 16 dic 2015 12:28:23 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

import asyncio
import weakref

from metapensiero.asyncio import transaction

from .weak import MethodAwareWeakSet


class Signal:
    """ The atom of event handling
    """

    class InstanceProxy:
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
            if not self.instance in data:
                data[self.instance] = MethodAwareWeakSet()
            return data[self.instance]

        def connect(self, cback):
            "See signal"
            return self.signal.connect(cback,
                                       subscribers=self.subscribers)

        def disconnect(self, cback):
            "See signal"
            return self.signal.disconnect(cback,
                                          subscribers=self.subscribers)

        def notify(self, *args, loop=None, **kwargs):
            "See signal"
            loop = loop or self.loop
            return self.signal.notify(*args,
                                      subscribers=self.subscribers,
                                      instance=self.instance,
                                      loop=loop,
                                      **kwargs)

    def __init__(self, name=None, loop=None):
        self.name = name
        self.subscribers = MethodAwareWeakSet()
        self.loop = loop or asyncio.get_event_loop()
        self.instance_subscribers = weakref.WeakKeyDictionary()
        self.external_publishers = weakref.WeakKeyDictionary()

    def connect(self, cback, subscribers=None):
        """Add  a function or a method as an handler of this signal.
        Every handler added should be a coroutine.
        """
        if subscribers is None:
            subscribers = self.subscribers
        subscribers.add(cback)

    def disconnect(self, cback, subscribers=None):
        """Remove a previously added function or method from the set of the
        signal's handlers.
        """
        if subscribers is None:
            subscribers = self.subscribers
        subscribers.remove(cback)

    def notify(self, *args, subscribers=None,
               instance=None, loop=None, **kwargs):
        """Call all the registered handlers with the arguments passed.
        If this signal is a class member, call also the handlers registered
        at class-definition time. If an external publish function is
        supplied, call it with the provided arguments at the end.

        Returns a list with the results from the handlers execution.
        """
        # if i'm not called from an instance, use the default subscribers
        if subscribers is None:
            subscribers = self.subscribers
        subscribers = set(subscribers)
        if instance and self.name and hasattr(instance.__class__,
                                              '_signal_handlers'):
            # merge the set of instance-only handlers with those declared
            # in the main class body and marked with @handler
            subscribers |= self._get_class_handlers(instance)

        # pop the kwargs prefixed with 'local_'
        # TODO: test this
        loc_kwargs = {k[6:]: v for k, v in kwargs.items()
                      if k.startswith('local_')}
        ext_kwargs = {k: v for k, v in kwargs.items()
                      if not k.startswith('local_')}
        loc_kwargs.update(ext_kwargs)
        coros = []
        results = []
        for method in subscribers:
            try:
                res = method(*args, **kwargs)
                if asyncio.iscoroutine(res):
                    coros.append(res)
                else:
                    results.append(res)
            except Exception as e:
                logger.exception('Error in notify')
        loop = loop or self.loop
        # maybe do a round of external publishing
        if instance:
            ext_res = self.ext_publish(instance, args, ext_kwargs)
            if asyncio.iscoroutine(ext_res):
                coros.append(ext_res)
        trans = transaction.get(None)
        all_co = asyncio.gather(*coros, loop=loop)
        if trans: trans.add(all_co)
        results.append(all_co)
        return results

    def ext_publish(self, instance, args, kwargs):
        publish_func = self.external_publishers.get(instance)
        if publish_func:
            # Assume that the loop is manages by the external handler
            return publish_func(*args, **kwargs)

    def __get__(self, instance, cls=None):
        if instance:
            result = self.InstanceProxy(self, instance)
        else:
            result = self
        return result

    def _get_class_handlers(self, instance):
        """Returns the handlers registered at class level.
        """
        cls = instance.__class__
        handlers = cls._signal_handlers
        return set(getattr(instance, hname) for hname, sig_name in
                   handlers.items() if sig_name == self.name)

    def register_instance_publisher(self, instance, func):
        self.external_publishers[instance] = func
