# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- A event framework that is asyncio aware
# :Created:   dom 09 ago 2015 12:57:35 CEST
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2015 Alberto Berti
#

import enum
import logging


NOISY_ERROR_LOGGER = logging.Logger.error


def log_noisy_error(logger, *args, **kwargs):
    NOISY_ERROR_LOGGER(logger, *args, **kwargs)


class SignalError(Exception):
    pass


HANDLERS_SORT_MODE = enum.Enum('HANDLERS_SORT_MODE', 'BOTTOMUP TOPDOWN')


from .external import ExternalSignaller, ExternalSignallerAndHandler
from .user import SignalNameHandlerDecorator, handler, SignalAndHandlerInitMeta
from .atom import Signal
from .utils import MultipleResults, NoResult

__all__ = (
    'ExternalSignaller',
    'ExternalSignallerAndHandler',
    'HANDLERS_SORT_MODE',
    'MultipleResults',
    'NoResult'
    'Signal',
    'SignalAndHandlerInitMeta',
    'SignalError',
    'SignalNameHandlerDecorator',
    'handler',
)
