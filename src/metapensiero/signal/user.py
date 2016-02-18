# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- Utilities for classes that use the signal
# :Created:    mer 16 dic 2015 12:46:59 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

from __future__ import unicode_literals, absolute_import

import six

if six.PY3:
    from collections import ChainMap
else:
    ChainMap = None

from .external import ExternalSignallerAndHandler
from . import SignalError

SPEC_CONTAINER_MEMBER_NAME = '_publish'
"Special attribute name to attach specific info to decorated methods."


class SignalNameHandlerDecorator(object):
    "A decorator used to mark a method as handler for a particular signal."

    def __init__(self, signal_name):
        self.signal_name = signal_name

    def __call__(self, method):
        setattr(method, SPEC_CONTAINER_MEMBER_NAME,
                {'kind': 'handler', 'name': self.signal_name})
        return method

    @classmethod
    def is_handler(cls, name, value):
        """Detect an handler and return its wanted signal name."""
        signal_name = False
        if callable(value) and hasattr(value, SPEC_CONTAINER_MEMBER_NAME):
                spec = getattr(value, SPEC_CONTAINER_MEMBER_NAME)
                if spec['kind'] == 'handler':
                    signal_name = spec['name']
        return signal_name

handler = SignalNameHandlerDecorator


class SignalAndHandlerInitMeta(type):
    """A metaclass for registering signals and handlers"""

    _is_handler = SignalNameHandlerDecorator.is_handler
    _external_signaller_and_handler = None

    def __init__(cls, name, bases, namespace):
        super(SignalAndHandlerInitMeta, cls).__init__(name, bases, namespace)
        # collect signals and handlers from the bases, overwriting them from
        # right to left
        signaller = cls._external_signaller_and_handler
        signals, handlers = cls._build_inheritation_chain(bases, '_signals',
                                                          '_signal_handlers')
        cls._find_local_signals(signals, namespace)
        cls._find_local_handlers(handlers, namespace)
        if signaller:
            signaller.register_class(cls, bases, namespace, signals, handlers)
        cls._check_local_handlers(signals, handlers, namespace)
        cls._signals = signals
        cls._signal_handlers = handlers

    def _find_local_signals(cls, signals,  namespace):
        """Add name info to every "local" (present in the body of this class)
        signal and add it to the mapping.  Also complete signal
        initialization as member of the class by injecting its name.
        """
        from . import Signal
        signaller = cls._external_signaller_and_handler
        for aname, avalue in six.iteritems(namespace):
            if isinstance(avalue, Signal):
                avalue.name = aname
                if signaller:
                    avalue.external_signaller = signaller
                signals[aname] = avalue

    def _find_local_handlers(cls, handlers,  namespace):
        """Add name info to every "local" (present in the body of this class)
        handler and add it to the mapping.
        """
        for aname, avalue in six.iteritems(namespace):
            sig_name = cls._is_handler(aname, avalue)
            if sig_name:
                handlers[aname] = sig_name

    def _check_local_handlers(cls, signals, handlers, namespace):
        """For every marked handler, see if there is a suitable signal. If
        not, raise an error."""
        for aname, sig_name in six.iteritems(handlers):
            # WARN: this code doesn't take in account the case where a new
            # method with the same name of an handler in a base class is
            # present in this class but it isn't an handler (so the handler
            # with the same name should be removed from the handlers)
            if sig_name not in signals:
                raise SignalError("Cannot find a signal named '%s'" % sig_name)

    def _build_inheritation_chain(cls, bases, *names):
        """For all of the names build a ChainMap containing a map for every
        base class."""
        result = []
        # chainmaps aren't available on PY2
        if six.PY3:
            for name in names:
                result.append(ChainMap({}, *(getattr(base, name, {}) for
                                             base in bases)))
        else:
            bases = list(bases)
            bases.reverse()
            for name in names:
                reg = {}
                for base in bases:
                    base_reg = getattr(base, name, None)
                    if base_reg:
                        reg.update(base_reg)
                result.append(reg)
        return result

    def _build_instance_handler_mapping(cls, instance, handle_d):
        """For every unbounded handler, get the bounded version."""
        res = {}
        for member_name, sig_name in six.iteritems(handle_d):
            if sig_name in res:
                sig_handlers = res[sig_name]
            else:
                sig_handlers = res[sig_name] = []
            sig_handlers.append(getattr(instance, member_name))
        return res

    def instance_signals_and_handlers(cls, instance):
        """Calculate per-instance signals and handlers."""
        isignals = cls._signals.copy()

        ihandlers = cls._build_instance_handler_mapping(
            instance,
            cls._signal_handlers
        )
        return isignals, ihandlers

    @classmethod
    def with_external(mclass, external, name=None):
        assert isinstance(external, ExternalSignallerAndHandler)
        name = name or "ExternalSignalAndHandlerInitMeta"
        if six.PY2:
            # Py2 needs a string
            name = str(name)
        return type(name, (mclass,), {'_external_signaller_and_handler': external})
