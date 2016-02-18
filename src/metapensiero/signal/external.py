# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- external signalling interface
# :Created:    dom 27 dic 2015 23:22:53 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

from __future__ import unicode_literals, absolute_import

import six

from abc import ABCMeta, abstractmethod


@six.add_metaclass(ABCMeta)
class ExternalSignaller(object):
    """An ExternalSignaler ABC, used to interface Signals with external
    event systems.
    """

    @abstractmethod
    def publish_signal(self, signal, instance, loop, args, kwargs):
        """Publish a notification externally. This can be either a normal method or
        a coroutine.
        """
        pass

    @abstractmethod
    def register_signal(self, signal, name):
        """Register a signal with its name"""
        pass


class ExternalSignallerAndHandler(ExternalSignaller):
    """An ABC for interfacing a SignalAndHandlerInitMeta with an external
    handling system.
    """

    @abstractmethod
    def register_class(cls, bases, namespace, signals, handlers):
        """Register a new class"""
        pass
