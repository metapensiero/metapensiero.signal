# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- weak ref derived classes
# :Created:   mer 16 dic 2015 12:30:10 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2015, 2016, 2017, 2018 Alberto Berti
#

import inspect
import weakref

from weakreflist import WeakList


class MethodAwareWeakList(WeakList):
    """A weaklist that supports methods"""

    def ref(self, item):
        if inspect.ismethod(item):
            try:
                item = weakref.WeakMethod(item, self.remove_all)
            finally:
                return item
        else:
            return super().ref(item)
