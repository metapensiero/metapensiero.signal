# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- A event framework that is asyncio aware
# :Created:   dom 09 ago 2015 12:57:35 CEST
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2015 Alberto Berti
#

import enum


class SignalError(Exception):
    pass


HANDLERS_SORT_MODE = enum.Enum('HANDLERS_SORT_MODE', 'BOTTOMUP TOPDOWN')


from .external import ExternalSignaller, ExternalSignallerAndHandler
from .user import SignalNameHandlerDecorator, handler, SignalAndHandlerInitMeta
from .atom import Signal

__all__ = ('SignalError', 'Signal', 'SignalNameHandlerDecorator', 'handler',
           'SignalAndHandlerInitMeta', 'ExternalSignaller',
           'ExternalSignallerAndHandler', 'HANDLERS_SORT_MODE')
