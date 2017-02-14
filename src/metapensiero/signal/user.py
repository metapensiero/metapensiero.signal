# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- Utilities for classes that use the signal
# :Created:    mer 16 dic 2015 12:46:59 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

from collections import ChainMap, defaultdict

from .external import ExternalSignallerAndHandler
from . import SignalError

SPEC_CONTAINER_MEMBER_NAME = '_publish'
"Special attribute name to attach specific info to decorated methods."


class SignalNameHandlerDecorator(object):
    "A decorator used to mark a method as handler for a particular signal."

    def __init__(self, signal_name, **config):
        self.signal_name = signal_name
        self.config = config

    def __call__(self, method):
        setattr(method, SPEC_CONTAINER_MEMBER_NAME,
                {'kind': 'handler', 'name': self.signal_name,
                 'config': self.config})
        return method

    @classmethod
    def is_handler(cls, name, value):
        """Detect an handler and return its wanted signal name."""
        signal_name = False
        config = None
        if callable(value) and hasattr(value, SPEC_CONTAINER_MEMBER_NAME):
                spec = getattr(value, SPEC_CONTAINER_MEMBER_NAME)
                if spec['kind'] == 'handler':
                    signal_name = spec['name']
                    config = spec['config']
        return signal_name, config

handler = SignalNameHandlerDecorator


class SignalAndHandlerInitMeta(type):
    """A metaclass for registering signals and handlers"""

    _is_handler = SignalNameHandlerDecorator.is_handler
    _external_signaller_and_handler = None
    """Optional `ExternalSignaller` instance that connects to external event
    systems."""
    _signals = None
    """Container for signal definitions."""
    _signal_handlers = None
    """Container for handlers definitions."""
    _signal_handlers_sorted = None
    """Contains a Dict[signal_name, handlers] with sorted handlers."""
    _signal_handlers_configs = None
    """Container for additional handler config."""

    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)
        # collect signals and handlers from the bases, overwriting them from
        # right to left
        signaller = cls._external_signaller_and_handler
        signals, handlers, configs = cls._build_inheritation_chain(bases,
            '_signals', '_signal_handlers', '_signal_handlers_configs')
        cls._find_local_signals(signals, namespace)
        cls._find_local_handlers(handlers, namespace, configs)
        cls._signal_handlers_sorted = cls._sort_handlers(handlers, configs)
        if signaller:
            signaller.register_class(cls, bases, namespace, signals, handlers)
        cls._check_local_handlers(signals, handlers, namespace)

        cls._signals = signals
        cls._signal_handlers = handlers
        cls._signal_handlers_configs = configs

    def _build_inheritation_chain(cls, bases, *names):
        """For all of the names build a ChainMap containing a map for every
        base class."""
        result = []
        for name in names:
            result.append(ChainMap({}, *((getattr(base, name, None) or {}) for
                                         base in bases)))
        return result

    def _build_instance_handler_mapping(cls, instance, handle_d):
        """For every unbounded handler, get the bounded version."""
        res = {}
        for member_name, sig_name in handle_d.items():
            if sig_name in res:
                sig_handlers = res[sig_name]
            else:
                sig_handlers = res[sig_name] = []
            sig_handlers.append(getattr(instance, member_name))
        return res

    def _check_local_handlers(cls, signals, handlers, namespace):
        """For every marked handler, see if there is a suitable signal. If
        not, raise an error."""
        for aname, sig_name in handlers.items():
            # WARN: this code doesn't take in account the case where a new
            # method with the same name of an handler in a base class is
            # present in this class but it isn't an handler (so the handler
            # with the same name should be removed from the handlers)
            if sig_name not in signals:
                raise SignalError("Cannot find a signal named '%s'" % sig_name)

    def _find_local_signals(cls, signals,  namespace):
        """Add name info to every "local" (present in the body of this class)
        signal and add it to the mapping.  Also complete signal
        initialization as member of the class by injecting its name.
        """
        from . import Signal
        signaller = cls._external_signaller_and_handler
        for aname, avalue in namespace.items():
            if isinstance(avalue, Signal):
                if avalue.name:
                    aname = avalue.name
                else:
                    avalue.name = aname
                assert aname not in signals
                if signaller:
                    avalue.external_signaller = signaller
                signals[aname] = avalue

    def _find_local_handlers(cls, handlers,  namespace, configs):
        """Add name info to every "local" (present in the body of this class)
        handler and add it to the mapping.
        """
        for aname, avalue in namespace.items():
            sig_name, config = cls._is_handler(aname, avalue)
            if sig_name:
                configs[aname] = config
                handlers[aname] = sig_name

    def _get_class_handlers(cls, signal_name, instance):
        """Returns the handlers registered at class level.
        """
        handlers = cls._signal_handlers_sorted[signal_name]
        return [getattr(instance, hname) for hname in handlers]

    def _sort_handlers(cls, handlers, configs):
        """Sort class defined handlers to give precedence to those declared at lower
        level. ``config`` is unused for now but will be considered for future
        expansions.
        """
        per_signal = defaultdict(list)
        for m in reversed(handlers.maps):
            for hname, sig_name in handlers.items():
                if hname not in per_signal[sig_name]:
                    per_signal[sig_name].append(hname)
        return per_signal

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
        return type(name, (mclass,), {'_external_signaller_and_handler': external})
