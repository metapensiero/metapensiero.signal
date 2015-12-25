# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- A event framework that is asyncio aware
# :Created:   dom 09 ago 2015 12:57:35 CEST
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2015 Alberto Berti
#


class SignalError(Exception):
    pass


from .atom import Signal
from .user import SignalNameHandlerDecorator, handler, SignalAndHandlerInitMeta

__all__ = ('SignalError', 'Signal', 'SignalNameHandlerDecorator', 'handler',
           'SignalAndHandlerInitMeta')
