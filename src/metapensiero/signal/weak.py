# -*- coding: utf-8 -*-
# :Project:  metapensiero.signal -- weak ref derived classes
# :Created:    mer 16 dic 2015 12:30:10 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
#

from __future__ import unicode_literals, absolute_import

import six

import inspect
import weakref

if six.PY3:
    WeakMethod = weakref.WeakMethod
else:
    import weakrefmethod
    WeakMethod = weakrefmethod.WeakMethod


class MethodAwareWeakSet(weakref.WeakSet):
    """A WeakSet than can take instance method as member"""

    def add(self, item):
        """A customized add that tests item and if it's a method uses a
        proper weakref.
        """
        # unfortunately i have to reimplement the method completely
        if self._pending_removals:
            self._commit_removals()
        if inspect.ismethod(item):
            ref = WeakMethod
        else:
            ref = weakref.ref
        self.data.add(ref(item, self._remove))
