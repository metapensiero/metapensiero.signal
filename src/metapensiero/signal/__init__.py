# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- A event framework that is asyncio aware
# :Created:   dom 09 ago 2015 12:57:35 CEST
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2015 Alberto Berti
#

import logging


NOISY_ERROR_LOGGER = logging.Logger.error


def log_noisy_error(logger, *args, **kwargs):
    NOISY_ERROR_LOGGER(logger, *args, **kwargs)


from .external import ExternalSignaller, ExternalSignallerAndHandler
from .user import SignalNameHandlerDecorator, handler, SignalAndHandlerInitMeta
from .core import Signal
from .utils import (Executor, MultipleResults, NoResult, SignalError,
                    SignalOptions)


__all__ = (
    'Executor',
    'ExternalSignaller',
    'ExternalSignallerAndHandler',
    'MultipleResults',
    'NoResult',
    'Signal',
    'SignalAndHandlerInitMeta',
    'SignalError',
    'SignalNameHandlerDecorator',
    'SignalOptions',
    'handler',
)
