# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- Utilities for classes that use the signal
# :Created:   mer 16 dic 2015 12:46:59 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2015 Alberto Berti
#

from abc import ABCMeta
from collections import ChainMap, defaultdict
from functools import partial

from .external import ExternalSignallerAndHandler
from .utils import HANDLERS_SORT_MODE, SignalError


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


class InheritanceToolsMeta(ABCMeta):
    """A reusable metaclass with method to deal with constructing data from
    elements contained in one class body and in its bases."""

    def _build_inheritance_chain(cls, bases, *names, merge=False):
        """For all of the names build a ChainMap containing a map for every
        base class."""
        result = []
        for name in names:
            maps = []
            for base in bases:
                bmap = getattr(base, name, None)
                if bmap is not None:
                    assert isinstance(bmap, (dict, ChainMap))
                    if len(bmap):
                        if isinstance(bmap, ChainMap):
                            maps.extend(bmap.maps)
                        else:
                            maps.append(bmap)
            result.append(ChainMap({}, *maps))
        if merge:
            result = [dict(map) for map in result]
        return result


class SignalAndHandlerInitMeta(InheritanceToolsMeta):
    """A metaclass for registering signals and handlers."""

    _is_handler = SignalNameHandlerDecorator.is_handler

    _external_signaller_and_handler = None
    """Optional :class:`~.atom.ExternalSignaller` instance that connects to
    external event systems.
    """

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
        signals, handlers, configs = cls._build_inheritance_chain(
            bases, '_signals', '_signal_handlers', '_signal_handlers_configs')
        cls._find_local_signals(signals, namespace)
        cls._find_local_handlers(handlers, namespace, configs)
        cls._signal_handlers_sorted = cls._sort_handlers(
            signals, handlers, configs)
        configs = dict(configs)
        if signaller is not None:
            try:
                signaller.register_class(
                    cls, bases, namespace, signals, handlers)
            except Exception as cause:
                new = SignalError(("Error while registering class "
                                   "{cls!r}").format(cls=cls))
                raise new from cause
        cls._check_local_handlers(signals, handlers, namespace, configs)

        cls._signals = signals
        cls._signal_handlers = handlers
        cls._signal_handlers_configs = configs

    def _build_instance_handler_mapping(cls, instance, handle_d):
        """For every unbound handler, get the bound version."""
        res = {}
        for member_name, sig_name in handle_d.items():
            if sig_name in res:
                sig_handlers = res[sig_name]
            else:
                sig_handlers = res[sig_name] = []
            sig_handlers.append(getattr(instance, member_name))
        return res

    def _check_local_handlers(cls, signals, handlers, namespace, configs):
        """For every marked handler, see if there is a suitable signal. If
        not, raise an error."""
        for aname, sig_name in handlers.items():
            # WARN: this code doesn't take in account the case where a new
            # method with the same name of an handler in a base class is
            # present in this class but it isn't an handler (so the handler
            # with the same name should be removed from the handlers)
            if sig_name not in signals:
                disable_check = configs[aname].get('disable_check', False)
                if not disable_check:
                    raise SignalError("Cannot find a signal named '%s'"
                                      % sig_name)

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

    def _sort_handlers(cls, signals, handlers, configs):
        """Sort class defined handlers to give precedence to those declared at
        lower level. ``config`` can contain two keys ``begin`` or ``end`` that
        will further reposition the handler at the two extremes.
        """
        def macro_precedence_sorter(direction, hname):
            """The default is to sort 'bottom_up', with lower level getting
            executed first, but sometimes you need them reversed."""
            data = configs[hname]
            topdown_sort = direction == HANDLERS_SORT_MODE.TOPDOWN
            if topdown_sort:
                level = levels_count - 1 - data['level']
            else:
                level = data['level']
            if 'begin' in data:
                return (-1, level, hname)
            elif 'end' in data:
                return (1, level, hname)
            else:
                return (0, level, hname)

        levels_count = len(handlers.maps)
        per_signal = defaultdict(list)
        for level, m in enumerate(reversed(handlers.maps)):
            for hname, sig_name in m.items():
                sig_handlers = per_signal[sig_name]
                if hname not in sig_handlers:
                    configs[hname]['level'] = level
                    sig_handlers.append(hname)
        for sig_name, sig_handlers in per_signal.items():
            if sig_name in signals:  # it may be on a mixin
                sort_mode = signals[sig_name]._sort_mode
                sig_handlers.sort(key=partial(macro_precedence_sorter,
                                              sort_mode))
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
        return type(name, (mclass,),
                    {'_external_signaller_and_handler': external})
